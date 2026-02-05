from services.instagram_api import InstagramScraper
from services.instagram_html import InstagramScraper as InstagramScraperHTML
# from services.instagram_api import save_profile_and_posts
import json
# Uncomment to Test Real Proxies
proxies = []
# proxies = [
#     {
#         "http": "http://51.159.66.158:3128",
#         "https": "http://51.159.66.158:3128"
#     }
# ]


scraper = InstagramScraper(proxies=proxies)
scraperHtml = InstagramScraperHTML()
username = "lilbieber"
max_posts = 200
# Get profile - returns InstagramProfile model
profile = scraper.get_profile(username = username)
print(f"profile: {profile}")

get_posts = scraper.get_posts(username = username, max_posts = max_posts)
print(f"get_posts: {get_posts}")

scraper.save_profile_and_posts(profile, get_posts, username)

# profile2 = scraperHtml.get_profile(username)


############### testing HTML Embedding - Not Working
# if profile2:
#     print(f"\n{'='*60}")
#     print("PROFILE DATA:")
#     print(f"{'='*60}")
    
#     # Print formatted profile
#     profile_dict = profile2.to_dict()
#     print(json.dumps(profile_dict, indent=2, ensure_ascii=False))
    
#     # Save to file
#     output_file = f"{username}_profile.json"
#     with open(output_file, 'w', encoding='utf-8') as f:
#         json.dump(profile_dict, f, indent=2, ensure_ascii=False)
    
#     print(f"\n✅ Profile saved to: {output_file}")
# else:
#     print(f"\n❌ Failed to scrape profile for @{username}")


# # Get posts - returns List[InstagramPost] and InstagramPagination
# posts, pagination = scraper.get_posts("cristiano", count=12)
# for post in posts:
#     print(f"{post.media_type}: {post.like_count:,} likes")