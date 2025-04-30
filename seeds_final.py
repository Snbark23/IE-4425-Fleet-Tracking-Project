import sys
import os
from faker import Faker
import random
from datetime import datetime
from werkzeug.security import generate_password_hash

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from website import create_app, db
from website.models import User, Vehicle, WorkOrder, FuelLog, MileageLog

app = create_app()
fake = Faker()

with app.app_context():
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
        if not User.query.filter_by(email=user.email).first():
            db.session.add(user)

    # === Add 50 vehicles ===
    makes = ['Ford', 'Toyota', 'Chevy', 'Nissan', 'Honda']
    models = ['F-150', 'Camry', 'Silverado', 'Altima', 'Civic']

    for _ in range(50):
        make = random.choice(makes)
        model = random.choice(models)
        vin = fake.unique.bothify(text='???#####??###???')
        db.session.add(Vehicle(make=make, model=model, vin=vin))

    # === Add 50 work orders ===
    for i in range(50):
        title = f"Work Order {i+1}"
        description = fake.sentence()
        scheduled = fake.date_time_this_year()
        db.session.add(WorkOrder(title=title, description=description, scheduled_date=scheduled, created_at=scheduled))

    # === Add 50 fuel logs ===
    for _ in range(50):
        vehicle_id = random.randint(1, 50)
        gallons = round(random.uniform(5, 25), 2)
        cost = round(gallons * random.uniform(2.5, 4.0), 2)
        date = fake.date_time_this_year()
        db.session.add(FuelLog(vehicle_id=vehicle_id, gallons=gallons, cost=cost, date=date))

    # === Add 50 mileage logs ===
    for _ in range(50):
        vehicle_id = random.randint(1, 50)
        miles = round(random.uniform(10, 300), 1)
        date = fake.date_time_this_year()
        db.session.add(MileageLog(vehicle_id=vehicle_id, miles_driven=miles, date=date))

    db.session.commit()
    print("Added 4 use-case users + 50 vehicles, work orders, fuel logs, and mileage logs.")
