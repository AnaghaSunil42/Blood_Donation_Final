import os
import sys
from os.path import dirname, abspath

# Add the parent directory to Python path to allow imports from backend
sys.path.insert(0, dirname(dirname(abspath(__file__))))

from flask import Flask, render_template, session, redirect, url_for, g
from dotenv import load_dotenv
import mysql.connector

# Load environment variables
load_dotenv(dotenv_path=os.path.join(dirname(dirname(abspath(__file__))), '.env'))

app = Flask(
    __name__,
    template_folder='../templates',
    static_folder='../static'
)

app.secret_key = os.getenv('SECRET_KEY', 'default-secret-key-for-dev')

# Global Constants
app.config['GOOGLE_MAPS_API_KEY'] = os.getenv('GOOGLE_MAPS_API_KEY')
app.config['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY')

# Database connection
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'blood_bank_db')
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

# Close DB connection properly after each request
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Provide current user type and info to all templates
@app.context_processor
def inject_user():
    return dict(
        user_type=session.get('user_type'),
        user_id=session.get('user_id'),
        user_name=session.get('user_name')
    )

from backend.routes.auth_routes import auth_bp
from backend.routes.donor_routes import donor_bp
from backend.routes.recipient_routes import recipient_bp
from backend.routes.admin_routes import admin_bp
from backend.routes.main_routes import main_bp
from backend.routes.chatbot_routes import chatbot_bp

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(donor_bp, url_prefix='/donor')
app.register_blueprint(recipient_bp, url_prefix='/recipient')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(chatbot_bp, url_prefix='/chatbot')
app.register_blueprint(main_bp, url_prefix='/')

# Setup default admin account if not exists
def setup_admin():
    conn = get_db_connection()
    if not conn:
        return
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin WHERE username = 'admin'")
    if not cursor.fetchone():
        from werkzeug.security import generate_password_hash
        hashed_pw = generate_password_hash('admin123')
        cursor.execute("INSERT INTO admin (username, password) VALUES ('admin', %s)", (hashed_pw,))
        conn.commit()
    cursor.close()
    conn.close()

# Quick utility inject for constants
@app.context_processor
def utility_processor():
    blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    return dict(blood_groups=blood_groups, map_api_key=app.config['GOOGLE_MAPS_API_KEY'])

if __name__ == '__main__':
    setup_admin()
    app.run(debug=True, port=5000)
