import sys
import os
from faker import Faker
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from website import create_app, db
from website.models import User, Vehicle, WorkOrder, FuelLog, VehicleAssignment

app = create_app()
fake = Faker()

with app.app_context():
    db.drop_all()
    db.create_all()

    # === Add 1 user per core role ===
    users = [
        User(first_name="Holly", last_name="Admin", email="hr@fleet.com", role="HR Admin",
             password=generate_password_hash("password123")),
        User(first_name="Casey", last_name="Clerk", email="clerk@fleet.com", role="Clerical Employee",
             password=generate_password_hash("password123")),
        User(first_name="Morgan", last_name="Manager", email="manager@fleet.com", role="Fleet Manager",
             password=generate_password_hash("password123")),
        User(first_name="Riley", last_name="Driver", email="driver@fleet.com", role="Driver Employee",
             password=generate_password_hash("password123"))
    ]

    for user in users:
        db.session.add(user)
    db.session.commit()

    driver = User.query.filter_by(email="driver@fleet.com").first()

    # === Add 50 vehicles and assign them to the driver ===
    makes = ['Ford', 'Toyota', 'Chevy', 'Nissan', 'Honda']
    models = ['F-150', 'Camry', 'Silverado', 'Altima', 'Civic']

    vehicles = []
    for _ in range(50):
        make = random.choice(makes)
        model = random.choice(models)
        vin = fake.unique.bothify(text='???#####??###???')
        vehicle = Vehicle(make=make, model=model, vin=vin, owner_id=driver.id)
        db.session.add(vehicle)
        db.session.flush()  # Needed to get vehicle.id before commit
        vehicles.append(vehicle)

        assignment = VehicleAssignment(vehicle_id=vehicle.id, driver_id=driver.id)
        db.session.add(assignment)

    db.session.commit()

    # === Add 50 work orders ===
    for i in range(50):
        title = f"Work Order {i+1}"
        description = fake.sentence()
        scheduled = fake.date_time_this_year()
        db.session.add(WorkOrder(title=title, description=description, scheduled_date=scheduled, created_at=scheduled))

    # === Add 50 unified Fuel + Mileage logs ===
    for _ in range(50):
        vehicle = random.choice(vehicles)
        gallons = round(random.uniform(5, 25), 2)
        cost = round(gallons * random.uniform(2.5, 4.0), 2)
        start_mileage = round(random.uniform(10000, 15000), 1)
        end_mileage = start_mileage + round(random.uniform(10, 300), 1)
        miles_driven = round(end_mileage - start_mileage, 1)
        date = fake.date_time_this_year()

        db.session.add(FuelLog(
            vehicle_id=vehicle.id,
            driver_id=driver.id,
            gallons=gallons,
            cost=cost,
            start_mileage=start_mileage,
            end_mileage=end_mileage,
            miles_driven=miles_driven,
            date=date
        ))

    db.session.commit()
    print("Seeded: 4 users, 50 vehicles + assignments, 50 work orders, and 50 trip logs.")
