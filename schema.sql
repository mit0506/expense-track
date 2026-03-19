-- Manual MySQL Database Schema
-- Last Updated: 2026-03-19

-- 1. Create UserProfile table
CREATE TABLE IF NOT EXISTS user_profile (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    name VARCHAR(100),
    monthly_income FLOAT DEFAULT 50000.0,
    monthly_target FLOAT DEFAULT 0.0,
    avatar VARCHAR(200)
);

-- 2. Create CategoryBudget table
CREATE TABLE IF NOT EXISTS category_budget (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    category VARCHAR(50) NOT NULL,
    amount FLOAT DEFAULT 0.0,
    CONSTRAINT _user_category_uc UNIQUE (user_id, category),
    FOREIGN KEY (user_id) REFERENCES user_profile(id) ON DELETE CASCADE
);

-- 3. Create Subscription table
CREATE TABLE IF NOT EXISTS subscription (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    merchant VARCHAR(100) NOT NULL,
    amount FLOAT NOT NULL,
    category VARCHAR(50),
    billing_cycle VARCHAR(20) DEFAULT 'monthly',
    next_billing_date VARCHAR(20) NOT NULL,
    auto_log BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES user_profile(id) ON DELETE CASCADE
);

-- 4. Create Expense table
CREATE TABLE IF NOT EXISTS expense (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    date VARCHAR(20) NOT NULL,
    merchant VARCHAR(100) NOT NULL,
    amount FLOAT NOT NULL,
    category VARCHAR(50),
    payment_type VARCHAR(50),
    FOREIGN KEY (user_id) REFERENCES user_profile(id) ON DELETE CASCADE
);
