from typing import Optional, List
from pydantic import BaseModel


class InstagramProfile(BaseModel):
    username: str
    full_name: Optional[str] = None
    biography: Optional[str] = None
    follower_count: int
    following_count: int
    posts_count: int
    profile_picture_url: Optional[str] = None
    is_verified: bool
    category: Optional[str] = None
    external_url: Optional[str] = None

class InstagramPost(BaseModel):
    post_id: str  # shortcode
    instagram_id: str  # numeric ID
    media_type: str  # IMAGE, VIDEO, CAROUSEL, REEL
    caption: Optional[str]
    like_count: int
    comment_count: int
    timestamp: Optional[int]
    display_urls: List[str] = []  # Changed to list
    video_urls: List[str] = []    # Changed to list
    view_count: Optional[int]
    location: Optional[dict]
    owner_username: str

class InstagramPagination(BaseModel):
    has_next_page: bool
    end_cursor: Optional[str] = None