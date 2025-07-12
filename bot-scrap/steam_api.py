import requests
import re
import time
import random
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from config import Config

class SteamAPI:
    """Steam API wrapper for scraping profile data"""
    
    def __init__(self):
        self.api_key = Config.STEAM_API_KEY
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
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
            
            # If it's a custom URL
            if not steamid.isdigit():
                return self._resolve_vanity_url(steamid)
            
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
            steamid64_pattern = r'(?:profiles/|id/)(\d{17})'
            match = re.search(steamid64_pattern, url)
            
            if match:
                return int(match.group(1))
            
            # Pattern for custom URL
            custom_pattern = r'steamcommunity\.com/id/([^/]+)'
            match = re.search(custom_pattern, url)
            
            if match:
                return self._resolve_vanity_url(match.group(1))
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting SteamID64 from URL: {e}")
            return None
            
    def _resolve_vanity_url(self, vanity_url: str) -> Optional[int]:
        """Resolve vanity URL to SteamID64 using Steam API"""
        try:
            self._rate_limit()
            
            url = f"{Config.STEAM_WEB_API_URL}/ISteamUser/ResolveVanityURL/v0001/"
            params = {
                'key': self.api_key,
                'vanityurl': vanity_url,
                'url_type': 1
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('response', {}).get('success') == 1:
                return int(data['response']['steamid'])
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error resolving vanity URL: {e}")
            return None
            
    def get_player_summaries(self, steamid64: int) -> Optional[Dict[str, Any]]:
        """Get player summary information from Steam API"""
        try:
            self._rate_limit()
            
            url = f"{Config.STEAM_WEB_API_URL}/ISteamUser/GetPlayerSummaries/v0002/"
            params = {
                'key': self.api_key,
                'steamids': str(steamid64)
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            players = data.get('response', {}).get('players', [])
            
            if players:
                return players[0]
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting player summary: {e}")
            return None
            
    def get_player_bans(self, steamid64: int) -> Optional[Dict[str, Any]]:
        """Get player ban information from Steam API"""
        try:
            self._rate_limit()
            
            url = f"{Config.STEAM_WEB_API_URL}/ISteamUser/GetPlayerBans/v1/"
            params = {
                'key': self.api_key,
                'steamids': str(steamid64)
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            players = data.get('players', [])
            
            if players:
                return players[0]
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting player bans: {e}")
            return None
            
    def get_steam_level(self, steamid64: int) -> Optional[int]:
        """Get Steam level from Steam API"""
        try:
            self._rate_limit()
            
            url = f"{Config.STEAM_WEB_API_URL}/IPlayerService/GetSteamLevel/v1/"
            params = {
                'key': self.api_key,
                'steamid': str(steamid64)
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if 'response' in data and 'player_level' in data['response']:
                return data['response']['player_level']
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Error getting Steam level: {e}")
            return 0
            
    def get_friend_list(self, steamid64: int) -> List[int]:
        """Get friend list from Steam API"""
        try:
            self._rate_limit()
            
            url = f"{Config.STEAM_WEB_API_URL}/ISteamUser/GetFriendList/v0001/"
            params = {
                'key': self.api_key,
                'steamid': str(steamid64),
                'relationship': 'friend'
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            friendslist = data.get('friendslist', {})
            friends = friendslist.get('friends', [])
            
            # Extract SteamID64s and limit to max friends per profile
            friend_ids = [int(friend['steamid']) for friend in friends]
            
            # Limit friends to prevent infinite loops
            if len(friend_ids) > Config.MAX_FRIENDS_PER_PROFILE:
                friend_ids = friend_ids[:Config.MAX_FRIENDS_PER_PROFILE]
            
            return friend_ids
            
        except Exception as e:
            self.logger.error(f"Error getting friend list: {e}")
            return []
            
    def scrape_profile_data(self, steamid64: int) -> Optional[Dict[str, Any]]:
        """Scrape comprehensive profile data"""
        try:
            self.logger.info(f"Scraping profile data for SteamID64: {steamid64}")
            
            # Get player summary
            player_summary = self.get_player_summaries(steamid64)
            if not player_summary:
                self.logger.warning(f"Could not get player summary for {steamid64}")
                return None
            
            # Get ban information
            ban_info = self.get_player_bans(steamid64)
            
            # Get Steam level
            steam_level = self.get_steam_level(steamid64)
            
            # Get friend list
            friends = self.get_friend_list(steamid64)
            
            # Extract ban information
            is_banned = False
            ban_date = None
            ban_type = None
            
            if ban_info:
                if ban_info.get('VACBanned'):
                    is_banned = True
                    ban_type = 'VAC'
                    # Calculate ban date from DaysSinceLastBan
                    days_since_ban = ban_info.get('DaysSinceLastBan', 0)
                    if days_since_ban > 0:
                        ban_date = datetime.now().date() - timedelta(days=days_since_ban)
                
                elif ban_info.get('CommunityBanned'):
                    is_banned = True
                    ban_type = 'Community'
                
                elif ban_info.get('EconomyBan') != 'none':
                    is_banned = True
                    ban_type = 'Economy'
            
            # Prepare profile data
            profile_data = {
                'steamid64': steamid64,
                'profile_url': player_summary.get('profileurl', f"{Config.STEAM_PROFILE_URL}{steamid64}"),
                'steam_level': steam_level,
                'avatar_url': player_summary.get('avatarfull', ''),
                'is_banned': is_banned,
                'ban_date': ban_date,
                'ban_type': ban_type,
                'friends': friends
            }
            
            self.logger.info(f"Successfully scraped profile {steamid64} - Level: {steam_level}, Friends: {len(friends)}, Banned: {is_banned}")
            
            return profile_data
            
        except Exception as e:
            self.logger.error(f"Error scraping profile data: {e}")
            return None
            
    def validate_steamid64(self, steamid64: int) -> bool:
        """Validate if SteamID64 is valid"""
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
            
            # Try to get player summary to verify it exists
            player_summary = self.get_player_summaries(steamid64)
            return player_summary is not None
            
        except Exception as e:
            self.logger.error(f"Error validating SteamID64: {e}")
            return False
            
    def get_multiple_player_summaries(self, steamid64_list: List[int]) -> List[Dict[str, Any]]:
        """Get multiple player summaries in one API call (up to 100 at a time)"""
        try:
            # Steam API allows up to 100 steamids per request
            batch_size = 100
            all_players = []
            
            for i in range(0, len(steamid64_list), batch_size):
                batch = steamid64_list[i:i + batch_size]
                
                self._rate_limit()
                
                url = f"{Config.STEAM_WEB_API_URL}/ISteamUser/GetPlayerSummaries/v0002/"
                params = {
                    'key': self.api_key,
                    'steamids': ','.join(map(str, batch))
                }
                
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                players = data.get('response', {}).get('players', [])
                all_players.extend(players)
            
            return all_players
            
        except Exception as e:
            self.logger.error(f"Error getting multiple player summaries: {e}")
            return []

 