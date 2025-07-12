import mysql.connector
from mysql.connector import Error
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from config import Config

class DatabaseManager:
    """Database manager for Steam scraper bot"""
    
    def __init__(self):
        self.connection = None
        self.cursor = None
        self.logger = logging.getLogger(__name__)
        
    def connect(self) -> bool:
        """Establish database connection"""
        try:
            self.connection = mysql.connector.connect(
                host=Config.DB_HOST,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                port=Config.DB_PORT,
                autocommit=True,
                ssl_disabled=True,
                use_pure=True
            )
            self.cursor = self.connection.cursor(dictionary=True)
            self.logger.info("Database connection established successfully")
            return True
        except Error as e:
            self.logger.error(f"Error connecting to database: {e}")
            return False
            
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        self.logger.info("Database connection closed")
        
    def create_tables(self) -> bool:
        """Create necessary tables if they don't exist"""
        try:
            # Steam profiles table
            profiles_table = """
            CREATE TABLE IF NOT EXISTS steam_profiles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                steamid64 BIGINT UNIQUE NOT NULL,
                profile_url VARCHAR(255) NOT NULL,
                steam_level INT DEFAULT 0,
                avatar_url VARCHAR(500),
                is_banned BOOLEAN DEFAULT FALSE,
                ban_date DATE NULL,
                ban_type VARCHAR(50) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_steamid64 (steamid64),
                INDEX idx_scraped_at (scraped_at)
            )
            """
            
            # Bot activities table (for oracle synchronization)
            activities_table = """
            CREATE TABLE IF NOT EXISTS bot_activities (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bot_id VARCHAR(50) NOT NULL,
                steamid64 BIGINT NOT NULL,
                activity_type ENUM('scraping', 'completed', 'failed') NOT NULL,
                status ENUM('pending', 'in_progress', 'completed', 'failed') DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_bot_id (bot_id),
                INDEX idx_steamid64 (steamid64),
                INDEX idx_status (status)
            )
            """
            
            # Friends relationships table
            friends_table = """
            CREATE TABLE IF NOT EXISTS steam_friends (
                id INT AUTO_INCREMENT PRIMARY KEY,
                steamid64 BIGINT NOT NULL,
                friend_steamid64 BIGINT NOT NULL,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_friendship (steamid64, friend_steamid64),
                INDEX idx_steamid64 (steamid64),
                INDEX idx_friend_steamid64 (friend_steamid64)
            )
            """
            
            # Queue table for managing scraping tasks
            queue_table = """
            CREATE TABLE IF NOT EXISTS scraping_queue (
                id INT AUTO_INCREMENT PRIMARY KEY,
                steamid64 BIGINT UNIQUE NOT NULL,
                priority INT DEFAULT 1,
                status ENUM('pending', 'in_progress', 'completed', 'failed') DEFAULT 'pending',
                assigned_bot_id VARCHAR(50) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_status (status),
                INDEX idx_priority (priority),
                INDEX idx_steamid64 (steamid64)
            )
            """
            
            tables = [profiles_table, activities_table, friends_table, queue_table]
            
            for table in tables:
                self.cursor.execute(table)
                
            self.logger.info("All tables created successfully")
            return True
            
        except Error as e:
            self.logger.error(f"Error creating tables: {e}")
            return False
            
    def insert_profile(self, profile_data: Dict[str, Any]) -> bool:
        """Insert or update a Steam profile"""
        try:
            query = """
            INSERT INTO steam_profiles (steamid64, profile_url, steam_level, avatar_url, is_banned, ban_date, ban_type)
            VALUES (%(steamid64)s, %(profile_url)s, %(steam_level)s, %(avatar_url)s, %(is_banned)s, %(ban_date)s, %(ban_type)s)
            ON DUPLICATE KEY UPDATE
                profile_url = VALUES(profile_url),
                steam_level = VALUES(steam_level),
                avatar_url = VALUES(avatar_url),
                is_banned = VALUES(is_banned),
                ban_date = VALUES(ban_date),
                ban_type = VALUES(ban_type),
                updated_at = CURRENT_TIMESTAMP
            """
            
            self.cursor.execute(query, profile_data)
            self.logger.debug(f"Profile inserted/updated: {profile_data['steamid64']}")
            return True
            
        except Error as e:
            self.logger.error(f"Error inserting profile: {e}")
            return False
            
    def add_friends(self, steamid64: int, friend_steamids: List[int]) -> bool:
        """Add friends relationships to database"""
        try:
            query = """
            INSERT IGNORE INTO steam_friends (steamid64, friend_steamid64)
            VALUES (%s, %s)
            """
            
            friends_data = [(steamid64, friend_id) for friend_id in friend_steamids]
            self.cursor.executemany(query, friends_data)
            self.logger.debug(f"Added {len(friend_steamids)} friends for profile {steamid64}")
            return True
            
        except Error as e:
            self.logger.error(f"Error adding friends: {e}")
            return False
            
    def get_next_profile_to_scrape(self, bot_id: str) -> Optional[int]:
        """Get next profile to scrape from queue"""
        try:
            # Get next available profile
            query = """
            SELECT steamid64 FROM scraping_queue
            WHERE status = 'pending' AND assigned_bot_id IS NULL
            ORDER BY priority DESC, created_at ASC
            LIMIT 1
            """
            
            self.cursor.execute(query)
            result = self.cursor.fetchone()
            
            if result:
                steamid64 = result['steamid64']
                
                # Assign profile to bot
                update_query = """
                UPDATE scraping_queue
                SET status = 'in_progress', assigned_bot_id = %s, updated_at = CURRENT_TIMESTAMP
                WHERE steamid64 = %s AND status = 'pending'
                """
                
                self.cursor.execute(update_query, (bot_id, steamid64))
                
                if self.cursor.rowcount > 0:
                    self.logger.debug(f"Assigned profile {steamid64} to bot {bot_id}")
                    return steamid64
                    
            return None
            
        except Error as e:
            self.logger.error(f"Error getting next profile: {e}")
            return None
            
    def add_to_queue(self, steamid64: int, priority: int = 1) -> bool:
        """Add profile to scraping queue"""
        try:
            query = """
            INSERT IGNORE INTO scraping_queue (steamid64, priority)
            VALUES (%s, %s)
            """
            
            self.cursor.execute(query, (steamid64, priority))
            return True
            
        except Error as e:
            self.logger.error(f"Error adding to queue: {e}")
            return False
            
    def mark_profile_completed(self, steamid64: int, bot_id: str) -> bool:
        """Mark profile as completed in queue"""
        try:
            query = """
            UPDATE scraping_queue
            SET status = 'completed', updated_at = CURRENT_TIMESTAMP
            WHERE steamid64 = %s AND assigned_bot_id = %s
            """
            
            self.cursor.execute(query, (steamid64, bot_id))
            return True
            
        except Error as e:
            self.logger.error(f"Error marking profile completed: {e}")
            return False
            
    def mark_profile_failed(self, steamid64: int, bot_id: str) -> bool:
        """Mark profile as failed in queue"""
        try:
            query = """
            UPDATE scraping_queue
            SET status = 'failed', updated_at = CURRENT_TIMESTAMP
            WHERE steamid64 = %s AND assigned_bot_id = %s
            """
            
            self.cursor.execute(query, (steamid64, bot_id))
            return True
            
        except Error as e:
            self.logger.error(f"Error marking profile failed: {e}")
            return False
            
    def is_profile_already_scraped(self, steamid64: int) -> bool:
        """Check if profile has already been scraped"""
        try:
            query = "SELECT 1 FROM steam_profiles WHERE steamid64 = %s"
            self.cursor.execute(query, (steamid64,))
            result = self.cursor.fetchone()
            return result is not None
            
        except Error as e:
            self.logger.error(f"Error checking if profile scraped: {e}")
            return False
            
    def get_pending_queue_count(self) -> int:
        """Get count of pending profiles in queue"""
        try:
            query = "SELECT COUNT(*) as count FROM scraping_queue WHERE status = 'pending'"
            self.cursor.execute(query)
            result = self.cursor.fetchone()
            return result['count'] if result else 0
            
        except Error as e:
            self.logger.error(f"Error getting queue count: {e}")
            return 0
            
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect() 