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

# Driver Employee
class FuelLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'))
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    gallons = db.Column(db.Float)
    cost = db.Column(db.Float)
    date = db.Column(db.Date, default=func.now())

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

class MileageLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'))
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    miles_driven = db.Column(db.Float)
    date = db.Column(db.Date, default=func.now())

# Clerical Employee
class MaintenanceEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'))
    description = db.Column(db.Text)
    maintenance_date = db.Column(db.Date)
    cost = db.Column(db.Float)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    upload_date = db.Column(db.DateTime(timezone=True), server_default=func.now())

