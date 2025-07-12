#!/usr/bin/env python3
"""
Database setup utility for Steam Profile Scraper Bot
This script creates the database and tables required for the scraper to function.
"""

import mysql.connector
from mysql.connector import Error
import logging
import sys
from config import Config

def create_database():
    """Create the database if it doesn't exist"""
    try:
        # Connect to MySQL without specifying database
        connection = mysql.connector.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            port=Config.DB_PORT,
            ssl_disabled=True,
            use_pure=True
        )
        
        cursor = connection.cursor()
        
        # Create database
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.DB_NAME}")
        print(f"✓ Database '{Config.DB_NAME}' created successfully")
        
        # Use the database
        cursor.execute(f"USE {Config.DB_NAME}")
        
        cursor.close()
        connection.close()
        
        return True
        
    except Error as e:
        print(f"✗ Error creating database: {e}")
        return False

def create_tables():
    """Create all required tables"""
    try:
        from database import DatabaseManager
        
        with DatabaseManager() as db:
            if db.create_tables():
                print("✓ All tables created successfully")
                return True
            else:
                print("✗ Failed to create tables")
                return False
                
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        return False

def test_connection():
    """Test database connection"""
    try:
        from database import DatabaseManager
        
        with DatabaseManager() as db:
            # Test basic query
            db.cursor.execute("SELECT 1")
            result = db.cursor.fetchone()
            
            if result:
                print("✓ Database connection test successful")
                return True
            else:
                print("✗ Database connection test failed")
                return False
                
    except Exception as e:
        print(f"✗ Database connection test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("=== Steam Profile Scraper Database Setup ===\n")
    
    # Validate configuration
    try:
        Config.validate_config()
        print("✓ Configuration validated")
    except ValueError as e:
        print(f"✗ Configuration error: {e}")
        print("\nPlease check your .env file and make sure all required variables are set.")
        sys.exit(1)
    
    # Create database
    print("\n1. Creating database...")
    if not create_database():
        sys.exit(1)
    
    # Create tables
    print("\n2. Creating tables...")
    if not create_tables():
        sys.exit(1)
    
    # Test connection
    print("\n3. Testing connection...")
    if not test_connection():
        sys.exit(1)
    
    print("\n=== Setup Complete ===")
    print("Your database is ready for scraping!")
    print(f"Database: {Config.DB_NAME}")
    print(f"Host: {Config.DB_HOST}:{Config.DB_PORT}")
    print("\nYou can now run the scraper with:")
    print("python main.py --seed YOUR_PROFILE_ID --bots 1 --interactive")

if __name__ == "__main__":
    main() 