import threading
import time
import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from database import DatabaseManager
from config import Config

class Oracle:
    """Oracle system for coordinating multiple bots"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.logger = logging.getLogger(__name__)
        self.lock = threading.Lock()
        self.running = False
        self.cleanup_thread = None
        
    def start(self):
        """Start the Oracle system"""
        try:
            if not self.db_manager.connect():
                self.logger.error("Failed to connect to database")
                return False
            
            if not self.db_manager.create_tables():
                self.logger.error("Failed to create database tables")
                return False
            
            self.running = True
            
            # Start cleanup thread
            self.cleanup_thread = threading.Thread(target=self._cleanup_stale_tasks, daemon=True)
            self.cleanup_thread.start()
            
            self.logger.info("Oracle system started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting Oracle: {e}")
            return False
            
    def stop(self):
        """Stop the Oracle system"""
        self.running = False
        if self.cleanup_thread:
            self.cleanup_thread.join()
        
        self.db_manager.disconnect()
        self.logger.info("Oracle system stopped")
        
    def request_task(self, bot_id: str) -> Optional[int]:
        """Request a new task (SteamID64) for a bot"""
        try:
            with self.lock:
                # Ensure database connection is active
                if not self.db_manager.connection or not self.db_manager.connection.is_connected():
                    self.logger.warning("Database connection lost, reconnecting...")
                    if not self.db_manager.connect():
                        self.logger.error("Failed to reconnect to database")
                        return None
                
                steamid64 = self.db_manager.get_next_profile_to_scrape(bot_id)
                
                if steamid64:
                    self.logger.info(f"Assigned task {steamid64} to bot {bot_id}")
                    return steamid64
                
                self.logger.debug(f"No tasks available for bot {bot_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error requesting task for bot {bot_id}: {e}")
            return None
            
    def submit_result(self, bot_id: str, steamid64: int, result_data: Dict[str, Any]) -> bool:
        """Submit scraping result from a bot"""
        try:
            with self.lock:
                # Ensure database connection is active
                if not self.db_manager.connection or not self.db_manager.connection.is_connected():
                    self.logger.warning("Database connection lost, reconnecting...")
                    if not self.db_manager.connect():
                        self.logger.error("Failed to reconnect to database")
                        return False
                
                # Validate that this bot was assigned this task
                if not self._validate_task_assignment(bot_id, steamid64):
                    self.logger.warning(f"Bot {bot_id} tried to submit result for unassigned task {steamid64}")
                    return False
                
                # Check if profile already exists (race condition protection)
                if self.db_manager.is_profile_already_scraped(steamid64):
                    self.logger.info(f"Profile {steamid64} already scraped by another bot, skipping")
                    self.db_manager.mark_profile_completed(steamid64, bot_id)
                    return True
                
                # Insert profile data
                profile_data = {
                    'steamid64': result_data['steamid64'],
                    'profile_url': result_data['profile_url'],
                    'steam_level': result_data['steam_level'],
                    'avatar_url': result_data['avatar_url'],
                    'is_banned': result_data['is_banned'],
                    'ban_date': result_data['ban_date'],
                    'ban_type': result_data['ban_type']
                }
                
                if self.db_manager.insert_profile(profile_data):
                    # Add friends to queue
                    friends = result_data.get('friends', [])
                    if friends:
                        self.db_manager.add_friends(steamid64, friends)
                        self._add_friends_to_queue(friends)
                    
                    # Mark task as completed
                    self.db_manager.mark_profile_completed(steamid64, bot_id)
                    
                    self.logger.info(f"Successfully processed result from bot {bot_id} for profile {steamid64}")
                    return True
                else:
                    self.logger.error(f"Failed to insert profile data for {steamid64}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error submitting result from bot {bot_id}: {e}")
            return False
            
    def report_failure(self, bot_id: str, steamid64: int, error_message: str) -> bool:
        """Report a failed scraping attempt"""
        try:
            with self.lock:
                # Validate that this bot was assigned this task
                if not self._validate_task_assignment(bot_id, steamid64):
                    self.logger.warning(f"Bot {bot_id} tried to report failure for unassigned task {steamid64}")
                    return False
                
                # Mark task as failed
                self.db_manager.mark_profile_failed(steamid64, bot_id)
                
                self.logger.warning(f"Bot {bot_id} reported failure for profile {steamid64}: {error_message}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error reporting failure from bot {bot_id}: {e}")
            return False
            
    def add_seed_profile(self, steamid64: int, priority: int = 1) -> bool:
        """Add a seed profile to start scraping"""
        try:
            with self.lock:
                success = self.db_manager.add_to_queue(steamid64, priority)
                
                if success:
                    self.logger.info(f"Added seed profile {steamid64} to queue with priority {priority}")
                else:
                    self.logger.debug(f"Seed profile {steamid64} already in queue")
                
                return success
                
        except Exception as e:
            self.logger.error(f"Error adding seed profile {steamid64}: {e}")
            return False
            
    def get_queue_status(self) -> Dict[str, int]:
        """Get current queue status"""
        try:
            # Ensure database connection is active
            if not self.db_manager.connection or not self.db_manager.connection.is_connected():
                self.logger.warning("Database connection lost, reconnecting...")
                if not self.db_manager.connect():
                    self.logger.error("Failed to reconnect to database")
                    return {'pending_tasks': 0, 'scraped_profiles': 0, 'active_bots': 0}
            
            # Get queue statistics
            pending_count = self.db_manager.get_pending_queue_count()
            
            # Get total profiles scraped
            query = "SELECT COUNT(*) as count FROM steam_profiles"
            self.db_manager.cursor.execute(query)
            result = self.db_manager.cursor.fetchone()
            scraped_count = result['count'] if result else 0
            
            # Get active bots
            query = """
            SELECT COUNT(DISTINCT assigned_bot_id) as count 
            FROM scraping_queue 
            WHERE status = 'in_progress' AND assigned_bot_id IS NOT NULL
            """
            self.db_manager.cursor.execute(query)
            result = self.db_manager.cursor.fetchone()
            active_bots = result['count'] if result else 0
            
            return {
                'pending_tasks': pending_count,
                'scraped_profiles': scraped_count,
                'active_bots': active_bots
            }
            
        except Exception as e:
            self.logger.error(f"Error getting queue status: {e}")
            return {'pending_tasks': 0, 'scraped_profiles': 0, 'active_bots': 0}
            
    def _validate_task_assignment(self, bot_id: str, steamid64: int) -> bool:
        """Validate that a bot was assigned a specific task"""
        try:
            query = """
            SELECT 1 FROM scraping_queue 
            WHERE steamid64 = %s AND assigned_bot_id = %s AND status = 'in_progress'
            """
            
            self.db_manager.cursor.execute(query, (steamid64, bot_id))
            result = self.db_manager.cursor.fetchone()
            
            return result is not None
            
        except Exception as e:
            self.logger.error(f"Error validating task assignment: {e}")
            return False
            
    def _add_friends_to_queue(self, friend_steamids: List[int]) -> None:
        """Add friends to scraping queue if not already present"""
        try:
            for steamid64 in friend_steamids:
                # Check if already scraped or in queue
                if not self.db_manager.is_profile_already_scraped(steamid64):
                    self.db_manager.add_to_queue(steamid64, priority=1)
                    
        except Exception as e:
            self.logger.error(f"Error adding friends to queue: {e}")
            
    def _cleanup_stale_tasks(self):
        """Clean up stale/orphaned tasks"""
        while self.running:
            try:
                time.sleep(Config.ORACLE_CHECK_INTERVAL)
                
                # Find tasks that have been in_progress for too long
                timeout_minutes = Config.ORACLE_TIMEOUT
                cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
                
                query = """
                UPDATE scraping_queue 
                SET status = 'pending', assigned_bot_id = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE status = 'in_progress' AND updated_at < %s
                """
                
                self.db_manager.cursor.execute(query, (cutoff_time,))
                
                if self.db_manager.cursor.rowcount > 0:
                    self.logger.info(f"Cleaned up {self.db_manager.cursor.rowcount} stale tasks")
                    
            except Exception as e:
                self.logger.error(f"Error in cleanup thread: {e}")
                
    def get_bot_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics about bot performance"""
        try:
            # Get per-bot statistics
            query = """
            SELECT 
                assigned_bot_id,
                COUNT(*) as total_tasks,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_tasks,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress_tasks
            FROM scraping_queue 
            WHERE assigned_bot_id IS NOT NULL
            GROUP BY assigned_bot_id
            """
            
            self.db_manager.cursor.execute(query)
            bot_stats = self.db_manager.cursor.fetchall()
            
            # Get overall statistics
            query = """
            SELECT 
                COUNT(*) as total_profiles,
                SUM(CASE WHEN is_banned = 1 THEN 1 ELSE 0 END) as banned_profiles,
                AVG(steam_level) as avg_level
            FROM steam_profiles
            """
            
            self.db_manager.cursor.execute(query)
            overall_stats = self.db_manager.cursor.fetchone()
            
            return {
                'bot_statistics': bot_stats,
                'overall_statistics': overall_stats
            }
            
        except Exception as e:
            self.logger.error(f"Error getting bot statistics: {e}")
            return {'bot_statistics': [], 'overall_statistics': {}}
            
    def register_bot(self, bot_id: str) -> bool:
        """Register a bot with the Oracle"""
        try:
            # Record bot registration
            query = """
            INSERT INTO bot_activities (bot_id, steamid64, activity_type, status)
            VALUES (%s, 0, 'scraping', 'pending')
            ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP
            """
            
            self.db_manager.cursor.execute(query, (bot_id,))
            self.logger.info(f"Registered bot {bot_id} with Oracle")
            return True
            
        except Exception as e:
            self.logger.error(f"Error registering bot {bot_id}: {e}")
            return False
            
    def unregister_bot(self, bot_id: str) -> bool:
        """Unregister a bot from the Oracle"""
        try:
            # Mark any in-progress tasks as pending
            query = """
            UPDATE scraping_queue 
            SET status = 'pending', assigned_bot_id = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE assigned_bot_id = %s AND status = 'in_progress'
            """
            
            self.db_manager.cursor.execute(query, (bot_id,))
            
            self.logger.info(f"Unregistered bot {bot_id} from Oracle")
            return True
            
        except Exception as e:
            self.logger.error(f"Error unregistering bot {bot_id}: {e}")
            return False
            
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop() 