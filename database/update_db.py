import os
import sys
from os.path import dirname, abspath

# Add the parent directory to Python path
sys.path.insert(0, dirname(dirname(abspath(__file__))))

from backend.app import get_db_connection

def update_database():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database.")
        sys.exit(1)
        
    cursor = conn.cursor()
    
    # Run alters. We use try/except block just in case column already exists
    alters = [
        "ALTER TABLE donors ADD COLUMN height DECIMAL(5,2);",
        "ALTER TABLE donors ADD COLUMN weight DECIMAL(5,2);",
        "ALTER TABLE donors ADD COLUMN latitude DECIMAL(10,8);",
        "ALTER TABLE donors ADD COLUMN longitude DECIMAL(10,8);",
        "ALTER TABLE donors ADD COLUMN availability_status VARCHAR(20) DEFAULT 'Available';",
        "ALTER TABLE donors ADD COLUMN reliability_score DECIMAL(5,2) DEFAULT 100.00;",
        "ALTER TABLE donors ADD COLUMN total_donations INT DEFAULT 0;",
        "ALTER TABLE donors ADD COLUMN lives_impacted INT DEFAULT 0;",
        "ALTER TABLE donors ADD COLUMN last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;",
        
        "ALTER TABLE donors ADD COLUMN cooldown_until DATETIME;",
        
        "ALTER TABLE donation_requests ADD COLUMN request_id_code VARCHAR(30) UNIQUE;",
        "ALTER TABLE donation_requests ADD COLUMN patient_name VARCHAR(100);",
        "ALTER TABLE donation_requests ADD COLUMN patient_age INT;",
        "ALTER TABLE donation_requests ADD COLUMN hospital_name VARCHAR(150);",
        "ALTER TABLE donation_requests ADD COLUMN latitude DECIMAL(10,8);",
        "ALTER TABLE donation_requests ADD COLUMN longitude DECIMAL(10,8);",
        "ALTER TABLE donation_requests ADD COLUMN urgency_level VARCHAR(20) DEFAULT 'High';",
        "ALTER TABLE donation_requests ADD COLUMN expiry_date DATETIME;",
        "ALTER TABLE donation_requests MODIFY COLUMN status VARCHAR(30) DEFAULT 'Active';",
        "ALTER TABLE donation_requests ADD COLUMN accepted_by INT NULL;",
        "ALTER TABLE donation_requests ADD FOREIGN KEY (accepted_by) REFERENCES donors(id) ON DELETE SET NULL;",
        "ALTER TABLE donation_requests ADD COLUMN donor_confirmed BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE donation_requests ADD COLUMN donor_confirmed_at DATETIME;",
        "ALTER TABLE donation_requests ADD COLUMN receiver_confirmed BOOLEAN DEFAULT FALSE;",
        
        "ALTER TABLE donor_responses ADD COLUMN reach_within_30_mins BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE donor_responses ADD COLUMN available_today BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE donor_responses MODIFY COLUMN response VARCHAR(20) DEFAULT 'Pending';"
    ]
    
    for query in alters:
        try:
            cursor.execute(query)
            print(f"Executed: {query}")
        except Exception as e:
            print(f"Skipped (likely exists): {query} - Error: {e}")
            
    # Create new tables
    create_notifications = """
    CREATE TABLE IF NOT EXISTS notifications (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        user_type VARCHAR(20) NOT NULL,
        title VARCHAR(100) NOT NULL,
        message TEXT NOT NULL,
        is_read BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    try:
        cursor.execute(create_notifications)
        print("Ensured notifications table exists.")
    except Exception as e:
        print(f"Error creating notifications: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    print("Database update complete!")

if __name__ == '__main__':
    update_database()
