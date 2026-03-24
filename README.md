# Blood Donation Management System

An AI-enabled Blood Donation Management System aligned with SDG Goal 3 – Good Health and Well-Being. 
This platform improves blood donation coordination by connecting donors, recipients, hospitals, and blood banks.

## Prerequisites
- Python 3.8+
- MySQL Server (e.g., via XAMPP)

## Step-by-Step Local Setup

1. **Start your MySQL Server**
   - Open XAMPP Control Panel and start the `MySQL` module.

2. **Setup Database**
   - Go to phpMyAdmin (usually `http://localhost/phpmyadmin/`).
   - You can either create a database named `blood_bank_db` and import the `database/schema.sql` file, OR you can run the SQL script directly which will create the database and tables for you.

3. **Install Python Dependencies**
   - Open a terminal in the `blood-donation-system` folder.
   - It is recommended to create a virtual environment:
     ```bash
     python -m venv venv
     # Windows:
     venv\Scripts\activate
     # Mac/Linux:
     source venv/bin/activate
     ```
   - Install dependencies:
     ```bash
     pip install -r requirements.txt
     ```

4. **Configuration**
   - Open the `.env` file in the root directory.
   - Verify that your MySQL credentials match your XAMPP setup (`DB_HOST`, `DB_USER`, `DB_PASSWORD`). By default in XAMPP, `DB_USER` is `root` and `DB_PASSWORD` is empty.
   - Replace the `GOOGLE_MAPS_API_KEY` and `GEMINI_API_KEY` with your actual keys when ready.

5. **Run the Application**
   - Start the Flask server:
     ```bash
     python app.py
     ```
   - Visit `http://127.0.0.1:5000` in your browser.

## Default Admin Credentials
When you run the app for the first time, it will generate a default admin account.
- **Username**: admin
- **Password**: admin123
