import requests
import json
from typing import Optional, List, Dict
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models.instagram import InstagramProfile, InstagramPost
import time


class InstagramScraper:
    
    def __init__(self, proxies: Optional[List[Dict[str, str]]] = None):
        self.base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "X-IG-App-ID": "936619743392459",
            "X-ASBD-ID": "129477",
            "X-IG-WWW-Claim": "0",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        
        self.proxies = proxies or []
        self.current_proxy_index = 0
        self.doc_id = "34579740524958711"
    
    def _get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Get next proxy from rotation pool"""
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        return proxy
    
    def get_profile(self, username: str) -> Optional[InstagramProfile]:
        """Fetch Instagram profile data"""
        url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}&hl=en"
        
        headers = self.base_headers.copy()
        headers["Referer"] = f"https://www.instagram.com/{username}/"
        
        proxy = self._get_next_proxy()
        
        try:
            resp = requests.get(url, headers=headers, proxies=proxy, timeout=10)
            resp.raise_for_status()
            
            data = resp.json()
            
            if data.get("status") != "ok":
                print(f"Error: {data.get('message', 'Unknown error')}")
                return None
            
            user = data["data"]["user"]
            
            profile = InstagramProfile(
                username=user["username"],
                full_name=user.get("full_name"),
                biography=user.get("biography"),
                follower_count=user.get("edge_followed_by", {}).get("count", 0),
                following_count=user.get("edge_follow", {}).get("count", 0),
                posts_count=user.get("edge_owner_to_timeline_media", {}).get("count", 0),
                profile_picture_url=user.get("profile_pic_url_hd") or user.get("profile_pic_url"),
                is_verified=user.get("is_verified", False),
                category=user.get("category_name") or user.get("business_category_name"),
                external_url=user.get("external_url"),
            )
            
            return profile
            
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def get_posts(self, username: str, max_posts: Optional[int] = 100) -> List[InstagramPost]:
        """
        Fetch posts from Instagram profile using GraphQL with pagination.
        
        Args:
            username: Instagram username
            max_posts: Maximum number of posts to fetch (None = all posts)
            
        Returns:
            List of InstagramPost objects
        """
        all_posts = []
        seen_ids = set()
        has_next_page = True
        end_cursor = None
        page = 1
        consecutive_empty_pages = 0
        
        while has_next_page:
            variables = {
                "data": {
                    "count": 12,
                    "include_reel_media_seen_timestamp": True,
                    "include_relationship_info": True,
                    "latest_besties_reel_media": True,
                    "latest_reel_media": True
                },
                "username": username
            }
            
            if end_cursor:
                variables["after"] = end_cursor
            
            posts_data = self._fetch_posts_page(variables)
            
            if not posts_data:
                print("Error: Failed to fetch posts page")
                break
            
            edges = posts_data.get("edges", [])
            page_info = posts_data.get("page_info", {})
            
            new_posts_count = 0
            
            if not edges:
                consecutive_empty_pages += 1
                if consecutive_empty_pages >= 3:
                    break
                page += 1
                continue
            
            consecutive_empty_pages = 0
            
            for edge in edges:
                node = edge["node"]
                post_id = node.get("code") or node.get("id") or node.get("pk")
                
                if post_id in seen_ids:
                    continue
                
                seen_ids.add(post_id)
                
                # Collect display and video URLs for carousel items
                display_urls = []
                video_urls = []
                carousel_items = node.get("carousel_media", [])
                
                if carousel_items:
                    for item in carousel_items:
                        display_url = self._get_display_url(item)
                        video_url = self._get_video_url(item)
                        if display_url:
                            display_urls.append(display_url)
                        if video_url:
                            video_urls.append(video_url)
                else:
                    display_url = self._get_display_url(node)
                    video_url = self._get_video_url(node)
                    if display_url:
                        display_urls.append(display_url)
                    if video_url:
                        video_urls.append(video_url)
                
                post = InstagramPost(
                    post_id=node.get("code"),
                    instagram_id=node.get("id") or node.get("pk"),
                    media_type=self._get_media_type(node),
                    caption=self._get_caption(node),
                    like_count=node.get("like_count", 0),
                    comment_count=node.get("comment_count", 0),
                    timestamp=node.get("taken_at"),
                    display_urls=display_urls,
                    video_urls=video_urls,
                    view_count=node.get("view_count"),
                    location=self._get_location(node),
                    owner_username=username,
                )
                
                all_posts.append(post)
                new_posts_count += 1
                
                if max_posts and len(all_posts) >= max_posts:
                    return all_posts
            
            print(f"Fetched {new_posts_count} posts on page {page}")
            
            has_next_page = page_info.get("has_next_page", False)
            end_cursor = page_info.get("end_cursor")
            
            print(f"  has_next_page: {has_next_page}, cursor: {end_cursor[:20] if end_cursor else 'None'}...")
            
            if not has_next_page:
                break
            
            if has_next_page and end_cursor:
                time.sleep(2)
            else:
                print("  Warning: has_next_page=True but no cursor provided")
                break
            
            page += 1
            
            if page > 100:
                break
        
        return all_posts
    
    def _fetch_posts_page(self, variables: dict) -> Optional[dict]:
        """Fetch a single page of posts using GraphQL with doc_id"""
        
        url = "https://www.instagram.com/graphql/query"
        
        params = {
            "doc_id": self.doc_id,
            "variables": json.dumps(variables)
        }
        
        headers = self.base_headers.copy()
        headers["Referer"] = f"https://www.instagram.com/{variables['username']}/"
        
        proxy = self._get_next_proxy()
        
        try:
            resp = requests.get(
                url, 
                params=params,
                headers=headers, 
                proxies=proxy, 
                timeout=15
            )
            
            resp.raise_for_status()
            
            data = resp.json()
            
            if "errors" in data:
                print(f"Error: GraphQL errors - {data['errors']}")
                return None
            
            if "data" in data:
                xdt_data = data.get("data", {}).get("xdt_api__v1__feed__user_timeline_graphql_connection")
                if xdt_data:
                    return xdt_data
                
                user_data = data.get("data", {}).get("user")
                if user_data:
                    timeline_media = user_data.get("edge_owner_to_timeline_media")
                    if timeline_media:
                        return timeline_media
            
            print(f"Error: Unexpected response structure")
            return None
                
        except requests.exceptions.HTTPError as e:
            print(f"Error: HTTP {e.response.status_code}")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def _get_media_type(self, node: dict) -> str:
        """Determine media type from node data"""
        product_type = node.get("product_type", "")
        if product_type == "clips":
            return "REEL"
        
        media_type = node.get("media_type")
        if media_type == 2:
            return "VIDEO"
        elif media_type == 8:
            return "CAROUSEL"
        elif media_type == 1:
            return "IMAGE"
        
        if node.get("is_video"):
            return "VIDEO"
        elif node.get("carousel_media_count") or node.get("carousel_media"):
            return "CAROUSEL"
        
        return "IMAGE"
    
    def _get_caption(self, node: dict) -> Optional[str]:
        """Extract caption from node data"""
        caption = node.get("caption")
        if caption:
            if isinstance(caption, dict):
                return caption.get("text")
            return caption
        
        edges = node.get("edge_media_to_caption", {}).get("edges", [])
        if edges and len(edges) > 0:
            return edges[0].get("node", {}).get("text")
        
        return None
    
    def _get_display_url(self, node: dict) -> Optional[str]:
        """Extract display URL from node data"""
        img_versions = node.get("image_versions2", {}).get("candidates", [])
        if img_versions:
            return img_versions[0].get("url")
        
        return node.get("display_url")
    
    def _get_video_url(self, node: dict) -> Optional[str]:
        """Extract video URL from node data"""
        video_versions = node.get("video_versions", [])
        if video_versions:
            return video_versions[0].get("url")
        
        return node.get("video_url")
    
    def _get_location(self, node: dict) -> Optional[dict]:
        """Extract location from node data"""
        location = node.get("location")
        if location:
            return {
                "id": location.get("id"),
                "name": location.get("name"),
                "slug": location.get("slug")
            }
        return None
    
    def save_profile_and_posts(self, profile: InstagramProfile, posts: List[InstagramPost], username: str):
        """Save profile and posts in one JSON file"""
        data = {
            "profile": profile.model_dump() if profile else None,
            "posts": [post.model_dump() for post in posts]
        }
        
        with open(f"{username}_data.json", 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)