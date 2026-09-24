from datetime import datetime
from . import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'Customer', 'Admin', 'Mechanic'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    vehicles = db.relationship('Vehicle', backref='owner', lazy=True, cascade="all, delete-orphan")
    bookings = db.relationship('Booking', backref='customer', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.name} ({self.role})>"


class Vehicle(db.Model):
    __tablename__ = 'vehicles'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    registration_no = db.Column(db.String(50), unique=True, nullable=False)
    model = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'Car', 'Bike', 'SUV', 'Scooter', 'Truck'
    year = db.Column(db.String(20), nullable=True)   # Manufacturing / Purchase Year
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    bookings = db.relationship('Booking', backref='vehicle', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Vehicle {self.registration_no} - {self.model}>"


class Mechanic(db.Model):
    __tablename__ = 'mechanics'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    specialization = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    bookings = db.relationship('Booking', backref='assigned_mechanic', lazy=True)

    def __repr__(self):
        return f"<Mechanic {self.name} ({self.specialization})>"


class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    service_name = db.Column(db.String(100), nullable=False)
    booking_date = db.Column(db.String(50), nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='Booked', nullable=False)  # 'Booked', 'Mechanic Assigned', 'Under Service', 'Completed'
    mechanic_id = db.Column(db.Integer, db.ForeignKey('mechanics.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to Bill (one-to-one)
    bill = db.relationship('Bill', backref='booking', uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Booking #{self.id} - {self.service_name} ({self.status})>"


class Bill(db.Model):
    __tablename__ = 'bills'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), unique=True, nullable=False)
    service_charge = db.Column(db.Float, default=0.0, nullable=False)
    extra_charge = db.Column(db.Float, default=0.0, nullable=False)
    total_amount = db.Column(db.Float, default=0.0, nullable=False)
    payment_status = db.Column(db.String(20), default='Pending', nullable=False)  # 'Pending', 'Paid'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Bill #{self.id} - Booking #{self.booking_id} Total: {self.total_amount}>"
