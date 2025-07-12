#!/usr/bin/env python3
"""
Example usage of Steam Profile Scraper Bot
This file shows how to use the scraper system programmatically.
"""

import time
import logging
from bot_scraper import BotManager, SteamScraperBot
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def example_single_bot():
    """Example using a single bot"""
    print("=== Single Bot Example ===")
    
    # Create and start a single bot
    with SteamScraperBot() as bot:
        print(f"Bot created: {bot.bot_id}")
        
        # Add seed profile (replace with a real SteamID64)
        seed_profile = "76561198000000000"  # Replace with actual SteamID64
        if bot.add_seed_profile(seed_profile):
            print(f"Added seed profile: {seed_profile}")
            
            # Let it run for a while
            time.sleep(60)
            
            # Check status
            status = bot.get_status()
            print(f"Bot status: {status}")
        else:
            print("Failed to add seed profile")

def example_multiple_bots():
    """Example using multiple bots with BotManager"""
    print("\n=== Multiple Bots Example ===")
    
    with BotManager() as manager:
        # Create multiple bots
        bot_ids = []
        for i in range(3):
            bot_id = manager.create_bot()
            bot_ids.append(bot_id)
            print(f"Created bot: {bot_id}")
        
        # Add seed profiles
        seed_profiles = [
            "76561198000000000",  # Replace with actual SteamID64s
            "76561198000000001",
            "76561198000000002"
        ]
        
        for profile in seed_profiles:
            if manager.add_seed_profile(profile):
                print(f"Added seed profile: {profile}")
        
        # Start all bots
        started_count = manager.start_all_bots()
        print(f"Started {started_count} bots")
        
        if started_count > 0:
            # Run for a while and monitor
            for i in range(5):  # 5 minutes total
                time.sleep(60)  # Wait 1 minute
                
                # Get statistics
                stats = manager.get_summary_statistics()
                print(f"Progress: {stats['total_profiles_scraped']} profiles scraped, "
                      f"{stats['queue_status'].get('pending_tasks', 0)} pending")
                
                # Get individual bot status
                bot_statuses = manager.get_all_bot_status()
                for bot_id, status in bot_statuses.items():
                    print(f"  {bot_id}: {status['profiles_scraped']} scraped, "
                          f"{status['success_rate']:.1f}% success rate")

def example_with_error_handling():
    """Example with proper error handling"""
    print("\n=== Error Handling Example ===")
    
    try:
        # Validate configuration first
        Config.validate_config()
        print("Configuration validated successfully")
        
        # Create bot manager
        manager = BotManager()
        
        # Create a single bot
        bot_id = manager.create_bot()
        print(f"Created bot: {bot_id}")
        
        # Try to add seed profile
        seed_profile = "invalid_profile"  # This will fail
        if not manager.add_seed_profile(seed_profile):
            print(f"Failed to add seed profile: {seed_profile}")
            
            # Try with a better format
            seed_profile = "76561198000000000"  # Replace with actual SteamID64
            if manager.add_seed_profile(seed_profile):
                print(f"Successfully added seed profile: {seed_profile}")
                
                # Start the bot
                if manager.start_bot(bot_id):
                    print(f"Bot {bot_id} started successfully")
                    
                    # Monitor for a short time
                    time.sleep(30)
                    
                    # Check final status
                    status = manager.get_all_bot_status()[bot_id]
                    print(f"Final status: {status}")
                else:
                    print(f"Failed to start bot {bot_id}")
            else:
                print("Failed to add any seed profile")
        
        # Clean up
        manager.stop_all_bots()
        print("All bots stopped")
        
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please check your .env file and Steam API key")
    except Exception as e:
        print(f"Unexpected error: {e}")

def example_custom_configuration():
    """Example showing how to work with custom configuration"""
    print("\n=== Custom Configuration Example ===")
    
    print(f"Current configuration:")
    print(f"  Database: {Config.DB_NAME}@{Config.DB_HOST}:{Config.DB_PORT}")
    print(f"  Max concurrent bots: {Config.MAX_CONCURRENT_BOTS}")
    print(f"  Bot delay: {Config.BOT_DELAY_MIN}-{Config.BOT_DELAY_MAX} seconds")
    print(f"  Requests per minute: {Config.REQUESTS_PER_MINUTE}")
    print(f"  Max friends per profile: {Config.MAX_FRIENDS_PER_PROFILE}")
    print(f"  Oracle check interval: {Config.ORACLE_CHECK_INTERVAL} seconds")

def main():
    """Main example function"""
    print("Steam Profile Scraper Bot - Usage Examples")
    print("=" * 50)
    
    # Show configuration
    example_custom_configuration()
    
    # Example with error handling (always run this first)
    example_with_error_handling()
    
    # Uncomment to run other examples
    # example_single_bot()
    # example_multiple_bots()
    
    print("\n" + "=" * 50)
    print("Examples completed!")
    print("\nNote: Replace the example SteamID64s with real ones to test scraping.")
    print("Make sure your .env file is configured properly before running.")

if __name__ == "__main__":
    main() 