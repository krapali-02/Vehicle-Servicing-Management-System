import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db
from models.models import User, Vehicle, Mechanic, Booking, Bill

app = Flask(__name__)

# Basic Configuration
app.config['SECRET_KEY'] = 'vcms-secret-key-2026'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'vcms.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize DB with App
db.init_app(app)

# Ensure Database Tables Exist & Seed Initial Demo Data
def init_db():
    with app.app_context():
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        if inspector.has_table('vehicles'):
            columns = [c['name'] for c in inspector.get_columns('vehicles')]
            if 'year' not in columns:
                print("Updating database schema with new fields...")
                db.drop_all()

        db.create_all()

        # Seed default Admin, Mechanic, and Customer if database is empty
        if not User.query.first():
            print("Seeding initial data into SQLite database...")
            admin = User(name="Admin User", email="admin@vcms.com", password="admin123", role="Admin")
            customer = User(name="John Doe", email="customer@vcms.com", password="user123", role="Customer")
            mechanic_user = User(name="Mike Mechanic", email="mechanic@vcms.com", password="mech123", role="Mechanic")
            
            db.session.add_all([admin, customer, mechanic_user])
            db.session.commit()

            # Seed Mechanic details
            m1 = Mechanic(name="Mike Mechanic", phone="9876543210", specialization="Engine & Brake Specialist", user_id=mechanic_user.id)
            m2 = Mechanic(name="Alex Electrician", phone="9123456789", specialization="AC & Electrical Specialist", user_id=None)
            
            db.session.add_all([m1, m2])
            db.session.commit()
            print("Initial database seed completed successfully.")

# Authentication & Role-Based Access Control Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            user_role = session.get('role')
            if user_role not in allowed_roles:
                flash(f'Access denied: You are logged in as {user_role}. You cannot access that page.', 'danger')
                if user_role == 'Customer':
                    return redirect(url_for('customer_dashboard'))
                elif user_role == 'Admin':
                    return redirect(url_for('admin_dashboard'))
                elif user_role == 'Mechanic':
                    return redirect(url_for('mechanic_dashboard'))
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_current_mechanic():
    user_id = session.get('user_id')
    user_name = session.get('user_name')
    if not user_id:
        return None
    mechanic = Mechanic.query.filter_by(user_id=user_id).first()
    if not mechanic and user_name:
        mechanic = Mechanic.query.filter_by(name=user_name).first()
        if mechanic and not mechanic.user_id:
            mechanic.user_id = user_id
            db.session.commit()
    return mechanic

# --- ROUTES ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        user_role = session.get('role')
        if user_role == 'Customer':
            return redirect(url_for('customer_dashboard'))
        elif user_role == 'Admin':
            return redirect(url_for('admin_dashboard'))
        elif user_role == 'Mechanic':
            return redirect(url_for('mechanic_dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        if not name or not email or not password:
            flash('Please fill in all required fields.', 'danger')
            return render_template('register.html')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email address is already registered. Please log in.', 'danger')
            return redirect(url_for('login'))

        new_user = User(
            name=name,
            email=email,
            password=password,
            role='Customer'
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Account registered successfully! Please log in with your credentials.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        user_role = session.get('role')
        if user_role == 'Customer':
            return redirect(url_for('customer_dashboard'))
        elif user_role == 'Admin':
            return redirect(url_for('admin_dashboard'))
        elif user_role == 'Mechanic':
            return redirect(url_for('mechanic_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(email=email).first()

        if user and user.password == password:
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['email'] = user.email
            session['role'] = user.role

            flash(f'Logged in successfully as {user.name} ({user.role})', 'success')

            if user.role == 'Customer':
                return redirect(url_for('customer_dashboard'))
            elif user.role == 'Admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'Mechanic':
                return redirect(url_for('mechanic_dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

# --- CUSTOMER MODULES ---

@app.route('/customer/dashboard')
@role_required('Customer')
def customer_dashboard():
    user_id = session['user_id']
    vehicles = Vehicle.query.filter_by(customer_id=user_id).all()
    bookings = Booking.query.filter_by(customer_id=user_id).all()
    bills = [b.bill for b in bookings if b.bill is not None]
    
    return render_template('customer_dashboard.html',
                           vehicle_count=len(vehicles),
                           booking_count=len(bookings),
                           bill_count=len(bills))

@app.route('/customer/vehicles')
@role_required('Customer')
def customer_vehicles():
    user_id = session['user_id']
    vehicles = Vehicle.query.filter_by(customer_id=user_id).all()
    return render_template('vehicles.html', vehicles=vehicles)

@app.route('/customer/vehicles/add', methods=['GET', 'POST'])
@role_required('Customer')
def add_vehicle():
    user_id = session['user_id']
    if request.method == 'POST':
        reg_no = request.form.get('registration_no', '').strip().upper()
        model = request.form.get('model', '').strip()
        v_type = request.form.get('type', '').strip()
        year = request.form.get('year', '').strip()

        if not reg_no or not model:
            flash('Registration number and model are required.', 'danger')
            return redirect(url_for('add_vehicle'))

        existing = Vehicle.query.filter_by(registration_no=reg_no).first()
        if existing:
            flash(f'Vehicle with registration number {reg_no} is already registered.', 'danger')
            return redirect(url_for('add_vehicle'))

        new_vehicle = Vehicle(
            customer_id=user_id,
            registration_no=reg_no,
            model=model,
            type=v_type,
            year=year
        )
        db.session.add(new_vehicle)
        db.session.commit()

        flash(f'Vehicle {model} ({reg_no}) registered successfully!', 'success')
        return redirect(url_for('customer_vehicles'))

    return render_template('add_vehicle.html')

@app.route('/customer/vehicles/edit/<int:vehicle_id>', methods=['POST'])
@role_required('Customer')
def edit_vehicle(vehicle_id):
    user_id = session['user_id']
    vehicle = Vehicle.query.get_or_404(vehicle_id)

    if vehicle.customer_id != user_id:
        flash('Unauthorized access to vehicle record.', 'danger')
        return redirect(url_for('customer_vehicles'))

    reg_no = request.form.get('registration_no', '').strip().upper()
    model = request.form.get('model', '').strip()
    v_type = request.form.get('type', '').strip()
    year = request.form.get('year', '').strip()

    if reg_no != vehicle.registration_no:
        existing = Vehicle.query.filter_by(registration_no=reg_no).first()
        if existing:
            flash(f'Registration number {reg_no} is already used by another vehicle.', 'danger')
            return redirect(url_for('customer_vehicles'))

    vehicle.registration_no = reg_no
    vehicle.model = model
    vehicle.type = v_type
    vehicle.year = year
    db.session.commit()

    flash('Vehicle details updated successfully.', 'success')
    return redirect(url_for('customer_vehicles'))

@app.route('/customer/vehicles/delete/<int:vehicle_id>', methods=['POST'])
@role_required('Customer')
def delete_vehicle(vehicle_id):
    user_id = session['user_id']
    vehicle = Vehicle.query.get_or_404(vehicle_id)

    if vehicle.customer_id != user_id:
        flash('Unauthorized access to vehicle record.', 'danger')
        return redirect(url_for('customer_vehicles'))

    db.session.delete(vehicle)
    db.session.commit()

    flash('Vehicle deleted successfully.', 'info')
    return redirect(url_for('customer_vehicles'))

@app.route('/customer/book-service', methods=['GET', 'POST'])
@role_required('Customer')
def book_service():
    user_id = session['user_id']
    vehicles = Vehicle.query.filter_by(customer_id=user_id).all()

    if request.method == 'POST':
        vehicle_id = request.form.get('vehicle_id', type=int)
        service_name = request.form.get('service_name', '').strip()
        booking_date = request.form.get('booking_date', '').strip()
        remarks = request.form.get('remarks', '').strip()

        if not vehicle_id or not service_name or not booking_date:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('book_service'))

        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle or vehicle.customer_id != user_id:
            flash('Invalid vehicle selection.', 'danger')
            return redirect(url_for('book_service'))

        new_booking = Booking(
            vehicle_id=vehicle_id,
            customer_id=user_id,
            service_name=service_name,
            booking_date=booking_date,
            remarks=remarks,
            status='Booked'
        )
        db.session.add(new_booking)
        db.session.commit()

        flash(f'Service booking for {vehicle.model} on {booking_date} submitted successfully!', 'success')
        return redirect(url_for('customer_bookings'))

    return render_template('book_service.html', vehicles=vehicles)

@app.route('/customer/bookings')
@role_required('Customer')
def customer_bookings():
    user_id = session['user_id']
    bookings = Booking.query.filter_by(customer_id=user_id).order_by(Booking.id.desc()).all()
    return render_template('customer_bookings.html', bookings=bookings)

@app.route('/customer/bills')
@role_required('Customer')
def customer_bills():
    user_id = session['user_id']
    customer_bookings = Booking.query.filter_by(customer_id=user_id).all()
    bills = [b.bill for b in customer_bookings if b.bill is not None]
    return render_template('customer_bills.html', bills=bills)

# --- ADMIN / SERVICE ADVISOR MODULE ---

@app.route('/admin/dashboard')
@role_required('Admin')
def admin_dashboard():
    total_customers = User.query.filter_by(role='Customer').count()
    total_vehicles = Vehicle.query.count()
    total_bookings = Booking.query.count()
    pending_bookings = Booking.query.filter_by(status='Booked').count()
    active_services = Booking.query.filter(Booking.status.in_(['Mechanic Assigned', 'Under Service'])).count()
    completed_services = Booking.query.filter_by(status='Completed').count()

    bookings = Booking.query.order_by(Booking.id.desc()).all()

    return render_template('admin_dashboard.html',
                           total_customers=total_customers,
                           total_vehicles=total_vehicles,
                           total_bookings=total_bookings,
                           pending_bookings=pending_bookings,
                           active_services=active_services,
                           completed_services=completed_services,
                           bookings=bookings)

@app.route('/admin/bookings/<int:booking_id>')
@role_required('Admin')
def admin_booking_detail(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    mechanics = Mechanic.query.all()
    return render_template('admin_booking_detail.html', booking=booking, mechanics=mechanics)

@app.route('/admin/bookings/<int:booking_id>/assign-mechanic', methods=['POST'])
@role_required('Admin')
def assign_mechanic(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    mechanic_id = request.form.get('mechanic_id', type=int)

    mechanic = Mechanic.query.get(mechanic_id)
    if not mechanic:
        flash('Invalid mechanic selected.', 'danger')
        return redirect(url_for('admin_booking_detail', booking_id=booking.id))

    booking.mechanic_id = mechanic_id
    if booking.status == 'Booked':
        booking.status = 'Mechanic Assigned'

    db.session.commit()

    flash(f'Mechanic {mechanic.name} assigned to Booking #{booking.id} successfully!', 'success')
    return redirect(url_for('admin_booking_detail', booking_id=booking.id))

@app.route('/admin/bookings/<int:booking_id>/update-status', methods=['POST'])
@role_required('Admin')
def update_service_status(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    new_status = request.form.get('status', '').strip()

    allowed_statuses = ['Booked', 'Mechanic Assigned', 'Under Service', 'Completed']
    if new_status not in allowed_statuses:
        flash('Invalid status selection.', 'danger')
        return redirect(url_for('admin_booking_detail', booking_id=booking.id))

    booking.status = new_status
    db.session.commit()

    flash(f'Status for Booking #{booking.id} updated to "{new_status}".', 'success')
    return redirect(url_for('admin_booking_detail', booking_id=booking.id))

@app.route('/admin/mechanics')
@role_required('Admin')
def admin_mechanics():
    mechanics = Mechanic.query.all()
    return render_template('admin_mechanics.html', mechanics=mechanics)

@app.route('/admin/mechanics/add', methods=['POST'])
@role_required('Admin')
def add_mechanic():
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    specialization = request.form.get('specialization', '').strip()

    if not name or not phone or not specialization:
        flash('Please fill in all mechanic details.', 'danger')
        return redirect(url_for('admin_mechanics'))

    new_mechanic = Mechanic(name=name, phone=phone, specialization=specialization)
    db.session.add(new_mechanic)
    db.session.commit()

    flash(f'Mechanic {name} registered successfully!', 'success')
    return redirect(url_for('admin_mechanics'))

# --- ADMIN BILLING ROUTES ---

@app.route('/admin/bills')
@role_required('Admin')
def admin_bills():
    bills = Bill.query.order_by(Bill.id.desc()).all()
    completed_bookings = Booking.query.filter_by(status='Completed').filter(~Booking.bill.has()).all()
    
    pending_bills_count = len([b for b in bills if b.payment_status == 'Pending'])
    total_revenue = sum([b.total_amount for b in bills if b.payment_status == 'Paid'])

    return render_template('admin_bills.html',
                           bills=bills,
                           completed_bookings=completed_bookings,
                           pending_bills_count=pending_bills_count,
                           total_revenue=total_revenue)

@app.route('/admin/bills/create', methods=['POST'])
@role_required('Admin')
def create_bill():
    booking_id = request.form.get('booking_id', type=int)
    try:
        service_charge = float(request.form.get('service_charge', 0))
        extra_charge = float(request.form.get('extra_charge', 0))
    except ValueError:
        flash('Invalid charge amounts entered.', 'danger')
        return redirect(url_for('admin_bills'))

    payment_status = request.form.get('payment_status', 'Pending').strip()

    booking = Booking.query.get(booking_id)
    if not booking or booking.status != 'Completed':
        flash('Cannot generate bill: Only completed service bookings are billable.', 'danger')
        return redirect(url_for('admin_bills'))

    existing_bill = Bill.query.filter_by(booking_id=booking_id).first()
    if existing_bill:
        flash(f'A bill has already been generated for Booking #{booking_id}.', 'danger')
        return redirect(url_for('admin_bills'))

    total_amount = service_charge + extra_charge

    new_bill = Bill(
        booking_id=booking_id,
        service_charge=service_charge,
        extra_charge=extra_charge,
        total_amount=total_amount,
        payment_status=payment_status
    )
    db.session.add(new_bill)
    db.session.commit()

    flash(f'Bill #BILL-{new_bill.id} generated for Booking #{booking_id} with Total: ₹{total_amount}.', 'success')
    return redirect(url_for('admin_bills'))

@app.route('/admin/bills/<int:bill_id>/update-status', methods=['POST'])
@role_required('Admin')
def update_payment_status(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    new_payment_status = request.form.get('payment_status', 'Pending').strip()

    if new_payment_status not in ['Pending', 'Paid']:
        flash('Invalid payment status.', 'danger')
        return redirect(url_for('admin_bills'))

    bill.payment_status = new_payment_status
    db.session.commit()

    flash(f'Payment status for Bill #BILL-{bill.id} updated to "{new_payment_status}".', 'success')
    return redirect(url_for('admin_bills'))

# --- MECHANIC WORKBENCH MODULE ---

@app.route('/mechanic/dashboard')
@role_required('Mechanic')
def mechanic_dashboard():
    mechanic = get_current_mechanic()
    if not mechanic:
        bookings = []
    else:
        bookings = Booking.query.filter_by(mechanic_id=mechanic.id).order_by(Booking.id.desc()).all()

    assigned_count = len(bookings)
    active_count = len([b for b in bookings if b.status == 'Under Service'])
    completed_count = len([b for b in bookings if b.status == 'Completed'])

    return render_template('mechanic_dashboard.html',
                           bookings=bookings,
                           assigned_count=assigned_count,
                           active_count=active_count,
                           completed_count=completed_count)

@app.route('/mechanic/jobs/<int:booking_id>')
@role_required('Mechanic')
def mechanic_job_detail(booking_id):
    mechanic = get_current_mechanic()
    booking = Booking.query.get_or_404(booking_id)

    if not mechanic or booking.mechanic_id != mechanic.id:
        flash('Access denied: You can only view jobs assigned directly to you.', 'danger')
        return redirect(url_for('mechanic_dashboard'))

    return render_template('mechanic_job_detail.html', booking=booking)

@app.route('/mechanic/jobs/<int:booking_id>/update-status', methods=['POST'])
@role_required('Mechanic')
def mechanic_update_status(booking_id):
    mechanic = get_current_mechanic()
    booking = Booking.query.get_or_404(booking_id)

    if not mechanic or booking.mechanic_id != mechanic.id:
        flash('Access denied: You can only update jobs assigned directly to you.', 'danger')
        return redirect(url_for('mechanic_dashboard'))

    new_status = request.form.get('status', '').strip()
    allowed_statuses = ['Mechanic Assigned', 'Under Service', 'Completed']

    if new_status not in allowed_statuses:
        flash('Invalid status selection for mechanic.', 'danger')
        return redirect(url_for('mechanic_job_detail', booking_id=booking.id))

    booking.status = new_status
    db.session.commit()

    flash(f'Job #{booking.id} status updated to "{new_status}" successfully.', 'success')
    return redirect(url_for('mechanic_job_detail', booking_id=booking.id))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
