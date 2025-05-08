from datetime import datetime
from datetime import timedelta
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, current_user
from functools import wraps
from flask import abort
from sqlalchemy import func
from website import db
import os
from werkzeug.utils import secure_filename
from flask import send_from_directory
from .models import Document, WorkAssignment, WorkOrder
from .models import User, Vehicle, VehicleAssignment, FuelLog, IncidentReport, AccidentReport, MileageLog, MaintenanceEvent, WorkAssignment, DecommissionedVehicle


views = Blueprint('views', __name__)

# Role-based access control decorator
def role_required(role):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if current_user.role != role:
                abort(403)  # Forbidden
            return f(*args, **kwargs)
        return wrapped
    return decorator

# Determines which portal the user goes to
@views.route('/')
@login_required
def home():
    # Redirect based on role after login
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

# Goes to the HR Admin Portal
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

    return render_template('hr_admin/hr_admin.html', users=users, roles=["Fleet Manager", "Driver Employee", "Clerical Employee", "HR Admin"], user=current_user)

@views.route('/fleet-manager')
@login_required
@role_required('Fleet Manager')
def fleet_manager():
    vehicle_count = Vehicle.query.count()
    assignment_count = VehicleAssignment.query.count()

    # Total fuel cost and mileage
    total_fuel_cost = db.session.query(func.coalesce(func.sum(FuelLog.cost), 0)).scalar()
    total_miles = db.session.query(func.coalesce(func.sum(MileageLog.miles_driven), 0)).scalar()

    # Incidents, accidents, and maintenance
    incident_count = IncidentReport.query.count()
    accident_count = AccidentReport.query.count()
    maintenance_count = MaintenanceEvent.query.count()

    # KPIs per vehicle
    vehicle_kpis = db.session.query(
        Vehicle,
        func.coalesce(func.sum(FuelLog.gallons), 0).label('total_fuel'),
        func.coalesce(func.sum(FuelLog.cost), 0).label('total_cost'),
        func.coalesce(func.sum(MileageLog.miles_driven), 0).label('total_miles')
    ).outerjoin(FuelLog, FuelLog.vehicle_id == Vehicle.id) \
     .outerjoin(MileageLog, MileageLog.vehicle_id == Vehicle.id) \
     .group_by(Vehicle.id).all()

    # Convert to objects
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
                       vehicle_kpis=vehicle_kpis_formatted,
                       user=current_user)


@views.route('/vehicle-identification')
@login_required
@role_required('Fleet Manager')
def vehicle_identification():
    vehicles = Vehicle.query.all()
    return render_template('fleet_manager/vehicle_identification.html', vehicles=vehicles, user=current_user)

@views.route('/vehicle-registration', methods=['GET', 'POST'])
@login_required
@role_required('Fleet Manager')
def vehicle_registration():
    if request.method == 'POST':
        vin = request.form.get('vin')
        make = request.form.get('make')
        model = request.form.get('model')
        year = request.form.get('year')
        engine_type = request.form.get('engine_type')
        displacement = request.form.get('displacement')
        cylinders = request.form.get('cylinders')
        fuel_type = request.form.get('fuel_type')

        new_vehicle = Vehicle(
            vin=vin,
            make=make,
            model=model,
            year=year,
            engine_type=engine_type,
            displacement=displacement,
            cylinders=cylinders,
            fuel_type=fuel_type
        )
        db.session.add(new_vehicle)
        db.session.commit()
        flash('Vehicle registered!', 'success')
        return redirect(url_for('views.vehicle_registration'))

    return render_template('fleet_manager/vehicle_registration.html', user=current_user)

# Create a new work order
@views.route('/create-work-order', methods=['GET', 'POST'])
@login_required
@role_required('Fleet Manager')
def create_work_order():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        scheduled_date = request.form.get('scheduled_date')

        new_order = WorkOrder(
            title=title,
            description=description,
            scheduled_date = datetime.strptime(scheduled_date, '%Y-%m-%dT%H:%M')
        )
        db.session.add(new_order)
        db.session.commit()
        flash('Work order created successfully.', 'success')
        return redirect(url_for('views.create_work_order'))

    return render_template('fleet_manager/create_work_order.html', user=current_user)

# Assign driver and vehicle to a work order
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

        # Check for duplicate assignment
        existing = WorkAssignment.query.filter_by(work_order_id=work_order_id, driver_id=driver_id).first()
        existing_vehicle = WorkAssignment.query.filter_by(work_order_id=work_order_id, vehicle_id=vehicle_id).first()

        # Get the scheduled time for this work order
        selected_work_order = WorkOrder.query.get(work_order_id)
        conflict = db.session.query(WorkAssignment).join(WorkOrder).filter(
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
            assignment = WorkAssignment(work_order_id=work_order_id, driver_id=driver_id, vehicle_id=vehicle_id)
            db.session.add(assignment)
            db.session.commit()
            flash('Work order assignment successful.', 'success')

        return redirect(url_for('views.assign_work_order'))

    return render_template('fleet_manager/assign_work_order.html',
                           work_orders=work_orders, drivers=drivers, vehicles=vehicles, user=current_user)

# View all work orders and their assignments
@views.route('/work-orders')
@login_required
@role_required('Fleet Manager')
def view_work_orders():
    work_orders = WorkOrder.query.all()
    return render_template('fleet_manager/work_orders.html', work_orders=work_orders, user=current_user)

@views.route('/calendar')
@login_required
@role_required('Fleet Manager')
def calendar():
    work_orders = WorkOrder.query.all()
    events = [{
        'title': wo.title,
        'start': wo.scheduled_date.strftime("%Y-%m-%dT%H:%M:%S"),
        'description': wo.description
    } for wo in work_orders]

    return render_template('fleet_manager/calendar.html', events=events, user=current_user)


# Fleet Manager Status View
@views.route('/fleet-status-overview')
@login_required
@role_required('Fleet Manager')
def fleet_status_overview():
    assignments = WorkAssignment.query.all()
    return render_template('fleet_manager/fleet_status_overview.html', assignments=assignments, user=current_user)

@views.route('/vehicle_decommision', methods=['GET', 'POST'])
@login_required
@role_required('Fleet Manager')
def vehicle_decommission():
    vehicles = Vehicle.query.all()
    if request.method == 'POST':
        vehicle_id = request.form.get('vehicle_id')
        vehicle = Vehicle.query.get(vehicle_id)
        if vehicle:
            db.session.delete(vehicle)
            db.session.commit()
            flash('Vehicle decommissioned.', 'success')
    return render_template('fleet_manager/vehicle_decommission.html', vehicles=vehicles, user=current_user)

# Driver Employee
@views.route('/driver-portal')
@login_required
@role_required('Driver Employee')
def driver_employee():
    fuel_logs = FuelLog.query.filter_by(driver_id=current_user.id).count()
    fuel_cost = db.session.query(db.func.sum(FuelLog.cost)).filter_by(driver_id=current_user.id).scalar() or 0
    miles = db.session.query(db.func.sum(MileageLog.miles_driven)).filter_by(driver_id=current_user.id).scalar() or 0
    incidents = IncidentReport.query.filter_by(driver_id=current_user.id).count()
    accidents = AccidentReport.query.filter_by(driver_id=current_user.id).count()

    return render_template('driver_employee/driver_employee.html',
                           user=current_user,
                           fuel_logs=fuel_logs,
                           fuel_cost=fuel_cost,
                           miles=miles,
                           incidents=incidents,
                           accidents=accidents)

# Driver Portal
@views.route('/my-assignments')
@login_required
def my_assignments():
    active_assignments = WorkAssignment.query.filter(
        WorkAssignment.driver_id == current_user.id,
        WorkAssignment.status.in_(['Assigned', 'In Progress'])
    ).all()
    completed_assignments = WorkAssignment.query.filter_by(
        driver_id=current_user.id, status='Completed'
    ).all()

    if current_user.role == "Driver Employee":
        return render_template(
            'driver_employee/my_assignments.html',
            active_assignments=active_assignments,
            completed_assignments=completed_assignments,
            user=current_user
        )
    elif current_user.role == "Clerical Employee":
        return render_template(
            'clerical_employee/my_assignments.html',
            active_assignments=active_assignments,
            completed_assignments=completed_assignments,
            user=current_user
        )
    else:
        flash("Unauthorized role for this page.", "danger")
        return redirect(url_for('views.home'))


@views.route('/update-assignment-status/<int:assignment_id>/<new_status>', methods=['POST'])
@login_required
def update_assignment_status(assignment_id, new_status):
    assignment = WorkAssignment.query.get_or_404(assignment_id)

    if assignment.driver_id != current_user.id:
        flash("Unauthorized", "danger")
        return redirect(url_for('views.home'))

    assignment.status = new_status
    db.session.commit()

    flash(f"Status updated to {new_status}", "success")

    # Redirect based on role
    if current_user.role == "Driver Employee":
        return redirect(url_for('views.my_assignments'))
    elif current_user.role == "Clerical Employee":
        return redirect(url_for('views.my_assignments'))
    else:
        return redirect(url_for('views.home'))


@views.route('/fuel-log', methods=['GET', 'POST'])
@login_required
@role_required('Driver Employee')
def fuel_log():
    assigned_vehicle_ids = [a.vehicle_id for a in current_user.assignments]
    vehicles = Vehicle.query.filter(Vehicle.id.in_(assigned_vehicle_ids)).all()

    
    if request.method == 'POST':
        vehicle_id = request.form.get('vehicle_id')
        gallons = request.form.get('gallons')
        cost = request.form.get('cost')
        fuel_entry = FuelLog(vehicle_id=vehicle_id, driver_id=current_user.id, gallons=gallons, cost=cost)
        db.session.add(fuel_entry)
        db.session.commit()
        flash('Fuel log entry added.', 'success')

    fuel_logs = FuelLog.query.filter_by(driver_id=current_user.id).all()
    return render_template('driver_employee/fuel_log.html', vehicles=vehicles, fuel_logs=fuel_logs, user=current_user)

@views.route('/accident-report', methods=['GET', 'POST'])
@login_required
@role_required('Driver Employee')
def accident_report():
    vehicles = Vehicle.query.filter_by(owner_id=current_user.id).all()

    if request.method == 'POST':
        vehicle_id = request.form.get('vehicle_id')
        description = request.form.get('description')
        damage_estimate = request.form.get('damage_estimate')
        report = AccidentReport(vehicle_id=vehicle_id, driver_id=current_user.id, description=description, damage_estimate=damage_estimate)
        db.session.add(report)
        db.session.commit()
        flash('Accident report submitted.', 'success')

    accidents = AccidentReport.query.filter_by(driver_id=current_user.id).all()
    return render_template('driver_employee/accident_report.html', vehicles=vehicles, accidents=accidents, user=current_user)

@views.route('/incident-report', methods=['GET', 'POST'])
@login_required
@role_required('Driver Employee')
def incident_report():
    vehicles = Vehicle.query.filter_by(owner_id=current_user.id).all()

    if request.method == 'POST':
        vehicle_id = request.form.get('vehicle_id')
        description = request.form.get('description')
        report = IncidentReport(vehicle_id=vehicle_id, driver_id=current_user.id, description=description)
        db.session.add(report)
        db.session.commit()
        flash('Incident report submitted.', 'success')

    incidents = IncidentReport.query.filter_by(driver_id=current_user.id).all()
    return render_template('driver_employee/incident_report.html', vehicles=vehicles, incidents=incidents, user=current_user)


@views.route('/mileage-log', methods=['GET', 'POST'])
@login_required
@role_required('Driver Employee')
def mileage_log():
    vehicles = Vehicle.query.filter_by(owner_id=current_user.id).all()

    if request.method == 'POST':
        vehicle_id = request.form.get('vehicle_id')
        miles_driven = request.form.get('miles_driven')
        entry = MileageLog(vehicle_id=vehicle_id, driver_id=current_user.id, miles_driven=miles_driven)
        db.session.add(entry)
        db.session.commit()
        flash('Mileage log submitted.', 'success')

    mileage_logs = MileageLog.query.filter_by(driver_id=current_user.id).all()
    return render_template('driver_employee/mileage_log.html', vehicles=vehicles, mileage_logs=mileage_logs, user=current_user)


@views.route('/clerical-portal')
@login_required
@role_required('Clerical Employee')
def clerical_employee():
    maintenance_events = MaintenanceEvent.query.count()
    maintenance_cost = db.session.query(db.func.sum(MaintenanceEvent.cost)).scalar() or 0
    documents_uploaded = Document.query.count()

    return render_template('clerical_employee/clerical_employee.html',
                           user=current_user,
                           maintenance_events=maintenance_events,
                           maintenance_cost=maintenance_cost,
                           documents_uploaded=documents_uploaded)

# Clerical Employee Route
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
        maintenance = MaintenanceEvent(vehicle_id=vehicle_id, description=description, maintenance_date=maintenance_date, cost=cost)
        db.session.add(maintenance)
        db.session.commit()
        flash('Maintenance event logged.', 'success')

    events = MaintenanceEvent.query.all()
    return render_template('clerical_employee/maintenance_events.html', vehicles=vehicles, events=events, user=current_user)

UPLOAD_FOLDER = UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')

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
            print("Saving to:", file_path)
            flash('Document uploaded successfully.', 'success')
            return redirect(url_for('views.upload_document'))

    docs = Document.query.all()
    return render_template('clerical_employee/upload_document.html', documents=docs, user=current_user)

@views.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@views.route('/delete-document/<int:doc_id>', methods=['POST'])
@login_required
@role_required('Clerical Employee')
def delete_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    file_path = os.path.join(UPLOAD_FOLDER, doc.filename)

    # Remove from filesystem
    if os.path.exists(file_path):
        os.remove(file_path)

    # Remove from database
    db.session.delete(doc)
    db.session.commit()
    flash(f'Deleted {doc.filename}', 'success')

    return redirect(url_for('views.upload_document'))

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
            current_user.password = generate_password_hash(new_password, method='pbkdf2:sha256')

        db.session.commit()
        flash('Profile updated successfully.', 'success')

    return render_template('profile.html', user=current_user)

@views.app_errorhandler(403)
def forbidden(e):
    return render_template('403.html', user=current_user), 403

