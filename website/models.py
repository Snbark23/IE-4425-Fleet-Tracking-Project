from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from sqlalchemy import DateTime

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    last_name = db.Column(db.String(150))
    role = db.Column(db.String(50))

    vehicles = db.relationship('Vehicle', backref='owner', lazy=True)

    # Disambiguated relationships for WorkAssignment
    driver_assignments = db.relationship('WorkAssignment', foreign_keys='WorkAssignment.driver_id', backref='driver_user', lazy=True)
    closed_assignments = db.relationship('WorkAssignment', foreign_keys='WorkAssignment.closed_by', backref='closer_user', lazy=True)

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vin = db.Column(db.String(17), unique=True, nullable=False)
    make = db.Column(db.String(50))
    model = db.Column(db.String(50))
    year = db.Column(db.Integer)
    engine_type = db.Column(db.String(50))
    displacement = db.Column(db.String(50))
    cylinders = db.Column(db.Integer)
    fuel_type = db.Column(db.String(50))
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# Fleet Manager
class VehicleAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'))
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    assignment_date = db.Column(db.DateTime, default=func.now())

    vehicle = db.relationship('Vehicle', backref='assignments')
    driver = db.relationship('User', backref='assignments')

class WorkOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    scheduled_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

class WorkAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    closed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    work_order_id = db.Column(db.Integer, db.ForeignKey('work_order.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)

    driver = db.relationship('User', foreign_keys=[driver_id])
    closer = db.relationship('User', foreign_keys=[closed_by])
    work_order = db.relationship('WorkOrder', backref='assignments')
    vehicle = db.relationship('Vehicle', backref='work_assignments')

    status = db.Column(db.String(20), default='Assigned')
    closed_at = db.Column(db.DateTime)

    __table_args__ = (
        db.UniqueConstraint('work_order_id', 'driver_id', name='unique_driver_assignment'),
        db.UniqueConstraint('work_order_id', 'vehicle_id', name='unique_vehicle_assignment'),
    )

# Driver Employee
class FuelLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'))
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    gallons = db.Column(db.Float)
    cost = db.Column(db.Float)
    date = db.Column(db.Date, default=func.now())

    start_mileage = db.Column(db.Float)
    end_mileage = db.Column(db.Float)
    miles_driven = db.Column(db.Float)

class IncidentReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'))
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    description = db.Column(db.Text)
    date = db.Column(db.Date, default=func.now())

class AccidentReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'))
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    description = db.Column(db.Text)
    damage_estimate = db.Column(db.Float)
    date = db.Column(db.Date, default=func.now())

# Clerical Employee
class MaintenanceEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'))
    description = db.Column(db.Text)
    maintenance_date = db.Column(db.Date)
    cost = db.Column(db.Float)
    vehicle = db.relationship('Vehicle') 

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    upload_date = db.Column(db.DateTime(timezone=True), server_default=func.now())

class DecommissionedVehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vin = db.Column(db.String(17))
    make = db.Column(db.String(50))
    model = db.Column(db.String(50))
    year = db.Column(db.Integer)
    engine_type = db.Column(db.String(50))
    displacement = db.Column(db.String(50))
    cylinders = db.Column(db.Integer)
    fuel_type = db.Column(db.String(50))
    sale_price = db.Column(db.Float)
    salvage_value = db.Column(db.Float)
    money_received = db.Column(db.Float)
    reason = db.Column(db.Text)
    decommission_date = db.Column(db.DateTime, server_default=func.now())
