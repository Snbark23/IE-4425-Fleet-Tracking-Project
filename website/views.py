from datetime import datetime, timedelta
from flask import Blueprint, flash, redirect, render_template, request, url_for, abort, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from website import db
from werkzeug.utils import secure_filename
import os

from .models import (
    User, Vehicle, VehicleAssignment, WorkOrder, FuelLog,
    IncidentReport, AccidentReport, MaintenanceEvent, WorkAssignment, Document, DecommissionedVehicle
)

views = Blueprint('views', __name__)

# Role-based access decorator
def role_required(role):
    def decorator(f):
        def wrapped(*args, **kwargs):
            if current_user.role != role:
                abort(403)
            return f(*args, **kwargs)
        wrapped.__name__ = f.__name__
        return wrapped
    return decorator

# Home routing
@views.route('/')
@login_required
def home():
    if current_user.role == 'HR Admin':
        return redirect(url_for('views.hr_admin'))
    elif current_user.role == 'Fleet Manager':
        return redirect(url_for('views.fleet_manager'))
    elif current_user.role == 'Driver Employee':
        return redirect(url_for('views.driver_employee'))
    elif current_user.role == 'Clerical Employee':
        return redirect(url_for('views.clerical_employee'))
    else:
        abort(403)

@views.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')

        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if new_password and new_password == confirm_password:
            from werkzeug.security import generate_password_hash
            current_user.password = generate_password_hash(new_password)

        db.session.commit()
        flash('Profile updated successfully.', 'success')

    return render_template('profile.html')


# HR Admin Portal
@views.route('/hr-admin', methods=['GET', 'POST'])
@login_required
@role_required('HR Admin')
def hr_admin():
    users = User.query.all()
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        new_role = request.form.get('new_role')
        user = User.query.get(user_id)
        if user:
            user.role = new_role
            db.session.commit()
            flash(f'Role updated for {user.first_name} to {new_role}', 'success')
    return render_template('hr_admin/hr_admin.html', users=users, roles=["Fleet Manager", "Driver Employee", "Clerical Employee", "HR Admin"])

# Fleet Manager Portal
@views.route('/fleet-manager')
@login_required
@role_required('Fleet Manager')
def fleet_manager():
    vehicle_count = Vehicle.query.count()
    assignment_count = VehicleAssignment.query.count()
    total_fuel_cost = db.session.query(func.coalesce(func.sum(FuelLog.cost), 0)).scalar()
    total_miles = db.session.query(func.coalesce(func.sum(FuelLog.miles_driven), 0)).scalar()

    incident_count = IncidentReport.query.count()
    accident_count = AccidentReport.query.count()
    maintenance_count = MaintenanceEvent.query.count()

    vehicle_kpis = db.session.query(
        Vehicle,
        func.coalesce(func.sum(FuelLog.gallons), 0).label('total_fuel'),
        func.coalesce(func.sum(FuelLog.cost), 0).label('total_cost'),
        func.coalesce(func.sum(FuelLog.miles_driven), 0).label('total_miles')
    ).outerjoin(FuelLog, FuelLog.vehicle_id == Vehicle.id).group_by(Vehicle.id).all()

    vehicle_kpis_formatted = [
        {
            'vehicle': v,
            'total_fuel': total_fuel,
            'total_cost': total_cost,
            'total_miles': total_miles
        }
        for v, total_fuel, total_cost, total_miles in vehicle_kpis
    ]

    return render_template("fleet_manager/fleet_manager.html",
        vehicle_count=vehicle_count,
        assignment_count=assignment_count,
        total_fuel_cost=total_fuel_cost,
        total_miles=total_miles,
        incident_count=incident_count,
        accident_count=accident_count,
        maintenance_count=maintenance_count,
        vehicle_kpis=vehicle_kpis_formatted
    )

@views.route('/vehicle-identification')
@login_required
@role_required('Fleet Manager')
def vehicle_identification():
    vehicles = Vehicle.query.all()
    return render_template('fleet_manager/vehicle_identification.html', vehicles=vehicles)

@views.route('/vehicle-registration', methods=['GET', 'POST'])
@login_required
@role_required('Fleet Manager')
def vehicle_registration():
    if request.method == 'POST':
        new_vehicle = Vehicle(
            vin=request.form.get('vin'),
            make=request.form.get('make'),
            model=request.form.get('model'),
            year=request.form.get('year'),
            engine_type=request.form.get('engine_type'),
            displacement=request.form.get('displacement'),
            cylinders=request.form.get('cylinders'),
            fuel_type=request.form.get('fuel_type')
        )
        db.session.add(new_vehicle)
        db.session.commit()
        flash('Vehicle registered!', 'success')
    return render_template('fleet_manager/vehicle_registration.html')

@views.route('/create-work-order', methods=['GET', 'POST'])
@login_required
@role_required('Fleet Manager')
def create_work_order():
    if request.method == 'POST':
        new_order = WorkOrder(
            title=request.form.get('title'),
            description=request.form.get('description'),
            scheduled_date=datetime.strptime(request.form.get('scheduled_date'), '%Y-%m-%dT%H:%M')
        )
        db.session.add(new_order)
        db.session.commit()
        flash('Work order created successfully.', 'success')
    return render_template('fleet_manager/create_work_order.html')

@views.route('/assign-work-order', methods=['GET', 'POST'])
@login_required
@role_required('Fleet Manager')
def assign_work_order():
    work_orders = WorkOrder.query.all()
    drivers = User.query.filter_by(role='Driver Employee').all()
    assigned_vehicle_ids = [wa.vehicle_id for wa in WorkAssignment.query.all()]
    vehicles = Vehicle.query.filter(~Vehicle.id.in_(assigned_vehicle_ids)).all()

    if request.method == 'POST':
        work_order_id = request.form.get('work_order_id')
        driver_id = request.form.get('driver_id')
        vehicle_id = request.form.get('vehicle_id')

        existing = WorkAssignment.query.filter_by(work_order_id=work_order_id, driver_id=driver_id).first()
        existing_vehicle = WorkAssignment.query.filter_by(work_order_id=work_order_id, vehicle_id=vehicle_id).first()

        selected_work_order = WorkOrder.query.get(work_order_id)
        conflict = WorkAssignment.query.join(WorkOrder).filter(
            WorkAssignment.driver_id == driver_id,
            WorkOrder.scheduled_date.between(
                selected_work_order.scheduled_date - timedelta(hours=1),
                selected_work_order.scheduled_date + timedelta(hours=1)
            )
        ).first()

        if existing:
            flash('Driver already assigned to this work order.', 'danger')
        elif existing_vehicle:
            flash('Vehicle already assigned to this work order.', 'danger')
        elif conflict:
            flash('Driver is already booked at that time.', 'danger')
        else:
            db.session.add(WorkAssignment(work_order_id=work_order_id, driver_id=driver_id, vehicle_id=vehicle_id))
            db.session.commit()
            flash('Work order assignment successful.', 'success')

    return render_template('fleet_manager/assign_work_order.html',
                           work_orders=work_orders, drivers=drivers, vehicles=vehicles)

@views.route('/work-orders')
@login_required
@role_required('Fleet Manager')
def view_work_orders():
    work_orders = WorkOrder.query.all()
    return render_template('fleet_manager/work_orders.html', work_orders=work_orders)

@views.route('/fleet-status-overview')
@login_required
@role_required('Fleet Manager')
def fleet_status_overview():
    assignments = WorkAssignment.query.all()
    return render_template('fleet_manager/fleet_status_overview.html', assignments=assignments)

@views.route('/calendar')
@login_required
@role_required('Fleet Manager')
def calendar():
    events = [
        {
            'title': wo.title,
            'start': wo.scheduled_date.strftime("%Y-%m-%dT%H:%M:%S"),
            'description': wo.description
        }
        for wo in WorkOrder.query.all()
    ]
    return render_template('fleet_manager/calendar.html', events=events)

@views.route('/vehicle_decommision', methods=['GET', 'POST'])
@login_required
@role_required('Fleet Manager')
def vehicle_decommission():
    vehicles = Vehicle.query.all()
    if request.method == 'POST':
        vehicle = Vehicle.query.get(request.form.get('vehicle_id'))
        if vehicle:
            db.session.delete(vehicle)
            db.session.commit()
            flash('Vehicle decommissioned.', 'success')
    return render_template('fleet_manager/vehicle_decommission.html', vehicles=vehicles)

# Driver Employee
@views.route('/driver-portal')
@login_required
@role_required('Driver Employee')
def driver_employee():
    fuel_logs = FuelLog.query.filter_by(driver_id=current_user.id).count()
    fuel_cost = db.session.query(func.sum(FuelLog.cost)).filter_by(driver_id=current_user.id).scalar() or 0
    miles = db.session.query(func.sum(FuelLog.miles_driven)).filter_by(driver_id=current_user.id).scalar() or 0
    incidents = IncidentReport.query.filter_by(driver_id=current_user.id).count()
    accidents = AccidentReport.query.filter_by(driver_id=current_user.id).count()

    return render_template('driver_employee/driver_employee.html',
                           fuel_logs=fuel_logs,
                           fuel_cost=fuel_cost,
                           miles=miles,
                           incidents=incidents,
                           accidents=accidents)

@views.route('/log-trip', methods=['GET', 'POST'])
@login_required
@role_required('Driver Employee')
def log_trip():
    assigned_vehicle_ids = [a.vehicle_id for a in current_user.assignments]
    vehicles = Vehicle.query.filter(Vehicle.id.in_(assigned_vehicle_ids)).all()

    if request.method == 'POST':
        vehicle_id = request.form.get('vehicle_id')
        gallons = float(request.form.get('gallons'))
        cost = float(request.form.get('cost'))
        start = float(request.form.get('start_mileage'))
        end = float(request.form.get('end_mileage'))
        miles = end - start

        log = FuelLog(
            vehicle_id=vehicle_id,
            driver_id=current_user.id,
            gallons=gallons,
            cost=cost,
            start_mileage=start,
            end_mileage=end,
            miles_driven=miles
        )
        db.session.add(log)
        db.session.commit()
        flash('Trip log submitted successfully.', 'success')

    logs = FuelLog.query.filter_by(driver_id=current_user.id).order_by(FuelLog.date.desc()).all()
    return render_template('driver_employee/log_trip.html', vehicles=vehicles, logs=logs)

@views.route('/get_last_mileage/<int:vehicle_id>')
@login_required
@role_required('Driver Employee')
def get_last_mileage(vehicle_id):
    last_log = FuelLog.query.filter_by(vehicle_id=vehicle_id, driver_id=current_user.id)\
        .order_by(FuelLog.date.desc()).first()
    return jsonify({'last_mileage': last_log.end_mileage if last_log else 0})

# Clerical Employee Portal Dashboard
@views.route('/clerical-portal')
@login_required
@role_required('Clerical Employee')
def clerical_employee():
    maintenance_events = MaintenanceEvent.query.count()
    maintenance_cost = db.session.query(db.func.sum(MaintenanceEvent.cost)).scalar() or 0
    documents_uploaded = Document.query.count()

    return render_template('clerical_employee/clerical_employee.html',
                           maintenance_events=maintenance_events,
                           maintenance_cost=maintenance_cost,
                           documents_uploaded=documents_uploaded)

# Maintenance Events Logging & View
@views.route('/maintenance-events', methods=['GET', 'POST'])
@login_required
@role_required('Clerical Employee')
def maintenance_events():
    vehicles = Vehicle.query.all()

    if request.method == 'POST':
        vehicle_id = request.form.get('vehicle_id')
        description = request.form.get('description')
        maintenance_date = request.form.get('maintenance_date')
        cost = request.form.get('cost')

        maintenance = MaintenanceEvent(
            vehicle_id=vehicle_id,
            description=description,
            maintenance_date=maintenance_date,
            cost=cost
        )
        db.session.add(maintenance)
        db.session.commit()
        flash('Maintenance event logged.', 'success')

    events = MaintenanceEvent.query.all()
    return render_template('clerical_employee/maintenance_events.html',
                           vehicles=vehicles, events=events)

# Document Upload
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')

@views.route('/upload-document', methods=['GET', 'POST'])
@login_required
@role_required('Clerical Employee')
def upload_document():
    if request.method == 'POST':
        file = request.files['document']
        if file:
            filename = secure_filename(file.filename)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)

            new_doc = Document(filename=filename, uploaded_by=current_user.id)
            db.session.add(new_doc)
            db.session.commit()
            flash('Document uploaded successfully.', 'success')
            return redirect(url_for('views.upload_document'))

    docs = Document.query.all()
    return render_template('clerical_employee/upload_document.html', documents=docs)

# Download Documents
@views.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# Delete Uploaded Documents
@views.route('/delete-document/<int:doc_id>', methods=['POST'])
@login_required
@role_required('Clerical Employee')
def delete_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    file_path = os.path.join(UPLOAD_FOLDER, doc.filename)

    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(doc)
    db.session.commit()
    flash(f'Deleted {doc.filename}', 'success')
    return redirect(url_for('views.upload_document'))

@views.route('/my-assignments')
@login_required
def my_assignments():
    active_assignments = WorkAssignment.query.filter(
        WorkAssignment.driver_id == current_user.id,
        WorkAssignment.status.in_(['Assigned', 'In Progress'])
    ).all()

    completed_assignments = WorkAssignment.query.filter_by(
        driver_id=current_user.id,
        status='Completed'
    ).all()

    if current_user.role == "Driver Employee":
        return render_template(
            'driver_employee/my_assignments.html',
            active_assignments=active_assignments,
            completed_assignments=completed_assignments
        )
    elif current_user.role == "Clerical Employee":
        return render_template(
            'clerical_employee/my_assignments.html',
            active_assignments=active_assignments,
            completed_assignments=completed_assignments
        )
    else:
        flash("Unauthorized role for this page.", "danger")
        return redirect(url_for('views.home'))
