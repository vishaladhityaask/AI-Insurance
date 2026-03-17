-- AI Insurance Phase 1 Database Setup
CREATE DATABASE IF NOT EXISTS ai_insurance;
USE ai_insurance;

CREATE TABLE IF NOT EXISTS workers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    phone VARCHAR(20),
    occupation VARCHAR(100) NOT NULL,
    age INT NOT NULL,
    region VARCHAR(100) NOT NULL,
    risk_level ENUM('low','medium','high') DEFAULT 'medium',
    base_premium DECIMAL(10,2) DEFAULT 0.00,
    final_premium DECIMAL(10,2) DEFAULT 0.00,
    weather_factor DECIMAL(4,2) DEFAULT 1.00,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('active','pending','suspended') DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS weather_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    region VARCHAR(100) NOT NULL,
    temperature DECIMAL(5,2),
    humidity DECIMAL(5,2),
    wind_speed DECIMAL(5,2),
    `condition` VARCHAR(50),
    risk_multiplier DECIMAL(4,2) DEFAULT 1.00,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS claims (
    id INT AUTO_INCREMENT PRIMARY KEY,
    worker_id INT NOT NULL,
    claim_type VARCHAR(100),
    amount DECIMAL(10,2),
    description TEXT,
    status ENUM('pending','approved','rejected') DEFAULT 'pending',
    filed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (worker_id) REFERENCES workers(id)
);

-- Seed weather data for regions
INSERT INTO weather_data (region, temperature, humidity, wind_speed, `condition`, risk_multiplier) VALUES
('North Zone', 32.5, 65.0, 18.0, 'Sunny', 1.0),
('South Zone', 28.0, 80.0, 12.0, 'Humid', 1.15),
('East Zone', 25.0, 70.0, 22.0, 'Windy', 1.2),
('West Zone', 38.0, 30.0, 8.0, 'Hot & Dry', 1.25),
('Central Zone', 30.0, 55.0, 15.0, 'Moderate', 1.05);

-- Seed demo workers (Swiggy / Zepto / Amazon)
INSERT INTO workers (full_name, email, phone, occupation, age, region, risk_level, base_premium, final_premium, weather_factor, status) VALUES
('Ravi Kumar',      'ravi@example.com',   '9876543210', 'Swiggy Delivery Partner',    26, 'South Zone',   'high',   3200.00, 4960.00, 1.15, 'active'),
('Priya Nair',      'priya@example.com',  '9876543211', 'Zepto Dark Store Picker',    24, 'North Zone',   'medium', 2500.00, 3000.00, 1.20, 'active'),
('Mohammed Salim',  'salim@example.com',  '9876543212', 'Amazon Delivery Associate',  31, 'East Zone',    'high',   3400.00, 4080.00, 1.20, 'pending'),
('Anita Sharma',    'anita@example.com',  '9876543213', 'Swiggy Instamart Picker',    28, 'West Zone',    'medium', 2600.00, 3575.00, 1.25, 'active'),
('David Raj',       'david@example.com',  '9876543214', 'Amazon Warehouse Associate', 35, 'Central Zone', 'medium', 2800.00, 2940.00, 1.05, 'active'),
('Lakshmi Devi',    'lakshmi@example.com','9876543215', 'Zepto Delivery Partner',     22, 'South Zone',   'high',   3000.00, 4140.00, 1.15, 'active'),
('Arjun Mehta',     'arjun@example.com',  '9876543216', 'Amazon Flex Delivery',       29, 'North Zone',   'high',   3100.00, 3596.00, 1.00, 'pending'),
('Sunita Rao',      'sunita@example.com', '9876543217', 'Swiggy Fleet Supervisor',    38, 'Central Zone', 'low',    2200.00, 2310.00, 1.05, 'active');
