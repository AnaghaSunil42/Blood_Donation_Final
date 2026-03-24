from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps

def get_db():
    from backend.app import get_db_connection
    return get_db_connection()

admin_bp = Blueprint('admin', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_type') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('auth.login_admin'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # Analytics Data
    cursor.execute("SELECT COUNT(*) as count FROM donors")
    total_donors = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM recipients")
    total_recipients = cursor.fetchone()['count']
    
    cursor.execute("SELECT SUM(units_available) as count FROM blood_inventory")
    total_blood_units = cursor.fetchone()['count'] or 0
    
    cursor.execute("SELECT COUNT(*) as count FROM donation_requests WHERE status = 'Pending' OR status = 'Active'")
    pending_requests = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM donation_requests WHERE status = 'Donor Confirmed'")
    pending_confirmations = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM donation_requests WHERE status = 'Completed' OR status = 'Fulfilled'")
    completed_donations = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM donation_requests WHERE status = 'Unverified'")
    unverified_donations = cursor.fetchone()['count']

    cursor.execute("SELECT AVG(reliability_score) as avg_score FROM donors")
    avg_reliability = cursor.fetchone()['avg_score'] or 100

    cursor.execute("SELECT COUNT(*) as count FROM donation_requests WHERE emergency_flag = True AND (status = 'Pending' OR status = 'Active')")
    emergency_requests = cursor.fetchone()['count']

    # For charts (blood inventory by group)
    cursor.execute("SELECT blood_group, units_available FROM blood_inventory")
    inventory_data = cursor.fetchall()
    
    # Latest Emergency Requests
    cursor.execute("""
        SELECT dr.*, r.hospital_name, r.name as recipient_name 
        FROM donation_requests dr
        JOIN recipients r ON dr.recipient_id = r.id
        WHERE dr.status = 'Pending'
        ORDER BY dr.emergency_flag DESC, dr.request_date DESC LIMIT 5
    """)
    recent_requests = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/dashboard.html', 
                           total_donors=total_donors,
                           total_recipients=total_recipients,
                           total_blood_units=total_blood_units,
                           pending_requests=pending_requests,
                           pending_confirmations=pending_confirmations,
                           completed_donations=completed_donations,
                           unverified_donations=unverified_donations,
                           avg_reliability=round(avg_reliability, 2),
                           emergency_requests=emergency_requests,
                           inventory_data=inventory_data,
                           recent_requests=recent_requests)

@admin_bp.route('/inventory', methods=['GET', 'POST'])
@login_required
def inventory():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        blood_group = request.form['blood_group']
        units = int(request.form['units'])
        action = request.form['action'] # 'add' or 'remove'
        
        cursor.execute("SELECT units_available FROM blood_inventory WHERE blood_group = %s", (blood_group,))
        current = cursor.fetchone()
        
        if current:
            new_val = current['units_available']
            if action == 'add':
                new_val += units
            else:
                new_val = max(0, new_val - units)
                
            cursor.execute("UPDATE blood_inventory SET units_available = %s WHERE blood_group = %s", (new_val, blood_group))
            conn.commit()
            flash(f"Inventory for {blood_group} updated successfully.", 'success')
            
    cursor.execute("SELECT * FROM blood_inventory")
    blood_stocks = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('admin/inventory.html', blood_stocks=blood_stocks)

@admin_bp.route('/requests')
@login_required
def manage_requests():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT dr.*, r.hospital_name, r.name as recipient_name 
        FROM donation_requests dr
        JOIN recipients r ON dr.recipient_id = r.id
        ORDER BY dr.emergency_flag DESC, dr.request_date DESC
    """)
    requests = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/requests.html', requests=requests)

@admin_bp.route('/request/<int:req_id>/update', methods=['POST'])
@login_required
def update_request(req_id):
    status = request.form['status']
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE donation_requests SET status = %s WHERE id = %s", (status, req_id))
    
    # If fulfilled, we could automatically deduct from inventory here theoretically
    # For simplicity, we just change status.
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash(f"Request #{req_id} marked as {status}.", 'success')
    return redirect(url_for('admin.manage_requests'))

@admin_bp.route('/send-confirmation-reminder/<int:req_id>', methods=['POST'])
@login_required
def send_confirmation_reminder(req_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # Get Recipient info
    cursor.execute("""
        SELECT dr.*, r.email as recipient_email, r.name as recipient_name, d.name as donor_name 
        FROM donation_requests dr
        JOIN recipients r ON dr.recipient_id = r.id
        LEFT JOIN donors d ON dr.accepted_by = d.id
        WHERE dr.id = %s
    """, (req_id,))
    req = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if req and req['status'] == 'Pending Confirmation':
        subject = f"URGENT: Verify Blood Donation Receipt - {req.get('request_id_code', 'Req-'+str(req_id))}"
        body = f"""Dear {req['recipient_name']},

We noticed that your emergency blood request {req.get('request_id_code', '')} is currently marked as 'Pending Confirmation'. 
The assigned donor, {req.get('donor_name') or 'the donor'}, has indicated in our system that they have successfully fulfilled this donation.

To ensure accuracy of our life-saving metrics and securely close this tracking log, please log in to your Sangu Atlas dashboard and verify this by clicking 'Confirm Blood Received'.

Is there any issue? Did the donor not donate the blood? If not, please contact the administrator immediately.
If yes, please click 'received successfully' on your dashboard!

Thank you,
Lifeline Blood Donation Management
"""
        try:
            from backend.utils.email_service import send_email
            send_email(req['recipient_email'], subject, body)
            flash(f"Verification email successfully dispatched to {req['recipient_name']}!", 'success')
        except Exception as e:
            flash(f"Email failed to send. Error: {str(e)}", 'danger')
    else:
        flash("Invalid request for reminder.", "danger")
        
    return redirect(url_for('admin.manage_requests'))
