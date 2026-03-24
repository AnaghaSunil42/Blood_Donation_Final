-- Database Schema Initializer

-- Donors Table
CREATE TABLE IF NOT EXISTS donors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    age INT NOT NULL,
    gender VARCHAR(10) NOT NULL,
    blood_group VARCHAR(5) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    last_donation_date DATE,
    health_status TEXT,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    height DECIMAL(5,2),
    weight DECIMAL(5,2),
    latitude DECIMAL(10,8),
    longitude DECIMAL(10,8),
    availability_status VARCHAR(20) DEFAULT 'Available',
    reliability_score DECIMAL(5,2) DEFAULT 100.00,
    total_donations INT DEFAULT 0,
    lives_impacted INT DEFAULT 0,
    cooldown_until DATETIME,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Recipients Table
CREATE TABLE IF NOT EXISTS recipients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    hospital_name VARCHAR(150),
    blood_group_required VARCHAR(5) NOT NULL,
    units_required INT NOT NULL,
    contact_number VARCHAR(20) NOT NULL,
    location VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Blood Inventory Table
CREATE TABLE IF NOT EXISTS blood_inventory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    blood_group VARCHAR(5) UNIQUE NOT NULL,
    units_available INT DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Initialize Blood Inventory with 0 units
INSERT INTO blood_inventory (blood_group, units_available) VALUES 
('A+', 0), ('A-', 0), ('B+', 0), ('B-', 0), 
('AB+', 0), ('AB-', 0), ('O+', 0), ('O-', 0)
ON DUPLICATE KEY UPDATE id=id;

-- Donation Requests (From Recipients)
CREATE TABLE IF NOT EXISTS donation_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    recipient_id INT NOT NULL,
    request_id_code VARCHAR(30) UNIQUE, -- Format BLD-XXXXXX
    patient_name VARCHAR(100),
    patient_age INT,
    blood_group VARCHAR(5) NOT NULL,
    units_needed INT NOT NULL,
    hospital_name VARCHAR(150),
    district VARCHAR(100),
    latitude DECIMAL(10,8),
    longitude DECIMAL(10,8),
    urgency_level VARCHAR(20) DEFAULT 'High',
    request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expiry_date DATETIME,
    status VARCHAR(30) DEFAULT 'Active', -- Active, Expired, Accepted, Fulfilled, Cancelled
    accepted_by INT NULL,
    emergency_flag BOOLEAN DEFAULT FALSE,
    donor_confirmed BOOLEAN DEFAULT FALSE,
    donor_confirmed_at DATETIME,
    receiver_confirmed BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (recipient_id) REFERENCES recipients(id) ON DELETE CASCADE,
    FOREIGN KEY (accepted_by) REFERENCES donors(id) ON DELETE SET NULL
);

-- Donor Responses / Micro-commitments
CREATE TABLE IF NOT EXISTS donor_responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    donor_id INT NOT NULL,
    request_id INT NOT NULL,
    reach_within_30_mins BOOLEAN DEFAULT FALSE,
    available_today BOOLEAN DEFAULT FALSE,
    response VARCHAR(20) DEFAULT 'Pending', -- Pending, Accepted, Declined
    response_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (donor_id) REFERENCES donors(id) ON DELETE CASCADE,
    FOREIGN KEY (request_id) REFERENCES donation_requests(id) ON DELETE CASCADE
);

-- Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    user_type VARCHAR(20) NOT NULL, -- 'donor' or 'recipient'
    title VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Admin Table
CREATE TABLE IF NOT EXISTS admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);
