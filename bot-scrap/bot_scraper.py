import threading
import time
import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from steam_scraper import SteamWebScraper
from shared_oracle import shared_oracle
from config import Config

class SteamScraperBot:
    """Main Steam scraper bot that coordinates with Oracle"""
    
    def __init__(self, bot_id: Optional[str] = None):
        self.bot_id = bot_id or f"bot_{uuid.uuid4().hex[:8]}"
        self.steam_scraper = SteamWebScraper()
        self.oracle = shared_oracle  # Use shared Oracle instance
        self.logger = logging.getLogger(f"{__name__}.{self.bot_id}")
        self.running = False
        self.scraping_thread = None
        self.stats = {
            'profiles_scraped': 0,
            'profiles_failed': 0,
            'start_time': None,
            'last_activity': None
        }
        
    def start(self) -> bool:
        """Start the scraper bot"""
        try:
            # Register bot with Oracle (Oracle is already started by BotManager)
            if not self.oracle.register_bot(self.bot_id):
                self.logger.error("Failed to register bot with Oracle")
                return False
            
            self.running = True
            self.stats['start_time'] = datetime.now()
            
            # Start scraping thread
            self.scraping_thread = threading.Thread(target=self._scraping_loop, daemon=True)
            self.scraping_thread.start()
            
            self.logger.info(f"Steam scraper bot {self.bot_id} started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting bot: {e}")
            return False
            
    def stop(self):
        """Stop the scraper bot"""
        self.running = False
        
        if self.scraping_thread:
            self.scraping_thread.join()
        
        # Unregister bot from Oracle
        self.oracle.unregister_bot(self.bot_id)
        
        self.logger.info(f"Steam scraper bot {self.bot_id} stopped")
        
    def add_seed_profile(self, steamid_input: str, priority: int = 1) -> bool:
        """Add a seed profile to start scraping"""
        try:
            # Convert input to SteamID64
            steamid64 = self.steam_scraper.steamid_to_steamid64(steamid_input)
            
            if not steamid64:
                self.logger.error(f"Could not convert {steamid_input} to SteamID64")
                return False
            
            # Validate SteamID64
            if not self.steam_scraper.validate_steamid64(steamid64):
                self.logger.error(f"Invalid SteamID64: {steamid64}")
                return False
            
            # Add to Oracle queue
            success = self.oracle.add_seed_profile(steamid64, priority)
            
            if success:
                self.logger.info(f"Added seed profile {steamid64} to scraping queue")
            else:
                self.logger.info(f"Seed profile {steamid64} already in queue")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error adding seed profile: {e}")
            return False
            
    def _scraping_loop(self):
        """Main scraping loop"""
        while self.running:
            try:
                # Request task from Oracle
                steamid64 = self.oracle.request_task(self.bot_id)
                
                if steamid64:
                    self.stats['last_activity'] = datetime.now()
                    
                    # Scrape profile
                    if self._scrape_profile(steamid64):
                        self.stats['profiles_scraped'] += 1
                        self.logger.info(f"Successfully scraped profile {steamid64}")
                    else:
                        self.stats['profiles_failed'] += 1
                        self.logger.warning(f"Failed to scrape profile {steamid64}")
                else:
                    # No tasks available, wait before checking again
                    time.sleep(Config.ORACLE_CHECK_INTERVAL)
                    
            except Exception as e:
                self.logger.error(f"Error in scraping loop: {e}")
                time.sleep(5)  # Wait before retrying
                
    def _scrape_profile(self, steamid64: int) -> bool:
        """Scrape a single profile"""
        try:
            self.logger.info(f"Starting scrape for profile {steamid64}")
            
            # Scrape profile data using web scraper
            profile_data = self.steam_scraper.scrape_profile_data(steamid64)
            
            if profile_data:
                # Submit result to Oracle
                if self.oracle.submit_result(self.bot_id, steamid64, profile_data):
                    self.logger.info(f"Successfully submitted result for profile {steamid64}")
                    return True
                else:
                    self.logger.error(f"Failed to submit result for profile {steamid64}")
                    self.oracle.report_failure(self.bot_id, steamid64, "Failed to submit result")
                    return False
            else:
                # Report failure to Oracle
                error_msg = f"Failed to scrape profile data for {steamid64}"
                self.oracle.report_failure(self.bot_id, steamid64, error_msg)
                return False
                
        except Exception as e:
            self.logger.error(f"Error scraping profile {steamid64}: {e}")
            self.oracle.report_failure(self.bot_id, steamid64, str(e))
            return False
            
    def get_status(self) -> Dict[str, Any]:
        """Get current bot status"""
        uptime = None
        if self.stats['start_time']:
            uptime = datetime.now() - self.stats['start_time']
        
        return {
            'bot_id': self.bot_id,
            'running': self.running,
            'uptime': str(uptime) if uptime else None,
            'profiles_scraped': self.stats['profiles_scraped'],
            'profiles_failed': self.stats['profiles_failed'],
            'last_activity': self.stats['last_activity'].isoformat() if self.stats['last_activity'] else None,
            'success_rate': self._calculate_success_rate()
        }
        
    def _calculate_success_rate(self) -> float:
        """Calculate success rate percentage"""
        total = self.stats['profiles_scraped'] + self.stats['profiles_failed']
        if total == 0:
            return 0.0
        return (self.stats['profiles_scraped'] / total) * 100
        
    def get_queue_status(self) -> Dict[str, int]:
        """Get current queue status from Oracle"""
        return self.oracle.get_queue_status()
        
    def get_bot_statistics(self) -> Dict[str, Any]:
        """Get detailed bot statistics from Oracle"""
        return self.oracle.get_bot_statistics()
        
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class BotManager:
    """Manager for multiple Steam scraper bots"""
    
    def __init__(self):
        self.bots = {}
        self.logger = logging.getLogger(__name__)
        self.oracle_started = False
        
    def create_bot(self, bot_id: Optional[str] = None) -> str:
        """Create a new bot and return its ID"""
        bot = SteamScraperBot(bot_id)
        self.bots[bot.bot_id] = bot
        self.logger.info(f"Created bot {bot.bot_id}")
        return bot.bot_id
        
    def start_bot(self, bot_id: str) -> bool:
        """Start a specific bot"""
        if bot_id not in self.bots:
            self.logger.error(f"Bot {bot_id} not found")
            return False
        
        return self.bots[bot_id].start()
        
    def stop_bot(self, bot_id: str) -> bool:
        """Stop a specific bot"""
        if bot_id not in self.bots:
            self.logger.error(f"Bot {bot_id} not found")
            return False
        
        self.bots[bot_id].stop()
        return True
        
    def start_all_bots(self) -> int:
        """Start all bots and return count of successfully started bots"""
        # Start shared Oracle first
        if not self.oracle_started:
            if shared_oracle.start():
                self.oracle_started = True
                self.logger.info("Shared Oracle started successfully")
            else:
                self.logger.error("Failed to start shared Oracle")
                return 0
        
        # Add seed profile automatically if configured
        if Config.SEED_PROFILE and self.bots:
            self.logger.info(f"Adding seed profile from config: {Config.SEED_PROFILE}")
            self.add_seed_profile(Config.SEED_PROFILE, priority=10)
        
        started_count = 0
        for bot_id, bot in self.bots.items():
            if bot.start():
                started_count += 1
                self.logger.info(f"Started bot {bot_id}")
            else:
                self.logger.error(f"Failed to start bot {bot_id}")
        
        return started_count
        
    def stop_all_bots(self):
        """Stop all bots"""
        for bot_id, bot in self.bots.items():
            bot.stop()
            self.logger.info(f"Stopped bot {bot_id}")
        
        # Stop shared Oracle
        if self.oracle_started:
            shared_oracle.stop()
            self.oracle_started = False
            self.logger.info("Shared Oracle stopped")
            
    def add_seed_profile(self, steamid_input: str, priority: int = 1) -> bool:
        """Add seed profile using shared Oracle"""
        try:
            # Convert input to SteamID64
            steam_scraper = SteamWebScraper()
            steamid64 = steam_scraper.steamid_to_steamid64(steamid_input)
            
            if not steamid64:
                self.logger.error(f"Could not convert {steamid_input} to SteamID64")
                return False
            
            # Add to Oracle queue using shared Oracle
            success = shared_oracle.add_seed_profile(steamid64, priority)
            
            if success:
                self.logger.info(f"Added seed profile {steamid64} to scraping queue")
            else:
                self.logger.info(f"Seed profile {steamid64} already in queue")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error adding seed profile: {e}")
            return False
        
    def get_all_bot_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all bots"""
        status = {}
        for bot_id, bot in self.bots.items():
            status[bot_id] = bot.get_status()
        return status
        
    def get_summary_statistics(self) -> Dict[str, Any]:
        """Get summary statistics for all bots"""
        total_scraped = sum(bot.stats['profiles_scraped'] for bot in self.bots.values())
        total_failed = sum(bot.stats['profiles_failed'] for bot in self.bots.values())
        running_bots = sum(1 for bot in self.bots.values() if bot.running)
        
        # Get queue status from shared Oracle
        queue_status = {}
        if self.oracle_started:
            queue_status = shared_oracle.get_queue_status()
        
        return {
            'total_bots': len(self.bots),
            'running_bots': running_bots,
            'total_profiles_scraped': total_scraped,
            'total_profiles_failed': total_failed,
            'overall_success_rate': (total_scraped / (total_scraped + total_failed) * 100) if (total_scraped + total_failed) > 0 else 0.0,
            'queue_status': queue_status
        }
        
    def remove_bot(self, bot_id: str) -> bool:
        """Remove a bot from the manager"""
        if bot_id not in self.bots:
            self.logger.error(f"Bot {bot_id} not found")
            return False
        
        # Stop bot if running
        self.bots[bot_id].stop()
        
        # Remove from manager
        del self.bots[bot_id]
        self.logger.info(f"Removed bot {bot_id}")
        return True
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_all_bots() 