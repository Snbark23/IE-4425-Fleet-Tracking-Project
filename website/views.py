from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, current_user
from functools import wraps
from flask import abort
from website import db
import os
from werkzeug.utils import secure_filename
from flask import send_from_directory
from website.models import Document  # <- make sure Document is imported

from website.models import User, Vehicle, VehicleAssignment, FuelLog, IncidentReport, AccidentReport, MileageLog, MaintenanceEvent

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

# Fleet Manager Portal
@views.route('/fleet-manager')
@login_required
@role_required('Fleet Manager')
def fleet_manager():
    return render_template('fleet_manager/fleet_manager.html', user=current_user)

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

@views.route('/vehicle-decommission', methods=['GET', 'POST'])
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


@views.route('/vehicle-assignment', methods=['GET', 'POST'])
@login_required
@role_required('Fleet Manager')
def vehicle_assignment():
    vehicles = Vehicle.query.all()
    drivers = User.query.filter_by(role='Driver Employee').all()
    
    if request.method == 'POST':
        vehicle_id = request.form.get('vehicle_id')
        driver_id = request.form.get('driver_id')
        assignment = VehicleAssignment(vehicle_id=vehicle_id, driver_id=driver_id)
        db.session.add(assignment)
        db.session.commit()
        flash('Vehicle assigned successfully.', 'success')

    assignments = VehicleAssignment.query.all()
    return render_template('fleet_manager/vehicle_assignment.html', vehicles=vehicles, drivers=drivers, assignments=assignments, user=current_user)

# Driver Employee Portal
@views.route('/driver-portal')
@login_required
@role_required('Driver Employee')
def driver_employee():
    return render_template('driver_employee/driver_employee.html', user=current_user)

@views.route('/fuel-log', methods=['GET', 'POST'])
@login_required
@role_required('Driver Employee')
def fuel_log():
    vehicles = Vehicle.query.filter_by(owner_id=current_user.id).all()
    
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


# Clerical Employee Portal
@views.route('/clerical-portal')
@login_required
@role_required('Clerical Employee')
def clerical_employee():
    return render_template('clerical_employee/clerical_employee.html', user=current_user)

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
    return render_template('403.html'), 403
