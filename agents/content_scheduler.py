"""Content Scheduler - 14-day SEO-optimized content calendar + auto-publish.
Generates 2-3 posts per day with informational, long-tail keywords.
"""
import os
import sys
import re
import json
import glob
import random
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__))))

from google import genai
from config import GEMINI_API_KEY, AMAZON_TAG, BLOG_BASE_URL
from safety import tracker

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-2.5-flash"
FALLBACK = "gemini-2.5-pro"
DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _call_gemini(prompt):
    for m in [MODEL, FALLBACK]:
        try:
            resp = client.models.generate_content(model=m, contents=prompt)
            tracker.log_api_call("gemini_flash")
            return resp.text
        except Exception as e:
            print(f"[Scheduler] {m} failed: {e}")
    return ""


def generate_content_calendar():
    """Generate a 14-day content calendar with SEO-optimized titles."""
    prompt = (
        "You are an elite SEO strategist and fashion editor for TrendLoop USA.\n\n"
        "Create a 14-day content calendar with exactly 3 posts per day (42 posts total).\n\n"
        "CRITICAL SEO RULES:\n"
        "- Every title MUST contain informational keywords real people search for\n"
        "- Use patterns: 'How to Style X in 2026', 'X vs Y: Which Is Better?', "
        "'The Complete Guide to X', 'X Outfit Ideas for Y', 'Best X Under $100', "
        "'What to Wear to X in 2026'\n"
        "- Target long-tail keywords (4-7 words)\n"
        "- Each post targets a DIFFERENT keyword cluster\n"
        "- Include estimated monthly search volume\n\n"
        "TOPIC MIX per day:\n"
        "- Slot 1: Evergreen guide (How to style, What to wear, Complete guide)\n"
        "- Slot 2: Trend piece (2026 trends, Spring/Summer forecast, runway)\n"
        "- Slot 3: Shopping/product piece (Best X, Under $X, Amazon finds)\n\n"
        "Cover these categories across 14 days: workwear, casual, date night, "
        "seasonal, body type, budget, occasion, luxury, streetwear, minimalist, "
        "capsule wardrobe, accessories, denim, athleisure.\n\n"
        "Return ONLY a JSON array of 42 objects:\n"
        '[{"day":1,"slot":1,"title":"...","target_keyword":"...","search_volume":"...","intent":"informational","category":"guide"}]\n'
    )

    text = _call_gemini(prompt)
    jm = re.search(r"\[[\s\S]+\]", text)
    if jm:
        try:
            calendar = json.loads(jm.group())
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(os.path.join(DATA_DIR, "content_calendar.json"), "w", encoding="utf-8") as f:
                json.dump(calendar, f, ensure_ascii=False, indent=2)
            print(f"[Scheduler] Calendar generated: {len(calendar)} posts")
            return calendar
        except json.JSONDecodeError as e:
            print(f"[Scheduler] JSON parse error: {e}")
    return []


def get_todays_posts():
    """Get posts scheduled for today from the calendar."""
    cal_path = os.path.join(DATA_DIR, "content_calendar.json")
    if not os.path.exists(cal_path):
        print("[Scheduler] No calendar found. Generating...")
        calendar = generate_content_calendar()
    else:
        with open(cal_path, "r", encoding="utf-8") as f:
            calendar = json.load(f)

    if not calendar:
        return []

    # Find which day we're on
    cal_meta_path = os.path.join(DATA_DIR, "calendar_meta.json")
    if os.path.exists(cal_meta_path):
        with open(cal_meta_path, "r") as f:
            meta = json.load(f)
        current_day = meta.get("current_day", 1)
    else:
        current_day = 1

    todays = [p for p in calendar if p.get("day") == current_day]

    # Advance day counter
    next_day = current_day + 1 if current_day < 14 else 1
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(cal_meta_path, "w") as f:
        json.dump({"current_day": next_day, "last_run": datetime.now(timezone.utc).isoformat()}, f)

    print(f"[Scheduler] Day {current_day}: {len(todays)} posts to generate")
    return todays


def generate_seo_post(post_info):
    """Generate a single SEO-optimized blog post."""
    title = post_info.get("title", "Fashion Trends 2026")
    keyword = post_info.get("target_keyword", "fashion trends 2026")
    category = post_info.get("category", "guide")
    intent = post_info.get("intent", "informational")

    prompt = (
        f"You are a senior fashion editor at TrendLoop USA.\n\n"
        f"Write a premium SEO-optimized article.\n"
        f"Title: {title}\n"
        f"Target keyword: {keyword}\n"
        f"Content type: {category} ({intent} intent)\n"
        f"Amazon tag: {AMAZON_TAG}\n\n"
        f"Requirements:\n"
        f"1. 1200-1800 words, engaging editorial voice\n"
        f"2. Use the target keyword naturally 4-6 times (including H1 and first paragraph)\n"
        f"3. Include 5-8 Amazon product links:\n"
        f'   <a href="https://www.amazon.com/s?k=KEYWORD&tag={AMAZON_TAG}" target="_blank" rel="nofollow sponsored">Product</a>\n'
        f"4. Use H2 subheadings with related keywords\n"
        f"5. Include a FAQ section (3 questions) at the bottom for featured snippets\n"
        f"6. Add internal links to other TrendLoop USA articles where natural\n"
        f"7. Practical, actionable advice - not just listing trends\n"
        f"8. End with a clear CTA\n\n"
        f"Output pure HTML only. No markdown. No code fences."
    )

    text = _call_gemini(prompt)
    if not text:
        return None

    # Clean code fences
    text = re.sub(r"^```html?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    # Generate slug
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug_base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
    slug = f"{today}-{slug_base}"

    # Wrap in full HTML
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | TrendLoop USA</title>
<meta name="description" content="{title} - Expert fashion advice and curated product picks for 2026.">
<meta name="keywords" content="{keyword}, fashion 2026, style guide, outfit ideas">
<meta property="og:title" content="{title}">
<meta property="og:description" content="Expert fashion advice and curated product picks.">
<meta property="og:type" content="article">
<meta property="og:url" content="{BLOG_BASE_URL}/{slug}.html">
<meta name="twitter:card" content="summary_large_image">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8049649445649586" crossorigin="anonymous"></script>
<link rel="canonical href="{BLOG_BASE_URL}/{slug}.html">
<style>
body {{ font-family: Georgia, serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.8; color: #1a1a1a; background: #fafaf8; }}
h1 {{ font-size: 2em; line-height: 1.25; }}
h2 {{ font-size: 1.4em; margin-top: 2em; border-bottom: 1px solid #ddd; padding-bottom: 0.3em; }}
a {{ color: #8B4513; }}
.faq {{ background: #f5f0eb; padding: 20px; margin: 2em 0; border-radius: 8px; }}
.faq h3 {{ margin-top: 1em; }}
.affiliate-disclosure {{ font-size: 0.85em; color: #888; margin-top: 3em; padding-top: 1em; border-top: 1px solid #eee; }}
</style>
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{title}",
  "author": {{"@type": "Organization", "name": "TrendLoop USA"}},
  "publisher": {{"@type": "Organization", "name": "TrendLoop USA", "url": "{BLOG_BASE_URL}"}},
  "datePublished": "{today}",
  "mainEntityOfPage": "{BLOG_BASE_URL}/{slug}.html"
}}
</script>
</head>
<body>
<article>
<h1>{title}</h1>
{text}
</article>
<p class="affiliate-disclosure"><em>This article contains affiliate links. TrendLoop USA may earn a commission at no extra cost to you.</em></p>
<footer style="margin-top:2em;padding-top:1em;border-top:1px solid #ddd;font-size:0.9em;color:#666;">
<p>&copy; 2026 <a href="{BLOG_BASE_URL}">TrendLoop USA</a></p>
</footer>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    file_path = os.path.join(DOCS_DIR, f"{slug}.html")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"[Scheduler] Published: {title}")
    print(f"[Scheduler] URL: {BLOG_BASE_URL}/{slug}.html")
    print(f"[Scheduler] Length: {len(text)} chars | KW: {keyword}")

    return {"title": title, "slug": slug, "file_path": file_path, "keyword": keyword}


def run_daily_schedule():
    """Run daily scheduled post generation (2-3 posts)."""
    print("=" * 60)
    print("  TrendLoop USA - Daily Content Schedule")
    print("=" * 60)

    posts = get_todays_posts()
    if not posts:
        print("[Scheduler] No posts scheduled. Generating fallback post.")
        posts = [{"title": "Fashion Trends You Need to Know in 2026", "target_keyword": "fashion trends 2026", "category": "trend", "intent": "informational"}]

    results = []
    for i, post_info in enumerate(posts, 1):
        print(f"\n--- Post {i}/{len(posts)} ---")
        result = generate_seo_post(post_info)
        if result:
            results.append(result)

    # Rebuild site infrastructure
    if results:
        print("\n--- Rebuilding site ---")
        from agents.index_builder import rebuild_index
        from agents.rss_builder import rebuild_rss
        from agents.marketer import update_sitemap

        existing = glob.glob(os.path.join(DOCS_DIR, "*.html"))
        all_slugs = [os.path.splitext(os.path.basename(f))[0] for f in existing if os.path.basename(f) != "index.html"]
        update_sitemap(all_slugs)
        rebuild_index()
        rebuild_rss()

    print(f"\n[Scheduler] Done: {len(results)}/{len(posts)} posts published")
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--calendar":
        generate_content_calendar()
    else:
        run_daily_schedule()
