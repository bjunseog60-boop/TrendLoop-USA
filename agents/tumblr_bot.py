"""Agent F - Tumblr Auto-Poster for TrendLoop USA."""
import os
import re
import pytumblr
from config import BLOG_BASE_URL
from safety import tracker

def _get_client():
    consumer_key = os.getenv("TUMBLR_CONSUMER_KEY", "")
    consumer_secret = os.getenv("TUMBLR_CONSUMER_SECRET", "")
    oauth_token = os.getenv("TUMBLR_OAUTH_TOKEN", "")
    oauth_secret = os.getenv("TUMBLR_OAUTH_SECRET", "")
    if not all([consumer_key, consumer_secret, oauth_token, oauth_secret]):
        print("[Tumblr] Credentials not configured. Skipping.")
        return None
    try:
        client = pytumblr.TumblrRestClient(
            consumer_key, consumer_secret,
            oauth_token, oauth_secret,
        )
        return client
    except Exception as e:
        print(f"[Tumblr] Auth error: {e}")
        return None

def post_to_tumblr(blog: dict, keywords: list = None) -> bool:
    client = _get_client()
    if not client:
        return False

    blog_name = os.getenv("TUMBLR_BLOG_NAME", "")
    if not blog_name:
        print("[Tumblr] TUMBLR_BLOG_NAME not set. Skipping.")
        return False

    title = blog.get("title", "Fashion Trend")
    slug = blog.get("slug", "")
    summary = blog.get("summary", "")
    html_body = blog.get("html", "")
    blog_url = f"{BLOG_BASE_URL}/{slug}.html"

    # Build tags
    tags = ["fashion", "trends", "USfashion", "TrendLoopUSA", "OOTD"]
    if keywords:
        for kw in keywords[:5]:
            tag = kw.get("keyword", "") if isinstance(kw, dict) else str(kw)
            tag = tag.strip().replace(" ", "")
            if tag and len(tag) > 2:
                tags.append(tag)

    # Build HTML body with excerpt + read more link
    body_html = f"<p>{summary}</p>" if summary else ""
    body_html += f'<p><a href="{blog_url}">Read the full article on TrendLoop USA &rarr;</a></p>'

    # Extract first image from blog HTML
    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html_body or "")
    if img_match:
        img_url = img_match.group(1)
        if img_url.startswith("/"):
            img_url = f"{BLOG_BASE_URL}{img_url}"
        body_html = f'<img src="{img_url}" alt="{title}"/>' + body_html

    try:
        result = client.create_text(
            blog_name,
            state="published",
            title=title,
            body=body_html,
            tags=tags[:10],
            format="html",
        )
        if isinstance(result, dict) and result.get("id"):
            post_id = result["id"]
            post_url = f"https://{blog_name}.tumblr.com/post/{post_id}"
            print(f"[Tumblr] Posted! {post_url}")
            tracker.log_api_call("tumblr")
            return True
        else:
            print(f"[Tumblr] Unexpected response: {str(result)[:200]}")
            tracker.log_error("other")
    except Exception as e:
        print(f"[Tumblr] Post failed: {e}")
        tracker.log_error("other")
    return False

if __name__ == "__main__":
    print("=== Tumblr Bot Test ===")
    client = _get_client()
    if client:
        info = client.info()
        print(f"[Tumblr] Logged in: {info}")
    else:
        print("[Tumblr] Not configured. Set TUMBLR_CONSUMER_KEY, TUMBLR_CONSUMER_SECRET, TUMBLR_OAUTH_TOKEN, TUMBLR_OAUTH_SECRET, TUMBLR_BLOG_NAME in .env")
