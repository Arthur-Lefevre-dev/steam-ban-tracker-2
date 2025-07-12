#!/usr/bin/env python3
"""
Debug script to identify why bots are not scraping
"""
import time
import logging
from bot_scraper import BotManager
from shared_oracle import shared_oracle
from config import Config

# Setup detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def debug_oracle():
    """Debug Oracle status"""
    print("=== Debug Oracle ===")
    
    # Check if Oracle is started
    print(f"Oracle started: {shared_oracle._initialized}")
    
    # Check queue status
    try:
        queue_status = shared_oracle.get_queue_status()
        print(f"Queue status: {queue_status}")
        
        # Check pending tasks
        pending = queue_status.get('pending_tasks', 0)
        print(f"Pending tasks: {pending}")
        
        if pending == 0:
            print("❌ No pending tasks - this is the problem!")
            return False
        else:
            print("✅ Tasks are pending")
            return True
            
    except Exception as e:
        print(f"❌ Error getting queue status: {e}")
        return False

def debug_bot_loop():
    """Debug a single bot's scraping loop"""
    print("\n=== Debug Bot Loop ===")
    
    # Create a single bot
    manager = BotManager()
    bot_id = manager.create_bot()
    
    # Start Oracle
    shared_oracle.start()
    
    # Add seed profile
    manager.add_seed_profile(Config.SEED_PROFILE)
    
    # Check if task is available
    steamid64 = shared_oracle.request_task(bot_id)
    print(f"Task requested for {bot_id}: {steamid64}")
    
    if steamid64:
        print(f"✅ Bot {bot_id} got task: {steamid64}")
        
        # Try to scrape manually
        from steam_scraper import SteamWebScraper
        scraper = SteamWebScraper()
        
        print(f"🔍 Attempting to scrape {steamid64}...")
        profile_data = scraper.scrape_profile_data(steamid64)
        
        if profile_data:
            print(f"✅ Scraping successful!")
            print(f"  Level: {profile_data['steam_level']}")
            print(f"  Friends: {len(profile_data['friends'])}")
            print(f"  Banned: {profile_data['is_banned']}")
            
            # Try to submit result
            success = shared_oracle.submit_result(bot_id, steamid64, profile_data)
            print(f"Submit result: {success}")
            
            return True
        else:
            print("❌ Scraping failed")
            return False
    else:
        print("❌ No task available")
        return False

def debug_database():
    """Debug database state"""
    print("\n=== Debug Database ===")
    
    try:
        from database import DatabaseManager
        
        with DatabaseManager() as db:
            # Check queue table
            db.cursor.execute("SELECT COUNT(*) as count FROM scraping_queue WHERE status = 'pending'")
            result = db.cursor.fetchone()
            pending = result['count']
            print(f"Pending tasks in DB: {pending}")
            
            # Check profiles table
            db.cursor.execute("SELECT COUNT(*) as count FROM steam_profiles")
            result = db.cursor.fetchone()
            profiles = result['count']
            print(f"Profiles in DB: {profiles}")
            
            # Show recent queue entries
            db.cursor.execute("SELECT * FROM scraping_queue ORDER BY created_at DESC LIMIT 5")
            queue_entries = db.cursor.fetchall()
            print(f"Recent queue entries: {len(queue_entries)}")
            for entry in queue_entries:
                print(f"  {entry['steamid64']} - {entry['status']} - {entry['assigned_bot_id']}")
            
            return pending > 0
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def main():
    print("🔍 Debug du système de scraping\n")
    
    # Test 1: Database
    db_ok = debug_database()
    
    # Test 2: Oracle
    oracle_ok = debug_oracle()
    
    # Test 3: Bot loop
    bot_ok = debug_bot_loop()
    
    print(f"\n=== Résumé ===")
    print(f"Database: {'✅' if db_ok else '❌'}")
    print(f"Oracle: {'✅' if oracle_ok else '❌'}")
    print(f"Bot Loop: {'✅' if bot_ok else '❌'}")
    
    if not db_ok:
        print("\n💡 Solution: Vérifiez la base de données")
    elif not oracle_ok:
        print("\n💡 Solution: Problème avec l'Oracle")
    elif not bot_ok:
        print("\n💡 Solution: Problème avec le scraping")
    else:
        print("\n🎉 Tout semble fonctionner !")

if __name__ == "__main__":
    main() 