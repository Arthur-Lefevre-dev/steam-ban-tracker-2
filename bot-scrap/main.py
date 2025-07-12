#!/usr/bin/env python3
"""
Steam Profile Scraper Bot
Main application entry point for managing Steam scraper bots
"""

import sys
import os
import logging
import argparse
import time
import signal
import json
from datetime import datetime
from typing import Optional, List

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from bot_scraper import BotManager, SteamScraperBot
from colorama import init, Fore, Back, Style

# Initialize colorama for colored output
init(autoreset=True)

class SteamScraperApp:
    """Main application class for Steam scraper"""
    
    def __init__(self):
        self.bot_manager = BotManager()
        self.logger = None
        self.running = False
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, Config.LOG_LEVEL),
            format=Config.LOG_FORMAT,
            handlers=[
                logging.FileHandler(f'steam_scraper_{datetime.now().strftime("%Y%m%d")}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def validate_config(self) -> bool:
        """Validate configuration before starting"""
        try:
            Config.validate_config()
            self.logger.info("Configuration validation successful")
            return True
        except ValueError as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False
            
    def create_bots(self, count: int) -> List[str]:
        """Create multiple bots"""
        bot_ids = []
        for i in range(count):
            bot_id = self.bot_manager.create_bot()
            bot_ids.append(bot_id)
            print(f"{Fore.GREEN}✓ Created bot: {bot_id}")
        
        return bot_ids
        
    def start_scraping(self, bot_count: int, seed_profiles: List[str]) -> bool:
        """Start scraping process"""
        print(f"\n{Fore.CYAN}=== Starting Steam Profile Scraper ==={Style.RESET_ALL}")
        
        # Validate configuration
        if not self.validate_config():
            return False
            
        # Create bots
        print(f"\n{Fore.YELLOW}Creating {bot_count} bots...")
        bot_ids = self.create_bots(bot_count)
        
        # Add seed profiles
        print(f"\n{Fore.YELLOW}Adding seed profiles...")
        for seed_profile in seed_profiles:
            if self.bot_manager.add_seed_profile(seed_profile):
                print(f"{Fore.GREEN}✓ Added seed profile: {seed_profile}")
            else:
                print(f"{Fore.RED}✗ Failed to add seed profile: {seed_profile}")
                
        # Start all bots
        print(f"\n{Fore.YELLOW}Starting bots...")
        started_count = self.bot_manager.start_all_bots()
        
        if started_count == 0:
            print(f"{Fore.RED}✗ No bots started successfully")
            return False
            
        print(f"{Fore.GREEN}✓ Started {started_count} out of {bot_count} bots")
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = True
        return True
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n{Fore.YELLOW}Received signal {signum}, shutting down...")
        self.running = False
        
    def run_interactive_mode(self):
        """Run in interactive mode with status updates"""
        print(f"\n{Fore.CYAN}=== Interactive Mode Started ==={Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Press Ctrl+C to stop\n")
        
        try:
            while self.running:
                # Display status
                self.display_status()
                
                # Wait before next update
                time.sleep(30)
                
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Keyboard interrupt received...")
            
        finally:
            self.shutdown()
            
    def display_status(self):
        """Display current status of bots and scraping progress"""
        try:
            # Get summary statistics
            summary = self.bot_manager.get_summary_statistics()
            
            # Clear screen (works on most terminals)
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print(f"{Fore.CYAN}=== Steam Profile Scraper Status ==={Style.RESET_ALL}")
            print(f"{Fore.WHITE}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            
            # Bot statistics
            print(f"{Fore.YELLOW}Bot Statistics:")
            print(f"  Total Bots: {summary['total_bots']}")
            print(f"  Running Bots: {summary['running_bots']}")
            print(f"  Profiles Scraped: {summary['total_profiles_scraped']}")
            print(f"  Profiles Failed: {summary['total_profiles_failed']}")
            print(f"  Success Rate: {summary['overall_success_rate']:.1f}%")
            print()
            
            # Queue status
            queue_status = summary.get('queue_status', {})
            print(f"{Fore.YELLOW}Queue Status:")
            print(f"  Pending Tasks: {queue_status.get('pending_tasks', 0)}")
            print(f"  Total Scraped: {queue_status.get('scraped_profiles', 0)}")
            print(f"  Active Bots: {queue_status.get('active_bots', 0)}")
            print()
            
            # Individual bot status
            bot_statuses = self.bot_manager.get_all_bot_status()
            if bot_statuses:
                print(f"{Fore.YELLOW}Individual Bot Status:")
                for bot_id, status in bot_statuses.items():
                    status_color = Fore.GREEN if status['running'] else Fore.RED
                    print(f"  {status_color}{bot_id}: {status['profiles_scraped']} scraped, {status['profiles_failed']} failed, {status['success_rate']:.1f}% success")
            
        except Exception as e:
            print(f"{Fore.RED}Error displaying status: {e}")
            
    def shutdown(self):
        """Shutdown all bots gracefully"""
        print(f"\n{Fore.YELLOW}Shutting down bots...")
        self.bot_manager.stop_all_bots()
        print(f"{Fore.GREEN}✓ All bots stopped")
        print(f"{Fore.CYAN}Thank you for using Steam Profile Scraper!")
        
    def run_single_profile(self, profile_input: str):
        """Run scraper for a single profile"""
        print(f"\n{Fore.CYAN}=== Single Profile Mode ==={Style.RESET_ALL}")
        
        if not self.validate_config():
            return False
            
        # Create single bot
        bot_id = self.bot_manager.create_bot()
        print(f"{Fore.GREEN}✓ Created bot: {bot_id}")
        
        # Add seed profile
        if self.bot_manager.add_seed_profile(profile_input):
            print(f"{Fore.GREEN}✓ Added seed profile: {profile_input}")
        else:
            print(f"{Fore.RED}✗ Failed to add seed profile: {profile_input}")
            return False
            
        # Start bot
        if self.bot_manager.start_bot(bot_id):
            print(f"{Fore.GREEN}✓ Started bot: {bot_id}")
        else:
            print(f"{Fore.RED}✗ Failed to start bot: {bot_id}")
            return False
            
        # Wait for completion or timeout
        print(f"{Fore.YELLOW}Scraping profile...")
        start_time = time.time()
        timeout = 300  # 5 minutes timeout
        
        while time.time() - start_time < timeout:
            status = self.bot_manager.get_all_bot_status()[bot_id]
            if status['profiles_scraped'] > 0 or status['profiles_failed'] > 0:
                break
            time.sleep(5)
            
        # Show results
        final_status = self.bot_manager.get_all_bot_status()[bot_id]
        if final_status['profiles_scraped'] > 0:
            print(f"{Fore.GREEN}✓ Profile scraped successfully!")
        else:
            print(f"{Fore.RED}✗ Profile scraping failed or timed out")
            
        self.bot_manager.stop_bot(bot_id)
        return True


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Steam Profile Scraper Bot')
    parser.add_argument('--bots', type=int, default=1, help='Number of bots to create (default: 1)')
    parser.add_argument('--seed', nargs='+', help='Seed profiles to start scraping (SteamID64, URLs, or custom URLs)')
    parser.add_argument('--single', type=str, help='Run single profile scraping mode')
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode with status updates')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Create application
    app = SteamScraperApp()
    
    try:
        if args.single:
            # Single profile mode
            app.run_single_profile(args.single)
            
        elif args.seed:
            # Multi-bot scraping mode
            if app.start_scraping(args.bots, args.seed):
                if args.interactive:
                    app.run_interactive_mode()
                else:
                    print(f"{Fore.GREEN}Scraping started. Use --interactive flag for status updates.")
                    try:
                        while True:
                            time.sleep(1)
                    except KeyboardInterrupt:
                        print(f"\n{Fore.YELLOW}Stopping...")
                        app.shutdown()
        else:
            # Show help if no arguments
            parser.print_help()
            print(f"\n{Fore.YELLOW}Examples:")
            print(f"  python main.py --seed 76561198000000000 --bots 3 --interactive")
            print(f"  python main.py --seed https://steamcommunity.com/profiles/76561198000000000 --bots 1")
            print(f"  python main.py --single 76561198000000000")
            print(f"  python main.py --seed customurl --bots 2")
            
    except Exception as e:
        print(f"{Fore.RED}Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 