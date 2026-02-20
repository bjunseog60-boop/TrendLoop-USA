"""Agent E - Reddit Auto-Poster for TrendLoop USA."""
import os
import re
import praw
from config import BLOG_BASE_URL
from safety import tracker

def _get_reddit():
    client_id = os.getenv("REDDIT_CLIENT_ID", "")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
    username = os.getenv("REDDIT_USERNAME", "")
    password = os.getenv("REDDIT_PASSWORD", "")
    if not all([client_id, client_secret, username, password]):
        print("[Reddit] Credentials not configured. Skipping.")
        return None
    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent="TrendLoopUSA/1.0 (by /u/" + username + ")",
        )
        return reddit
    except Exception as e:
        print(f"[Reddit] Auth error: {e}")
        return None

# Fashion subreddits that allow link posts
FASHION_SUBREDDITS = [
    "fashiontrends",
    "womensstreetwear",
    "fashion",
]

def post_to_reddit(blog: dict, keywords: list = None) -> bool:
    reddit = _get_reddit()
    if not reddit:
        return False

    title = blog.get("title", "Fashion Trend")
    slug = blog.get("slug", "")
    summary = blog.get("summary", "")
    blog_url = f"{BLOG_BASE_URL}/{slug}.html"

    posted = 0
    for sub_name in FASHION_SUBREDDITS:
        try:
            subreddit = reddit.subreddit(sub_name)
            # Post as link
            submission = subreddit.submit(
                title=title[:300],
                url=blog_url,
            )
            print(f"[Reddit] Posted to r/{sub_name}: {submission.shortlink}")
            tracker.log_api_call("reddit")
            posted += 1
        except Exception as e:
            err_msg = str(e)
            if "RATELIMIT" in err_msg.upper():
                print(f"[Reddit] Rate limited on r/{sub_name}. Skipping rest.")
                break
            print(f"[Reddit] r/{sub_name} failed: {err_msg[:150]}")
            tracker.log_error("other")

    print(f"[Reddit] Posted to {posted}/{len(FASHION_SUBREDDITS)} subreddits")
    return posted > 0

def post_self_to_reddit(blog: dict, keywords: list = None) -> bool:
    """Post as self/text post with excerpt + link (safer for some subreddits)."""
    reddit = _get_reddit()
    if not reddit:
        return False

    title = blog.get("title", "Fashion Trend")
    slug = blog.get("slug", "")
    summary = blog.get("summary", "")
    blog_url = f"{BLOG_BASE_URL}/{slug}.html"

    body = f"{summary}\n\n"
    if keywords:
        tags = [kw.get("keyword", "") if isinstance(kw, dict) else str(kw) for kw in keywords[:5]]
        body += "Keywords: " + ", ".join(tags) + "\n\n"
    body += f"Read more: {blog_url}"

    try:
        subreddit = reddit.subreddit("fashiontrends")
        submission = subreddit.submit(
            title=title[:300],
            selftext=body,
        )
        print(f"[Reddit] Self post: {submission.shortlink}")
        tracker.log_api_call("reddit")
        return True
    except Exception as e:
        print(f"[Reddit] Self post failed: {e}")
        tracker.log_error("other")
    return False

if __name__ == "__main__":
    print("=== Reddit Bot Test ===")
    reddit = _get_reddit()
    if reddit:
        print(f"[Reddit] Logged in as: {reddit.user.me()}")
    else:
        print("[Reddit] Not configured. Set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD in .env")
