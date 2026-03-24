from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector

# Lazy import to avoid circular dependency
def get_db():
    from backend.app import get_db_connection
    return get_db_connection()

auth_bp = Blueprint('auth', __name__)

# --- DONOR AUTH ---

@auth_bp.route('/register/donor', methods=['GET', 'POST'])
def register_donor():
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        blood_group = request.form['blood_group']
        phone = request.form['phone']
        email = request.form['email']
        address = request.form['address']
        city = request.form['city']
        password = request.form['password']
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        
        hashed_password = generate_password_hash(password)
        conn = get_db()
        if not conn:
            flash('Database connection failed. Please ensure your local MySQL server (e.g. XAMPP) is running.', 'danger')
            return render_template('auth/register_donor.html')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO donors (name, age, gender, blood_group, phone, email, address, city, password, latitude, longitude)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (name, age, gender, blood_group, phone, email, address, city, hashed_password, latitude or None, longitude or None))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login_donor'))
        except mysql.connector.Error as err:
            if err.errno == 1062: # Duplicate entry
                flash('Email already registered!', 'danger')
            else:
                flash(f'An error occurred: {err}', 'danger')
        finally:
            cursor.close()
            conn.close()
            
    return render_template('auth/register_donor.html')

@auth_bp.route('/login/donor', methods=['GET', 'POST'])
def login_donor():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db()
        if not conn:
            flash('Database connection failed. Please ensure your local MySQL server (e.g. XAMPP) is running.', 'danger')
            return render_template('auth/login_donor.html')
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM donors WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_type'] = 'donor'
            flash('Logged in successfully.', 'success')
            return redirect(url_for('donor.dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
            
    return render_template('auth/login_donor.html')


# --- RECIPIENT AUTH ---

@auth_bp.route('/register/recipient', methods=['GET', 'POST'])
def register_recipient():
    if request.method == 'POST':
        name = request.form['name']
        hospital_name = request.form['hospital_name']
        blood_group_required = request.form['blood_group_required']
        units_required = request.form['units_required']
        contact_number = request.form['contact_number']
        location = request.form['location']
        email = request.form['email']
        password = request.form['password']
        
        hashed_password = generate_password_hash(password)
        conn = get_db()
        if not conn:
            flash('Database connection failed. Please ensure your local MySQL server (e.g. XAMPP) is running.', 'danger')
            return render_template('auth/register_recipient.html')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO recipients (name, hospital_name, blood_group_required, units_required, contact_number, location, email, password)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (name, hospital_name, blood_group_required, units_required, contact_number, location, email, hashed_password))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login_recipient'))
        except mysql.connector.Error as err:
            if err.errno == 1062:
                flash('Email already registered!', 'danger')
            else:
                flash(f'An error occurred: {err}', 'danger')
        finally:
            cursor.close()
            conn.close()
            
    return render_template('auth/register_recipient.html')

@auth_bp.route('/login/recipient', methods=['GET', 'POST'])
def login_recipient():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db()
        if not conn:
            flash('Database connection failed. Please ensure your local MySQL server (e.g. XAMPP) is running.', 'danger')
            return render_template('auth/login_recipient.html')
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM recipients WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_type'] = 'recipient'
            flash('Logged in successfully.', 'success')
            return redirect(url_for('recipient.dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
            
    return render_template('auth/login_recipient.html')


# --- ADMIN AUTH ---

@auth_bp.route('/login/admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        if not conn:
            flash('Database connection failed. Please ensure your local MySQL server (e.g. XAMPP) is running.', 'danger')
            return render_template('auth/login_admin.html')
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admin WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = 'Admin'
            session['user_type'] = 'admin'
            flash('Logged in successfully.', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('auth/login_admin.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))
