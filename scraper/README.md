# Instagram Scraper

A Python tool to scrape Instagram profile data and posts using GraphQL.

## Setup

# # # #INITIAL NOTES
 - Scraper Using API and Graph QL
 - API Limit - Banned first before Graph QL

### 1. Create Virtual Environment
```bash
python -m venv venv
```

### 2. Activate Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r scraper/requirements.txt
```

## Usage

### Basic Example
```python
from scraper.instagram_scraper import InstagramScraper

# Initialize scraper
scraper = InstagramScraper()

# Fetch profile
username = "instagram"
profile = scraper.get_profile(username)
print(f"Followers: {profile.follower_count}")

# Fetch posts
posts = scraper.get_posts(username, max_posts=100)
print(f"Fetched {len(posts)} posts")

# Save to file
scraper.save_profile_and_posts(profile, posts, username)
```

### With Proxies (Optional)
```python
proxies = [
    {"http": "http://proxy1.com:8080", "https": "http://proxy1.com:8080"},
    {"http": "http://proxy2.com:8080", "https": "http://proxy2.com:8080"},
]

# Noting that Proxies Do not work

scraper = InstagramScraper(proxies=proxies)
```

## Output

Posts are saved to `{username}_data.json` with:
- Profile info (username, followers, bio, etc.)
- Posts array with:
  - post_id
  - media_type (IMAGE, VIDEO, CAROUSEL, REEL)
  - caption
  - like_count, comment_count
  - display_urls (list of image URLs)
  - video_urls (list of video URLs)
  - timestamp
  - location

## Notes

- Carousel posts have multiple URLs in `display_urls` and `video_urls`
- Single posts have one URL per list
- Rate limit: 2 second delay between pages
- Max 100 pages per scrape session
- Noting that Proxies Do not work
- attempted to extract from embedded HTML with no Luck and time constrainsts
- example JSON extractions added in repo

