import requests
import re
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
import time


@dataclass
class InstagramProfile:
    """Instagram profile data model"""
    username: str
    full_name: Optional[str] = None
    biography: Optional[str] = None
    follower_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    profile_picture_url: Optional[str] = None
    is_verified: bool = False
    category: Optional[str] = None
    external_url: Optional[str] = None
    
    def to_dict(self):
        """Convert to dictionary for JSON output"""
        return asdict(self)


class InstagramScraper:
    """Instagram scraper that parses embedded JSON from HTML pages"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        })
    
    def get_profile(self, username: str, retry_count: int = 3) -> Optional[InstagramProfile]:
        """
        Fetch Instagram profile by parsing embedded JSON from HTML page.
        
        Args:
            username: Instagram username
            retry_count: Number of retry attempts
            
        Returns:
            InstagramProfile object or None if failed
        """
        url = f"https://www.instagram.com/{username}/"
        
        for attempt in range(retry_count):
            try:
                print(f"\n[Attempt {attempt + 1}/{retry_count}] Fetching profile: @{username}")
                
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                
                html = response.text
                
                # Try multiple extraction methods
                user_data = self._extract_user_data(html, username)
                
                if not user_data:
                    print(f"⚠️ Could not extract user data from HTML")
                    if attempt < retry_count - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        print(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    return None
                
                # Parse and create profile
                profile = self._parse_profile(user_data, username)
                print(f"✅ Successfully scraped @{username}")
                return profile
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    print(f"❌ Profile not found: @{username}")
                    return None
                elif e.response.status_code == 429:
                    print(f"⚠️ Rate limited. Waiting before retry...")
                    time.sleep(5 * (attempt + 1))
                else:
                    print(f"❌ HTTP Error {e.response.status_code}: {e}")
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ Request Error: {e}")
                
            except Exception as e:
                print(f"❌ Unexpected Error: {e}")
            
            if attempt < retry_count - 1:
                wait_time = 2 ** attempt
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        return None
    
    def _extract_user_data(self, html: str, username: str) -> Optional[Dict[str, Any]]:
        """
        Extract user data from HTML using multiple methods.
        Instagram frequently changes their HTML structure.
        """
        # Method 1: window._sharedData (legacy format)
        user_data = self._try_shared_data(html)
        if user_data:
            print("📦 Found data in window._sharedData")
            return user_data
        
        # Method 2: <script type="application/json"> tags (current format)
        user_data = self._try_json_scripts(html, username)
        if user_data:
            print("📦 Found data in JSON script tags")
            return user_data
        
        # Method 3: ld+json schema
        user_data = self._try_ld_json(html, username)
        if user_data:
            print("📦 Found data in ld+json schema")
            return user_data
        
        return None
    
    def _try_shared_data(self, html: str) -> Optional[Dict[str, Any]]:
        """Extract from window._sharedData (older Instagram format)"""
        try:
            pattern = r'window\._sharedData\s*=\s*({.+?});>'
            match = re.search(pattern, html, re.DOTALL)
            
            if match:
                data = json.loads(match.group(1))
                user = data.get('entry_data', {}).get('ProfilePage', [{}])[0].get('graphql', {}).get('user')
                return user
        except Exception as e:
            pass
        
        return None
    
    def _try_json_scripts(self, html: str, username: str) -> Optional[Dict[str, Any]]:
        """Extract from <script type="application/json"> tags (newer format)"""
        try:
            # Find all JSON script tags
            pattern = r'<script type="application/json"[^>]*>({.+?})</script>'
            matches = re.findall(pattern, html, re.DOTALL)
            
            for match in matches:
                try:
                    data = json.loads(match)
                    # Recursively search for user data
                    user_data = self._find_user_in_json(data, username)
                    if user_data:
                        return user_data
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass
        
        return None
    
    def _try_ld_json(self, html: str, username: str) -> Optional[Dict[str, Any]]:
        """Extract from ld+json schema (limited data)"""
        try:
            pattern = r'<script type="application/ld\+json">({.+?})</script>'
            match = re.search(pattern, html, re.DOTALL)
            
            if match:
                data = json.loads(match.group(1))
                # This format has very limited data, mainly for SEO
                # Return a minimal structure if it matches the username
                if data.get('mainEntityOfPage', {}).get('url', '').endswith(f'/{username}/'):
                    return {
                        'username': username,
                        'full_name': data.get('name'),
                        'biography': data.get('description'),
                    }
        except Exception:
            pass
        
        return None
    
    def _find_user_in_json(self, data: Any, username: str) -> Optional[Dict[str, Any]]:
        """
        Recursively search nested JSON for user profile data.
        Looks for objects with username and follower data.
        """
        if isinstance(data, dict):
            # Check if this is user profile data
            if (data.get('username') == username and 
                ('edge_followed_by' in data or 'follower_count' in data)):
                return data
            
            # Recursively check all values
            for key, value in data.items():
                result = self._find_user_in_json(value, username)
                if result:
                    return result
        
        elif isinstance(data, list):
            for item in data:
                result = self._find_user_in_json(item, username)
                if result:
                    return result
        
        return None
    
    def _parse_profile(self, user_data: Dict[str, Any], username: str) -> InstagramProfile:
        """Parse user data into InstagramProfile object"""
        
        # Handle different data structures
        follower_count = 0
        following_count = 0
        posts_count = 0
        
        # Try edge_followed_by format (GraphQL)
        if 'edge_followed_by' in user_data:
            follower_count = user_data['edge_followed_by'].get('count', 0)
        elif 'follower_count' in user_data:
            follower_count = user_data['follower_count']
        
        if 'edge_follow' in user_data:
            following_count = user_data['edge_follow'].get('count', 0)
        elif 'following_count' in user_data:
            following_count = user_data['following_count']
        
        if 'edge_owner_to_timeline_media' in user_data:
            posts_count = user_data['edge_owner_to_timeline_media'].get('count', 0)
        elif 'media_count' in user_data:
            posts_count = user_data['media_count']
        
        # Get profile picture URL (try HD first, fallback to regular)
        profile_pic = (user_data.get('profile_pic_url_hd') or 
                      user_data.get('profile_pic_url'))
        
        # Get category (try multiple fields)
        category = (user_data.get('category_name') or 
                   user_data.get('business_category_name') or
                   user_data.get('category'))
        
        return InstagramProfile(
            username=user_data.get('username', username),
            full_name=user_data.get('full_name'),
            biography=user_data.get('biography'),
            follower_count=follower_count,
            following_count=following_count,
            posts_count=posts_count,
            profile_picture_url=profile_pic,
            is_verified=user_data.get('is_verified', False),
            category=category,
            external_url=user_data.get('external_url'),
        )

