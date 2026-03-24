import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

# Load env variables safely based on execution context
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(os.path.dirname(current_dir), '..', '.env')
load_dotenv(dotenv_path=os.path.abspath(env_path))

def send_emergency_blood_email(donor_email, blood_group, patient_name, age, location, request_id):
    sender_email = os.getenv("EMAIL_ID")
    sender_password = os.getenv("EMAIL_APP_PASSWORD")

    if not sender_email or not sender_password:
        print("Email credentials not configured in environment.", sender_email)
        return False

    subject = "URGENT: Blood Required"
    body = f"""Blood Group: {blood_group}
Patient: {patient_name}, Age {age}
Location: {location}

Request ID: {request_id}

Can you reach within 30 minutes?
Login and use this ID to respond."""

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = donor_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print(f"Emergency email sent successfully to {donor_email}")
        return True
    except Exception as e:
        print(f"Failed to send email to {donor_email}: {e}")
        return False

def send_confirmation_prompt_email(recipient_email, request_id_code):
    sender_email = os.getenv("EMAIL_ID")
    sender_password = os.getenv("EMAIL_APP_PASSWORD")

    if not sender_email or not sender_password:
        return False

    subject = "Confirmation Required: Blood Donation Progress"
    body = f"""Hello,

The donor has marked the blood donation (Request ID: {request_id_code}) as successfully completed.

To finalize this process, could you please log in to your dashboard and confirm receipt? 
- If you have successfully received the blood, click 'Received Successfully'.
- If the donation did NOT occur, you may re-request blood from the dashboard.

Thank you for being part of the Lifeline community."""

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send confirmation prompt to {recipient_email}: {e}")
        return False
