from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps

def get_db():
    from backend.app import get_db_connection
    return get_db_connection()

recipient_bp = Blueprint('recipient', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_type') != 'recipient':
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login_recipient'))
        return f(*args, **kwargs)
    return decorated_function

def process_unverified_requests(cursor, conn):
    """Checks for donor-confirmed requests older than 30 mins and marks them unverified."""
    time_limit = datetime.datetime.now() - datetime.timedelta(minutes=30)
    
    # Find requests that were confirmed by donor but not recipient within 30 mins
    cursor.execute("""
        SELECT dr.*, d.email as donor_email, d.name as donor_name, d.reliability_score 
        FROM donation_requests dr
        JOIN donors d ON dr.accepted_by = d.id
        WHERE dr.status = 'Donor Confirmed' AND dr.donor_confirmed_at < %s
    """, (time_limit,))
    
    unverified_reqs = cursor.fetchall()
    
    for req in unverified_reqs:
        # Mark as unverified
        cursor.execute("UPDATE donation_requests SET status = 'Unverified' WHERE id = %s", (req['id'],))
        
        # Log unverified attempt and reduce reliability score
        new_score = max(0.0, float(req['reliability_score']) - 10.0)
        cursor.execute("UPDATE donors SET reliability_score = %s WHERE id = %s", (new_score, req['accepted_by']))
        
        # Send Alert Email to Recipient
        try:
            from backend.utils.email_service import send_email
            recipient_email = session.get('user_email') # We might need to fetch this or store in session
            # For now, we fetch it since session might not have it for all users if not updated
            cursor.execute("SELECT email FROM recipients WHERE id = %s", (req['recipient_id'],))
            r_email = cursor.fetchone()['email']
            
            subject = "Immediate Confirmation Required"
            body = f"""Hello,
The donor ({req['donor_name']}) has marked the blood donation (ID: {req['request_id_code']}) as completed, but we have not yet received your confirmation.

If you have successfully received the blood, please log in immediately and click 'Received Successfully'.

If the donation did NOT occur, please report the issue or create a new request.
Thank you."""
            send_email(r_email, subject, body)
        except Exception as e:
            print(f"Error sending unverified alert: {e}")
            
    if unverified_reqs:
        conn.commit()

@recipient_bp.route('/confirm-received/<int:request_id>', methods=['POST'])
@login_required
def confirm_received(request_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # Verify request belongs to this recipient and is pending confirmation
    cursor.execute("""
        SELECT dr.*, d.reliability_score 
        FROM donation_requests dr
        JOIN donors d ON dr.accepted_by = d.id
        WHERE dr.id = %s AND dr.recipient_id = %s AND dr.status = 'Donor Confirmed'
    """, (request_id, session['user_id']))
    req = cursor.fetchone()
    
    if req:
        # Check 30 minute window
        now = datetime.datetime.now()
        # Ensure it's not a string
        confirmed_at = req['donor_confirmed_at']
        if isinstance(confirmed_at, str):
            confirmed_at = datetime.datetime.strptime(confirmed_at, '%Y-%m-%d %H:%M:%S')
            
        if (now - confirmed_at).total_seconds() > 1800:
            flash("Confirmation window (30 mins) has expired. This donation is marked as unverified.", "danger")
            cursor.execute("UPDATE donation_requests SET status = 'Unverified' WHERE id = %s", (request_id,))
            conn.commit()
        else:
            # Update request status to Completed
            cursor.execute("UPDATE donation_requests SET status = 'Completed', receiver_confirmed = 1 WHERE id = %s", (request_id,))
            
            # Sangu Atlas: Increment Donor Impact Metrics!
            units = req.get('units_needed', 1)
            lives_saved = units * 3
            
            cursor.execute("""
                UPDATE donors 
                SET total_donations = total_donations + 1, 
                    lives_impacted = lives_impacted + %s,
                    reliability_score = LEAST(100, reliability_score + 5)
                WHERE id = %s
            """, (lives_saved, req['accepted_by']))
            
            conn.commit()
            flash("Confirmed! The donation is successfully verified. Thank you!", "success")
    else:
        flash("Invalid request or already confirmed.", "danger")
        
    cursor.close()
    conn.close()
    return redirect(url_for('recipient.dashboard'))

@recipient_bp.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # Process any unverified timeouts
    process_unverified_requests(cursor, conn)
    
    # Get user profile
    cursor.execute("SELECT * FROM recipients WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    
    # Get their requests
    cursor.execute("SELECT * FROM donation_requests WHERE recipient_id = %s ORDER BY request_date DESC", (session['user_id'],))
    requests = cursor.fetchall()
    
    # Check inventory for their required blood group
    cursor.execute("SELECT units_available FROM blood_inventory WHERE blood_group = %s", (user['blood_group_required'],))
    inventory = cursor.fetchone()
    available_units = inventory['units_available'] if inventory else 0
    
    cursor.close()
    conn.close()
    
    return render_template('recipient/dashboard.html', user=user, requests=requests, available_units=available_units)

import uuid
import datetime
from backend.utils.matching_algorithm import find_best_donors
from backend.utils.email_service import send_emergency_blood_email

@recipient_bp.route('/request-blood', methods=['GET', 'POST'])
@login_required
def request_blood():
    target_donor = None
    target_donor_id = request.args.get('target_donor_id')
    
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if target_donor_id:
        cursor.execute("SELECT id, blood_group, city FROM donors WHERE id = %s", (target_donor_id,))
        target_donor = cursor.fetchone()

    if request.method == 'POST':
        blood_group = request.form['blood_group']
        units_needed = request.form['units_needed']
        patient_name = request.form.get('patient_name', 'Unknown')
        patient_age = request.form.get('patient_age', 0)
        hospital_name = request.form.get('hospital_name', 'Unknown')
        district = request.form.get('district', 'Unknown')
        latitude = request.form.get('latitude', 0.0)
        longitude = request.form.get('longitude', 0.0)
        urgency_level = request.form.get('urgency_level', 'High')
        emergency_flag = True if request.form.get('emergency_flag') else False
        
        request_id_code = f"BLD-{str(uuid.uuid4().hex)[:6].upper()}"
        expiry_date = datetime.datetime.now() + datetime.timedelta(hours=48)
        
        cursor.execute("""
            INSERT INTO donation_requests (
                recipient_id, request_id_code, patient_name, patient_age, 
                blood_group, units_needed, hospital_name, district, latitude, longitude, 
                urgency_level, expiry_date, status, emergency_flag
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Active', %s)
        """, (
            session['user_id'], request_id_code, patient_name, patient_age,
            blood_group, units_needed, hospital_name, district, latitude, longitude,
            urgency_level, expiry_date, emergency_flag
        ))
        
        conn.commit()
        
        # SANGU ATLAS: Intelligent Matching and Notifications
        form_target_donor_id = request.form.get('target_donor_id')
        
        # Determine notification limit and targets
        notification_limit = 0
        target_donors = []
        
        if form_target_donor_id:
            # Targeted Request: Notify only this donor
            cursor.execute("SELECT id, name, email, latitude, longitude, reliability_score FROM donors WHERE id = %s", (form_target_donor_id,))
            donor_obj = cursor.fetchone()
            if donor_obj:
                target_donors = [donor_obj]
                notification_limit = 1
        elif urgency_level == 'Critical':
            notification_limit = None  # Notify all matching donors
        elif emergency_flag:
            notification_limit = 5     # Notify top 5 matching donors
            
        if notification_limit is not 0:
            if not target_donors: # Only if not already targeted
                target_donors = find_best_donors(cursor, blood_group, latitude, longitude, limit=notification_limit, requested_district=district)
            
            for d in target_donors:
                donor_email = d.get('email')
                if donor_email:
                    location_str = f"{hospital_name} (Lat: {latitude}, Lon: {longitude})"
                    send_emergency_blood_email(
                        donor_email, blood_group, patient_name, patient_age, 
                        location_str, request_id_code
                    )
        
        cursor.close()
        conn.close()
        
        flash(f'Blood request submitted successfully. Request ID: {request_id_code}', 'success')
        return redirect(url_for('recipient.dashboard'))
        
    return render_template('recipient/request_blood.html', 
                          blood_groups=['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'],
                          target_donor=target_donor)

@recipient_bp.route('/map')
@login_required
def find_donors_map():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # Fetch all donors with their city/address for the map
    # In a real app we'd geocode these, but we'll use the Maps API client-side 
    # to display markers based on addresses.
    blood_group = request.args.get('blood_group', '')
    
    if blood_group:
        cursor.execute("SELECT id, name, blood_group, city, latitude, longitude FROM donors WHERE blood_group = %s AND availability_status = 'Available'", (blood_group,))
    else:
        cursor.execute("SELECT id, name, blood_group, city, latitude, longitude FROM donors WHERE availability_status = 'Available'")
        
    donors = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('recipient/map.html', donors=donors, selected_bg=blood_group)

@recipient_bp.route('/delete-request/<int:request_id>', methods=['POST'])
@login_required
def delete_request(request_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # Verify the request belongs to the user and is 'Active' or 'Unverified' or 'Expired'
    # Generally, deleting 'Accepted' or 'Completed' might be restricted, but I'll allow it for now per user request.
    cursor.execute("SELECT id FROM donation_requests WHERE id = %s AND recipient_id = %s", (request_id, session['user_id']))
    req = cursor.fetchone()
    
    if req:
        cursor.execute("DELETE FROM donation_requests WHERE id = %s", (request_id,))
        conn.commit()
        flash("Blood request deleted successfully.", "success")
    else:
        flash("Request not found or unauthorized.", "danger")
        
    cursor.close()
    conn.close()
    return redirect(url_for('recipient.dashboard'))
