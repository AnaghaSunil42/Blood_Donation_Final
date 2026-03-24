from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
import datetime
from backend.utils.email_service import send_confirmation_prompt_email

# Lazy import DB connection
def get_db():
    from backend.app import get_db_connection
    return get_db_connection()

donor_bp = Blueprint('donor', __name__)

# Authentication Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_type') != 'donor':
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login_donor'))
        return f(*args, **kwargs)
    return decorated_function

@donor_bp.route('/mark-donated/<int:request_id>', methods=['POST'])
@login_required
def mark_donated(request_id):
    conn = get_db()
    cursor = conn.cursor()
    
    # Update request status and confirmation timestamps
    now = datetime.datetime.now()
    cursor.execute("""
        UPDATE donation_requests 
        SET status = 'Donor Confirmed', 
            donor_confirmed = 1, 
            donor_confirmed_at = %s 
        WHERE id = %s AND accepted_by = %s AND (status = 'Accepted' OR status = 'Active')
    """, (now, request_id, session['user_id']))
    
    # Set cooldown for donor (105 days = 3.5 months)
    cooldown_until = now + datetime.timedelta(days=105)
    cursor.execute("""
        UPDATE donors 
        SET cooldown_until = %s, last_donation_date = %s 
        WHERE id = %s
    """, (cooldown_until, now.date(), session['user_id']))
    
    # Fetch recipient email and request code for email notification
    cursor.execute("""
        SELECT r.email, dr.request_id_code 
        FROM donation_requests dr
        JOIN recipients r ON dr.recipient_id = r.id
        WHERE dr.id = %s
    """, (request_id,))
    recipient_data = cursor.fetchone()
    
    conn.commit()
    
    # Send Automated Confirmation Email to Recipient
    if recipient_data:
        send_confirmation_prompt_email(recipient_data[0], recipient_data[1])
    cursor.close()
    conn.close()
    
    flash("Thank you! Mark as Donated Successfully. Awaiting receiver confirmation (valid for 30 minutes).", "info")
    return redirect(url_for('donor.dashboard'))


@donor_bp.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # Get user profile
    cursor.execute("SELECT * FROM donors WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    
    # Check eligibility (cooldown)
    is_eligible = True
    days_to_wait = 0
    next_eligible_date = user.get('cooldown_until')
    
    if next_eligible_date:
        if isinstance(next_eligible_date, str):
            next_eligible_date = datetime.datetime.strptime(next_eligible_date, '%Y-%m-%d %H:%M:%S')
        
        if next_eligible_date > datetime.datetime.now():
            is_eligible = False
            days_to_wait = (next_eligible_date - datetime.datetime.now()).days
    
    user['is_eligible'] = is_eligible
    user['next_eligible_date'] = next_eligible_date
    user['next_eligible_date_iso'] = next_eligible_date.isoformat() if next_eligible_date else None
    user['days_to_wait'] = days_to_wait
    
    # Get recent requests matching donor's blood group
    cursor.execute("""
        SELECT dr.*, r.hospital_name, r.location, r.name as recipient_name 
        FROM donation_requests dr
        JOIN recipients r ON dr.recipient_id = r.id
        WHERE dr.blood_group = %s AND dr.status = 'Active'
        ORDER BY dr.emergency_flag DESC, dr.request_date DESC LIMIT 5
    """, (user['blood_group'],))
    requests = cursor.fetchall()
    
    # Get personal donation history
    cursor.execute("""
        SELECT resp.*, req.status as request_status, req.blood_group, req.units_needed, req.request_date, r.hospital_name
        FROM donor_responses resp
        JOIN donation_requests req ON resp.request_id = req.id
        JOIN recipients r ON req.recipient_id = r.id
        WHERE resp.donor_id = %s
        ORDER BY resp.response_date DESC
    """, (session['user_id'],))
    history = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('donor/dashboard.html', user=user, requests=requests, history=history)

@donor_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        phone = request.form['phone']
        address = request.form['address']
        city = request.form['city']
        last_donation_date = request.form['last_donation_date'] or None
        health_status = request.form['health_status']
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        
        cursor.execute("""
            UPDATE donors 
            SET phone=%s, address=%s, city=%s, last_donation_date=%s, health_status=%s, latitude=%s, longitude=%s
            WHERE id=%s
        """, (phone, address, city, last_donation_date, health_status, latitude, longitude, session['user_id']))
        conn.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('donor.dashboard'))
        
    cursor.execute("SELECT * FROM donors WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return render_template('donor/profile.html', user=user)

@donor_bp.route('/search-request', methods=['GET', 'POST'])
@login_required
def search_request():
    if request.method == 'POST':
        request_id_code = request.form.get('request_id_code', '').strip().upper()
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, request_id_code, blood_group, urgency_level, hospital_name, status, accepted_by
            FROM donation_requests 
            WHERE request_id_code = %s
        """, (request_id_code,))
        req_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not req_data:
            flash("Request ID not found.", "danger")
            return redirect(url_for('donor.dashboard'))
            
        if req_data['status'] != 'Active':
            flash(f"This request is {req_data['status'].lower()}.", "warning")
            return redirect(url_for('donor.dashboard'))
            
        return render_template('donor/request_details.html', req=req_data)
        
    return redirect(url_for('donor.dashboard'))

@donor_bp.route('/commit-request/<int:request_id>', methods=['POST'])
@login_required
def commit_request(request_id):
    reach_within_30 = 1 if request.form.get('reach_within_30') == 'yes' else 0
    available_today = 1 if request.form.get('available_today') == 'yes' else 0
    
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # Check donor cooldown
    cursor.execute("SELECT cooldown_until FROM donors WHERE id = %s", (session['user_id'],))
    donor = cursor.fetchone()
    if donor and donor.get('cooldown_until'):
        now = datetime.datetime.now()
        cooldown = donor['cooldown_until']
        if isinstance(cooldown, str):
            cooldown = datetime.datetime.strptime(cooldown, '%Y-%m-%d %H:%M:%S')
            
        if cooldown > now:
            days_left = (cooldown - now).days
            flash(f"You are still on cooldown. You can donate again in {days_left} days.", "warning")
            cursor.close()
            conn.close()
            return redirect(url_for('donor.dashboard'))

    # Save micro-commitment
    cursor.execute("""
        INSERT INTO donor_responses (donor_id, request_id, reach_within_30_mins, available_today, response) 
        VALUES (%s, %s, %s, %s, 'Accepted')
    """, (session['user_id'], request_id, reach_within_30, available_today))
    
    # Update request to Accepted
    cursor.execute("""
        UPDATE donation_requests 
        SET status = 'Accepted', accepted_by = %s 
        WHERE id = %s AND status = 'Active'
    """, (session['user_id'], request_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash("You have successfully accepted the request! Here are the contact details.", "success")
    return redirect(url_for('donor.accepted_request_details', request_id=request_id))

@donor_bp.route('/accepted-details/<int:request_id>')
@login_required
def accepted_request_details(request_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT dr.*, r.contact_number, r.email as recipient_email 
        FROM donation_requests dr
        JOIN recipients r ON dr.recipient_id = r.id
        WHERE dr.id = %s AND dr.accepted_by = %s
    """, (request_id, session['user_id']))
    req_data = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not req_data:
        flash("You are not authorized to view these details.", "danger")
        return redirect(url_for('donor.dashboard'))
        
    return render_template('donor/full_request_details.html', req=req_data)
