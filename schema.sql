-- 1. Create and select the database
CREATE DATABASE IF NOT EXISTS expense_track;
USE expense_track;

-- 2. Create the `expense` table
CREATE TABLE expense (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date VARCHAR(10),
    merchant VARCHAR(100),
    amount FLOAT,
    category VARCHAR(50),
    payment_type VARCHAR(50)
);

-- 3. Create the `user_profile` table
CREATE TABLE user_profile (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) DEFAULT 'User',
    monthly_income FLOAT DEFAULT 0.0,
    monthly_target FLOAT DEFAULT 0.0,
    avatar VARCHAR(200) NULL
);
