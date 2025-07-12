import requests
import re
import time
import random
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from config import Config

class SteamWebScraper:
    """Steam web scraper without API - scrapes directly from web pages"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.logger = logging.getLogger(__name__)
        self.last_request_time = 0
        
    def _rate_limit(self):
        """Apply rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 60 / Config.REQUESTS_PER_MINUTE
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            time.sleep(sleep_time)
            
        # Add random delay to avoid detection
        random_delay = random.uniform(Config.BOT_DELAY_MIN, Config.BOT_DELAY_MAX)
        time.sleep(random_delay)
        
        self.last_request_time = time.time()
        
    def steamid_to_steamid64(self, steamid: str) -> Optional[int]:
        """Convert various Steam ID formats to SteamID64"""
        try:
            # If it's already a SteamID64 (17 digits starting with 7656119)
            if steamid.isdigit() and len(steamid) == 17 and steamid.startswith('7656119'):
                return int(steamid)
            
            # If it's a profile URL
            if steamid.startswith('http'):
                return self._extract_steamid64_from_url(steamid)
            
            # If it's a custom URL, try to resolve it
            if not steamid.isdigit():
                return self._resolve_custom_url(steamid)
            
            # If it's a SteamID32, convert to SteamID64
            if steamid.isdigit() and len(steamid) <= 10:
                return int(steamid) + 76561197960265728
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error converting SteamID: {e}")
            return None
            
    def _extract_steamid64_from_url(self, url: str) -> Optional[int]:
        """Extract SteamID64 from Steam profile URL"""
        try:
            # Pattern for direct SteamID64 in URL
            steamid64_pattern = r'(?:profiles/)(\d{17})'
            match = re.search(steamid64_pattern, url)
            
            if match:
                return int(match.group(1))
            
            # Pattern for custom URL
            custom_pattern = r'steamcommunity\.com/id/([^/]+)'
            match = re.search(custom_pattern, url)
            
            if match:
                return self._resolve_custom_url(match.group(1))
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting SteamID64 from URL: {e}")
            return None
            
    def _resolve_custom_url(self, custom_name: str) -> Optional[int]:
        """Resolve custom URL by scraping the profile page"""
        try:
            self._rate_limit()
            
            url = f"https://steamcommunity.com/id/{custom_name}"
            response = self.session.get(url)
            response.raise_for_status()
            
            # Look for steamid in the page source
            steamid64_pattern = r'steamcommunity\.com/profiles/(\d{17})'
            match = re.search(steamid64_pattern, response.text)
            
            if match:
                return int(match.group(1))
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error resolving custom URL: {e}")
            return None
            
    def get_profile_data(self, steamid64: int) -> Optional[Dict[str, Any]]:
        """Scrape profile data from Steam profile page"""
        try:
            self._rate_limit()
            
            url = f"https://steamcommunity.com/profiles/{steamid64}"
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check if profile exists and is public
            if "This user has not yet set up their Steam Community profile" in response.text:
                self.logger.warning(f"Profile {steamid64} not set up")
                return None
                
            if "This profile is private" in response.text:
                self.logger.warning(f"Profile {steamid64} is private")
                return None
            
            # Extract avatar URL
            avatar_url = ""
            avatar_img = soup.find('div', class_='playerAvatarAutoSizeInner')
            if avatar_img:
                img_tag = avatar_img.find('img')
                if img_tag:
                    avatar_url = img_tag.get('src', '')
            
            # Extract steam level
            steam_level = 0
            level_element = soup.find('span', class_='friendPlayerLevelNum')
            if level_element:
                try:
                    steam_level = int(level_element.text.strip())
                except ValueError:
                    steam_level = 0
            
            # Extract ban information (from profile page)
            is_banned = False
            ban_type = None
            ban_date = None
            
            # Look for ban indicators in profile
            ban_indicators = ['VAC banned', 'Game banned', 'Community banned']
            for indicator in ban_indicators:
                if indicator in response.text:
                    is_banned = True
                    if 'VAC' in indicator:
                        ban_type = 'VAC'
                    elif 'Game' in indicator:
                        ban_type = 'Game'
                    elif 'Community' in indicator:
                        ban_type = 'Community'
                    break
            
            # Get friends list
            friends = self._get_friends_from_profile(steamid64)
            
            profile_data = {
                'steamid64': steamid64,
                'profile_url': url,
                'steam_level': steam_level,
                'avatar_url': avatar_url,
                'is_banned': is_banned,
                'ban_date': ban_date,
                'ban_type': ban_type,
                'friends': friends
            }
            
            self.logger.info(f"Successfully scraped profile {steamid64} - Level: {steam_level}, Friends: {len(friends)}, Banned: {is_banned}")
            
            return profile_data
            
        except Exception as e:
            self.logger.error(f"Error scraping profile {steamid64}: {e}")
            return None
            
    def _get_friends_from_profile(self, steamid64: int) -> List[int]:
        """Get friends list by scraping friends page"""
        try:
            self._rate_limit()
            
            url = f"https://steamcommunity.com/profiles/{steamid64}/friends/"
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            friends = []
            
            # Look for friend links
            friend_links = soup.find_all('a', href=re.compile(r'/profiles/\d{17}'))
            
            for link in friend_links:
                href = link.get('href', '')
                match = re.search(r'/profiles/(\d{17})', href)
                if match:
                    friend_id = int(match.group(1))
                    if friend_id != steamid64:  # Don't include self
                        friends.append(friend_id)
            
            # Limit friends to prevent infinite loops
            if len(friends) > Config.MAX_FRIENDS_PER_PROFILE:
                friends = friends[:Config.MAX_FRIENDS_PER_PROFILE]
            
            self.logger.debug(f"Found {len(friends)} friends for profile {steamid64}")
            return friends
            
        except Exception as e:
            self.logger.error(f"Error getting friends for {steamid64}: {e}")
            return []
            
    def scrape_profile_data(self, steamid64: int) -> Optional[Dict[str, Any]]:
        """Main method to scrape comprehensive profile data"""
        try:
            self.logger.info(f"Scraping profile data for SteamID64: {steamid64}")
            
            profile_data = self.get_profile_data(steamid64)
            
            if profile_data:
                self.logger.info(f"Successfully scraped profile {steamid64}")
                return profile_data
            else:
                self.logger.warning(f"Could not scrape profile {steamid64}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error scraping profile data: {e}")
            return None
            
    def validate_steamid64(self, steamid64: int) -> bool:
        """Validate if SteamID64 is valid by checking if profile exists"""
        try:
            # Basic validation
            if not isinstance(steamid64, int):
                return False
                
            steamid64_str = str(steamid64)
            
            # Must be 17 digits
            if len(steamid64_str) != 17:
                return False
                
            # Must start with 7656119
            if not steamid64_str.startswith('7656119'):
                return False
            
            # Try to access profile to verify it exists
            profile_data = self.get_profile_data(steamid64)
            return profile_data is not None
            
        except Exception as e:
            self.logger.error(f"Error validating SteamID64: {e}")
            return False 