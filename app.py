# app.py - Complete Production Application (No Demo Info)
import os
import sys
import json
import socket
import webbrowser
import threading
import time
from datetime import datetime, timedelta
from functools import wraps
from dotenv import load_dotenv

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration - All sensitive data from environment variables
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24).hex())
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///laachir_tech.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_PERMANENT'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Create upload folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page'


# ==================== DATABASE MODELS ====================

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='technician')
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Client(db.Model):
    __tablename__ = 'clients'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.String(200))
    city = db.Column(db.String(50), default='Marrakech')
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    interventions = db.relationship('Intervention', backref='client', lazy=True)


class Intervention(db.Model):
    __tablename__ = 'interventions'

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(50), unique=True, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    address = db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending')
    payment_status = db.Column(db.String(20), default='locked')
    amount = db.Column(db.Float, default=0)
    deposit_received = db.Column(db.Float, default=0)
    technician_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    scheduled_date = db.Column(db.DateTime)
    completed_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    priority = db.Column(db.String(10), default='medium')

    technician = db.relationship('User', foreign_keys=[technician_id])


class InterventionReport(db.Model):
    __tablename__ = 'intervention_reports'

    id = db.Column(db.Integer, primary_key=True)
    intervention_id = db.Column(db.Integer, db.ForeignKey('interventions.id'), nullable=False)
    status_update = db.Column(db.String(20))
    notes = db.Column(db.Text)
    parts_used = db.Column(db.Text)
    photos_before = db.Column(db.String(500))
    photos_after = db.Column(db.String(500))
    signature = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    intervention = db.relationship('Intervention', backref='reports')


class Part(db.Model):
    __tablename__ = 'parts'

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    quantity_in_stock = db.Column(db.Integer, default=0)
    unit_price = db.Column(db.Float, default=0)


class TechnicianLocation(db.Model):
    __tablename__ = 'technician_locations'

    id = db.Column(db.Integer, primary_key=True)
    technician_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    status = db.Column(db.String(20), default='available')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    technician = db.relationship('User', foreign_keys=[technician_id])


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ==================== HELPER FUNCTIONS ====================

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role not in roles:
                flash('Accès non autorisé', 'error')
                return redirect(url_for('dashboard' if current_user.role == 'manager' else 'tech_dashboard'))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def generate_intervention_ref():
    year = datetime.now().strftime('%Y')
    count = Intervention.query.filter(
        Intervention.reference.like(f'INT-{year}-%')
    ).count() + 1
    return f'INT-{year}-{count:03d}'


# ==================== BASIC ROUTES ====================

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'manager':
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('tech_dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.is_active:
            login_user(user)
            session.permanent = True
            flash('Connexion réussie !', 'success')
            if user.role == 'manager':
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('tech_dashboard'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
@role_required('manager')
def dashboard():
    return render_template('manager_dashboard.html')


@app.route('/tech-dashboard')
@login_required
@role_required('technician')
def tech_dashboard():
    return render_template('tech_dashboard.html')


# ==================== API ROUTES - KPI & DASHBOARD ====================

@app.route('/api/kpi-data')
@login_required
@role_required('manager')
def get_kpi_data():
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    interventions_today = Intervention.query.filter(
        Intervention.scheduled_date.between(today_start, today_end)
    ).count()

    completed_today = Intervention.query.filter(
        Intervention.status == 'completed',
        Intervention.completed_date.between(today_start, today_end)
    ).count()

    pending_deposits = Intervention.query.filter_by(payment_status='locked').count()

    total_collected = db.session.query(db.func.sum(Intervention.deposit_received)).filter(
        Intervention.payment_status == 'unlocked'
    ).scalar() or 0

    return jsonify({
        'interventions_today': interventions_today,
        'completed_today': completed_today,
        'pending_deposits': pending_deposits,
        'total_collected': int(total_collected)
    })


@app.route('/api/interventions')
@login_required
def get_interventions():
    if current_user.role == 'manager':
        interventions = Intervention.query.order_by(Intervention.created_at.desc()).all()
    else:
        interventions = Intervention.query.filter_by(technician_id=current_user.id).order_by(
            Intervention.scheduled_date).all()

    return jsonify([{
        'id': i.id,
        'reference': i.reference,
        'client_name': i.client.name,
        'type': i.type,
        'address': i.address,
        'status': i.status,
        'payment_status': i.payment_status,
        'amount': i.amount,
        'technician': i.technician.full_name if i.technician else 'Non assigné',
        'technician_id': i.technician_id,
        'scheduled_date': i.scheduled_date.isoformat() if i.scheduled_date else None,
        'priority': i.priority
    } for i in interventions])


# ==================== API ROUTES - INTERVENTIONS ====================

@app.route('/api/intervention/<int:id>')
@login_required
def get_intervention(id):
    intervention = Intervention.query.get_or_404(id)
    return jsonify({
        'id': intervention.id,
        'reference': intervention.reference,
        'client_id': intervention.client_id,
        'client_name': intervention.client.name,
        'client_phone': intervention.client.phone,
        'client_address': intervention.client.address,
        'client_lat': intervention.client.lat,
        'client_lng': intervention.client.lng,
        'type': intervention.type,
        'description': intervention.description,
        'address': intervention.address,
        'status': intervention.status,
        'payment_status': intervention.payment_status,
        'amount': intervention.amount,
        'deposit_received': intervention.deposit_received,
        'technician_id': intervention.technician_id,
        'scheduled_date': intervention.scheduled_date.isoformat() if intervention.scheduled_date else None,
        'priority': intervention.priority
    })


@app.route('/api/intervention', methods=['POST'])
@login_required
@role_required('manager')
def create_intervention():
    try:
        data = request.json

        if not data.get('client_id'):
            return jsonify({'error': 'Client requis'}), 400

        deposit = float(data.get('deposit_received', 0)) if data.get('deposit_received') else float(
            data.get('amount', 0)) * 0.7

        intervention = Intervention(
            reference=generate_intervention_ref(),
            client_id=data['client_id'],
            type=data['type'],
            description=data.get('description', ''),
            address=data.get('address', ''),
            amount=float(data.get('amount', 0)),
            deposit_received=deposit,
            technician_id=data.get('technician_id') if data.get('technician_id') else None,
            scheduled_date=datetime.fromisoformat(data['scheduled_date']) if data.get(
                'scheduled_date') else datetime.now(),
            priority=data.get('priority', 'medium')
        )
        db.session.add(intervention)
        db.session.commit()

        return jsonify({'success': True, 'reference': intervention.reference, 'id': intervention.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/intervention/<int:id>/payment', methods=['PUT'])
@login_required
@role_required('manager')
def update_payment_status(id):
    intervention = Intervention.query.get_or_404(id)
    intervention.payment_status = 'unlocked'
    db.session.commit()
    return jsonify({'success': True})


# ==================== INTERVENTION MANAGEMENT ROUTES ====================

@app.route('/api/intervention/<int:id>/status', methods=['PUT'])
@login_required
@role_required('manager')
def update_intervention_status(id):
    """Update intervention status (for drag & drop)"""
    try:
        intervention = Intervention.query.get_or_404(id)
        data = request.json
        intervention.status = data.get('status', intervention.status)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/intervention/<int:id>/financial', methods=['PUT'])
@login_required
@role_required('manager')
def update_intervention_financial(id):
    """Update intervention amount and deposit"""
    try:
        intervention = Intervention.query.get_or_404(id)
        data = request.json
        intervention.amount = float(data.get('amount', intervention.amount))
        intervention.deposit_received = float(data.get('deposit_received', intervention.deposit_received))

        # Auto-unlock if deposit reaches 70% or more
        if intervention.deposit_received >= intervention.amount * 0.7:
            intervention.payment_status = 'unlocked'

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/intervention/<int:id>', methods=['PUT'])
@login_required
@role_required('manager')
def update_intervention(id):
    """Update intervention priority and technician"""
    try:
        intervention = Intervention.query.get_or_404(id)
        data = request.json

        if 'priority' in data:
            intervention.priority = data['priority']
        if 'technician_id' in data:
            intervention.technician_id = data['technician_id']

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/intervention/<int:id>', methods=['DELETE'])
@login_required
@role_required('manager')
def delete_intervention(id):
    """Delete an intervention"""
    try:
        intervention = Intervention.query.get_or_404(id)

        # Delete associated reports first
        InterventionReport.query.filter_by(intervention_id=id).delete()

        db.session.delete(intervention)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==================== API ROUTES - CLIENTS ====================

@app.route('/api/clients', methods=['GET'])
@login_required
def get_clients():
    clients = Client.query.order_by(Client.name).all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'contact_person': c.contact_person,
        'phone': c.phone,
        'email': c.email,
        'address': c.address,
        'city': c.city,
        'lat': c.lat,
        'lng': c.lng,
        'notes': c.notes,
        'interventions': [{'id': i.id, 'reference': i.reference} for i in c.interventions]
    } for c in clients])


@app.route('/api/clients/<int:id>', methods=['GET'])
@login_required
def get_client(id):
    client = Client.query.get_or_404(id)
    return jsonify({
        'id': client.id,
        'name': client.name,
        'contact_person': client.contact_person,
        'phone': client.phone,
        'email': client.email,
        'address': client.address,
        'city': client.city,
        'lat': client.lat,
        'lng': client.lng,
        'notes': client.notes
    })


@app.route('/api/clients', methods=['POST'])
@login_required
@role_required('manager')
def create_client():
    try:
        data = request.json

        if not data.get('name'):
            return jsonify({'error': 'Le nom du client est requis'}), 400

        client = Client(
            name=data['name'],
            contact_person=data.get('contact_person', ''),
            phone=data.get('phone', ''),
            email=data.get('email', ''),
            address=data.get('address', ''),
            city=data.get('city', 'Marrakech'),
            lat=data.get('lat') if data.get('lat') else None,
            lng=data.get('lng') if data.get('lng') else None,
            notes=data.get('notes', '')
        )
        db.session.add(client)
        db.session.commit()

        return jsonify({'success': True, 'id': client.id, 'message': 'Client créé avec succès'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/clients/<int:id>', methods=['PUT'])
@login_required
@role_required('manager')
def update_client(id):
    try:
        client = Client.query.get_or_404(id)
        data = request.json

        client.name = data.get('name', client.name)
        client.contact_person = data.get('contact_person', client.contact_person)
        client.phone = data.get('phone', client.phone)
        client.email = data.get('email', client.email)
        client.address = data.get('address', client.address)
        client.city = data.get('city', client.city)
        client.lat = data.get('lat') if data.get('lat') else None
        client.lng = data.get('lng') if data.get('lng') else None
        client.notes = data.get('notes', client.notes)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Client mis à jour'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/clients/<int:id>', methods=['DELETE'])
@login_required
@role_required('manager')
def delete_client(id):
    try:
        client = Client.query.get_or_404(id)

        if client.interventions:
            return jsonify({'error': 'Impossible de supprimer un client avec des interventions existantes'}), 400

        db.session.delete(client)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Client supprimé'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/clients/<int:id>/history')
@login_required
def get_client_history(id):
    client = Client.query.get_or_404(id)
    interventions = Intervention.query.filter_by(client_id=id).order_by(Intervention.created_at.desc()).all()

    return jsonify({
        'client': {
            'name': client.name,
            'contact_person': client.contact_person,
            'phone': client.phone,
            'email': client.email,
            'address': client.address,
            'city': client.city,
            'lat': client.lat,
            'lng': client.lng
        },
        'interventions': [{
            'id': i.id,
            'reference': i.reference,
            'type': i.type,
            'status': i.status,
            'amount': i.amount,
            'date': i.created_at.isoformat(),
            'technician': i.technician.full_name if i.technician else None
        } for i in interventions]
    })


# ==================== API ROUTES - TECHNICIANS ====================

@app.route('/api/technicians')
@login_required
def get_technicians():
    technicians = User.query.filter_by(role='technician', is_active=True).all()
    result = []
    for t in technicians:
        location = TechnicianLocation.query.filter_by(technician_id=t.id).first()
        result.append({
            'id': t.id,
            'full_name': t.full_name,
            'phone': t.phone,
            'status': location.status if location else 'available',
            'lat': location.lat if location else None,
            'lng': location.lng if location else None
        })
    return jsonify(result)


# ==================== API ROUTES - GPS GEOLOCATION ====================

@app.route('/api/technician/update-location', methods=['POST'])
@login_required
@role_required('technician')
def update_technician_gps():
    """Update technician's current GPS location"""
    try:
        data = request.json
        location = TechnicianLocation.query.filter_by(technician_id=current_user.id).first()

        if not location:
            location = TechnicianLocation(technician_id=current_user.id)
            db.session.add(location)

        location.lat = data.get('lat')
        location.lng = data.get('lng')
        location.status = data.get('status', location.status)
        location.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True, 'message': 'Position mise à jour'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/technician/current-location', methods=['GET'])
@login_required
def get_technician_gps():
    """Get technician's current location"""
    location = TechnicianLocation.query.filter_by(technician_id=current_user.id).first()
    if location:
        return jsonify({
            'lat': location.lat,
            'lng': location.lng,
            'status': location.status,
            'updated_at': location.updated_at.isoformat()
        })
    return jsonify({'error': 'No location found'}), 404


@app.route('/api/map/technicians', methods=['GET'])
@login_required
@role_required('manager')
def get_all_technicians_location():
    """Get all technicians locations for the map"""
    try:
        locations = db.session.query(TechnicianLocation, User).join(
            User, TechnicianLocation.technician_id == User.id
        ).filter(User.is_active == True).all()

        result = []
        for loc, user in locations:
            result.append({
                'technician_id': user.id,
                'name': user.full_name,
                'phone': user.phone,
                'lat': loc.lat,
                'lng': loc.lng,
                'status': loc.status,
                'updated_at': loc.updated_at.isoformat() if loc.updated_at else None
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/map/clients', methods=['GET'])
@login_required
def get_clients_with_coordinates():
    """Get all clients with GPS coordinates"""
    try:
        clients = Client.query.filter(
            Client.lat.isnot(None),
            Client.lng.isnot(None)
        ).all()

        result = []
        for client in clients:
            result.append({
                'id': client.id,
                'name': client.name,
                'address': client.address,
                'lat': client.lat,
                'lng': client.lng,
                'phone': client.phone
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== API ROUTES - TECHNICIAN MISSIONS ====================

@app.route('/api/technician/missions')
@login_required
@role_required('technician')
def get_technician_missions():
    missions = Intervention.query.filter(
        Intervention.technician_id == current_user.id
    ).order_by(Intervention.scheduled_date).all()

    return jsonify([{
        'id': m.id,
        'reference': m.reference,
        'client_name': m.client.name,
        'client_phone': m.client.phone,
        'client_address': m.client.address,
        'client_lat': m.client.lat,
        'client_lng': m.client.lng,
        'type': m.type,
        'address': m.address,
        'status': m.status,
        'payment_status': m.payment_status,
        'amount': m.amount,
        'scheduled_date': m.scheduled_date.isoformat() if m.scheduled_date else None
    } for m in missions])


@app.route('/api/technician/mission/<int:mission_id>/start', methods=['POST'])
@login_required
@role_required('technician')
def start_mission(mission_id):
    mission = Intervention.query.get_or_404(mission_id)
    if mission.technician_id != current_user.id:
        return jsonify({'error': 'Non autorisé'}), 403

    mission.status = 'in_progress'
    db.session.commit()

    location = TechnicianLocation.query.filter_by(technician_id=current_user.id).first()
    if location:
        location.status = 'on_mission'
        db.session.commit()

    return jsonify({'success': True, 'status': 'started'})


@app.route('/api/technician/mission/<int:mission_id>/complete', methods=['POST'])
@login_required
@role_required('technician')
def complete_mission(mission_id):
    mission = Intervention.query.get_or_404(mission_id)
    if mission.technician_id != current_user.id:
        return jsonify({'error': 'Non autorisé'}), 403

    mission.status = 'completed'
    mission.completed_date = datetime.utcnow()
    db.session.commit()

    location = TechnicianLocation.query.filter_by(technician_id=current_user.id).first()
    if location:
        location.status = 'available'
        db.session.commit()

    return jsonify({'success': True, 'status': 'completed'})


@app.route('/api/technician/report', methods=['POST'])
@login_required
@role_required('technician')
def submit_mission_report():
    try:
        data = request.json

        report = InterventionReport(
            intervention_id=data['intervention_id'],
            status_update=data.get('status', 'completed'),
            notes=data.get('notes', ''),
            parts_used=json.dumps(data.get('parts_used', [])),
            photos_before=data.get('photos_before'),
            photos_after=data.get('photos_after'),
            signature=data.get('signature')
        )
        db.session.add(report)

        intervention = Intervention.query.get(data['intervention_id'])
        if intervention:
            intervention.status = 'completed'
            intervention.completed_date = datetime.utcnow()

        db.session.commit()

        return jsonify({'success': True, 'report_id': report.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/technician/mission/<int:mission_id>/client-location', methods=['GET'])
@login_required
def get_mission_client_location(mission_id):
    mission = Intervention.query.get_or_404(mission_id)
    return jsonify({
        'client_name': mission.client.name,
        'address': mission.client.address,
        'lat': mission.client.lat,
        'lng': mission.client.lng,
        'phone': mission.client.phone
    })


# ==================== API ROUTES - PARTS ====================

@app.route('/api/parts')
@login_required
def get_parts():
    parts = Part.query.all()
    return jsonify([{
        'id': p.id,
        'reference': p.reference,
        'name': p.name,
        'description': p.description,
        'quantity_in_stock': p.quantity_in_stock,
        'unit_price': p.unit_price
    } for p in parts])


# ==================== API ROUTES - USER MANAGEMENT ====================

@app.route('/api/users')
@login_required
@role_required('manager')
def get_users():
    users = User.query.all()
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'email': u.email,
        'full_name': u.full_name,
        'phone': u.phone,
        'role': u.role,
        'is_active': u.is_active,
        'created_at': u.created_at.isoformat()
    } for u in users])


@app.route('/api/users/<int:user_id>')
@login_required
@role_required('manager')
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'phone': user.phone,
        'role': user.role,
        'is_active': user.is_active
    })


@app.route('/api/users', methods=['POST'])
@login_required
@role_required('manager')
def create_user():
    try:
        data = request.json

        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Ce nom d\'utilisateur existe déjà'}), 400

        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Cet email existe déjà'}), 400

        if not data.get('password'):
            return jsonify({'error': 'Le mot de passe est requis'}), 400

        user = User(
            username=data['username'],
            email=data['email'],
            full_name=data['full_name'],
            phone=data.get('phone', ''),
            role=data.get('role', 'technician'),
            is_active=True
        )
        user.set_password(data['password'])

        db.session.add(user)
        db.session.commit()

        if user.role == 'technician':
            location = TechnicianLocation(technician_id=user.id, lat=31.6295, lng=-7.9811, status='available')
            db.session.add(location)
            db.session.commit()

        return jsonify({'success': True, 'id': user.id, 'message': 'Utilisateur créé avec succès'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
@role_required('manager')
def update_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        data = request.json

        if data['username'] != user.username:
            if User.query.filter_by(username=data['username']).first():
                return jsonify({'error': 'Ce nom d\'utilisateur existe déjà'}), 400

        if data['email'] != user.email:
            if User.query.filter_by(email=data['email']).first():
                return jsonify({'error': 'Cet email existe déjà'}), 400

        user.username = data['username']
        user.email = data['email']
        user.full_name = data['full_name']
        user.phone = data.get('phone', '')
        user.role = data.get('role', user.role)

        if data.get('password'):
            user.set_password(data['password'])

        db.session.commit()

        return jsonify({'success': True, 'message': 'Utilisateur mis à jour'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
@role_required('manager')
def delete_user(user_id):
    try:
        user = User.query.get_or_404(user_id)

        if user.id == current_user.id:
            return jsonify({'error': 'Vous ne pouvez pas supprimer votre propre compte'}), 400

        if user.role == 'manager':
            manager_count = User.query.filter_by(role='manager', is_active=True).count()
            if manager_count <= 1:
                return jsonify({'error': 'Impossible de supprimer le dernier compte gérant'}), 400

        if user.role == 'technician':
            TechnicianLocation.query.filter_by(technician_id=user.id).delete()

        db.session.delete(user)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Utilisateur supprimé'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/users/<int:user_id>/status', methods=['PUT'])
@login_required
@role_required('manager')
def toggle_user_status(user_id):
    try:
        user = User.query.get_or_404(user_id)
        data = request.json

        if user.id == current_user.id and not data.get('is_active', True):
            return jsonify({'error': 'Vous ne pouvez pas désactiver votre propre compte'}), 400

        if user.role == 'manager' and not data.get('is_active', True):
            manager_count = User.query.filter_by(role='manager', is_active=True).count()
            if manager_count <= 1:
                return jsonify({'error': 'Impossible de désactiver le dernier compte gérant'}), 400

        user.is_active = data.get('is_active', True)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Statut utilisateur mis à jour'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==================== DATABASE INITIALIZATION ====================

def init_db():
    """Initialize database with default data"""
    try:
        db.create_all()
        print("✅ Database tables ready")

        # Only create a default manager if no users exist at all
        if User.query.count() == 0:
            print("📝 Creating default administrator account...")
            print("⚠️  PLEASE CHANGE THE DEFAULT PASSWORD AFTER FIRST LOGIN!")

            # Create ONLY a default manager account - no demo technician accounts
            manager = User(
                username='admin',
                email='admin@laachir-tech.ma',
                full_name='Administrateur',
                role='manager',
                phone=''
            )
            # Use a secure random password that must be changed
            import secrets
            temp_password = secrets.token_urlsafe(8)
            manager.set_password(temp_password)
            db.session.add(manager)
            db.session.commit()

            print(f"✅ Default administrator created:")
            print(f"   Username: admin")
            print(f"   Temporary password: {temp_password}")
            print(f"   ⚠️  CHANGE THIS PASSWORD IMMEDIATELY AFTER FIRST LOGIN!")

        else:
            print(f"✅ Database already contains {User.query.count()} users")

        print("🎉 Database initialization complete!")
    except Exception as e:
        print(f"⚠️ Error initializing database: {e}")
        db.session.rollback()


# ==================== LOCAL DEVELOPMENT SERVER ====================

def find_free_port():
    """Find an available port starting from 5000"""
    for port in range(5000, 5010):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    return 5000


def open_browser(port):
    """Open browser after a short delay"""
    time.sleep(2)
    webbrowser.open(f'http://127.0.0.1:{port}')


if __name__ == '__main__':
    port = find_free_port()

    print("\n" + "=" * 60)
    print("❄️  LAACHIR-TECH PME - Application de Gestion")
    print("=" * 60)
    print(f"🌐 Server started at: http://127.0.0.1:{port}")
    print("\n📋 First-time setup:")
    print("   1. Login with the generated admin credentials shown above")
    print("   2. CHANGE THE DEFAULT PASSWORD immediately")
    print("   3. Create technician accounts via User Management")
    print("   4. Add your clients and start managing interventions")
    print("\n⚠️  Close this window to stop the application")
    print("=" * 60 + "\n")

    # Initialize database
    with app.app_context():
        init_db()

    # Open browser in a separate thread
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    # Run the app
    app.run(host='127.0.0.1', port=port, debug=False)

