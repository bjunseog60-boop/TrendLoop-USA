#!/usr/bin/env python3
"""Batch Publisher - Generate a week of posts at once, publish daily.

Batch mode: Generate 70 posts (10/day x 7 days) in one batch via Gemini.
Scheduler mode: Auto-publish from the queue at scheduled times.

Uses Gemini Batch API for cost savings (~50% cheaper than real-time).
Falls back to sequential generation if batch API unavailable.

Usage:
  python3 batch_publisher.py --generate     # Generate 70 posts, save to queue
  python3 batch_publisher.py --publish      # Publish today's posts from queue
  python3 batch_publisher.py --status       # Check queue status
"""
import os
import sys
import io
import re
import json
import glob
import time
from datetime import datetime, timezone, timedelta

if hasattr(sys.stdout, "buffer"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS",
    os.path.join(os.path.dirname(__file__), "google_creds.json"),
)

from config import GEMINI_API_KEY, AMAZON_TAG, BLOG_BASE_URL
from safety import tracker
from google import genai

client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-2.5-flash"

PROJECT_ID = "fashion-money-maker"
LOCATION = "us-central1"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "docs")
DATA_DIR = os.path.join(BASE_DIR, "data")
QUEUE_DIR = os.path.join(DATA_DIR, "post_queue")
QUEUE_INDEX = os.path.join(DATA_DIR, "queue_index.json")

POSTS_PER_DAY = 10
DAYS_AHEAD = 7
TOTAL_POSTS = POSTS_PER_DAY * DAYS_AHEAD


def log(msg, level="INFO"):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        log_path = os.path.join(BASE_DIR, "logs", "batch_publisher.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def generate_weekly_topics():
    """Generate 70 unique topic ideas for the week."""
    log(f"Generating {TOTAL_POSTS} topic ideas...")

    prompt = (
        f"You are an elite SEO strategist for TrendLoop USA fashion blog.\n\n"
        f"Generate exactly {TOTAL_POSTS} unique blog post ideas.\n"
        f"Each post targets a DIFFERENT long-tail keyword (4-7 words).\n\n"
        f"TOPIC MIX:\n"
        f"- 20 evergreen guides (How to, What to wear, Complete guide)\n"
        f"- 15 trend pieces (2026 trends, seasonal, runway inspired)\n"
        f"- 15 shopping guides (Best X, Under $X, Amazon finds)\n"
        f"- 10 body-type/inclusive (plus size, petite, curvy, tall)\n"
        f"- 10 occasion-specific (wedding, work, vacation, date)\n\n"
        f"Categories: workwear, casual, date-night, seasonal, body-type, "
        f"budget, occasion, luxury, streetwear, minimalist, athleisure, denim\n\n"
        f"Return ONLY a JSON array of {TOTAL_POSTS} objects:\n"
        f'[{{"title":"...","keyword":"...","category":"...","day":1}}]\n'
        f"Assign day 1-7 evenly ({POSTS_PER_DAY} per day)."
    )

    try:
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        tracker.log_api_call("gemini_flash")
        text = resp.text
        jm = re.search(r"\[[\s\S]+\]", text)
        if jm:
            topics = json.loads(jm.group())
            log(f"Generated {len(topics)} topics")
            return topics
    except Exception as e:
        log(f"Topic generation error: {e}", "ERROR")

    return []


def generate_single_post(topic, index):
    """Generate a single post's HTML content."""
    title = topic.get("title", f"Fashion Trends 2026 #{index}")
    keyword = topic.get("keyword", "fashion trends 2026")
    category = topic.get("category", "casual")

    prompt = (
        f"You are a senior fashion editor at TrendLoop USA.\n\n"
        f"Write a premium SEO-optimized article.\n"
        f"Title: {title}\n"
        f"Target keyword: {keyword}\n"
        f"Amazon tag: {AMAZON_TAG}\n\n"
        f"Requirements:\n"
        f"1. 1200-1800 words, engaging editorial voice for US women 20-40\n"
        f"2. Use target keyword 4-6 times naturally including H1 and first paragraph\n"
        f"3. Include 5-8 Amazon product links:\n"
        f'   <a href="https://www.amazon.com/s?k=KEYWORD&tag={AMAZON_TAG}" '
        f'target="_blank" rel="nofollow sponsored">Product</a>\n'
        f"4. Use H2 subheadings with related keywords\n"
        f"5. Include FAQ section (3 questions) for featured snippets\n"
        f"6. Practical, actionable advice - not generic filler\n"
        f"7. Do NOT use em dashes. Use regular hyphens.\n"
        f"8. End with a clear CTA\n\n"
        f"Output pure HTML only. No markdown. No code fences."
    )

    try:
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        tracker.log_api_call("gemini_flash")
        text = resp.text.strip()
        text = re.sub(r"^```html?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return text
    except Exception as e:
        log(f"Post #{index} generation error: {e}", "ERROR")
        return None


def wrap_full_html(title, keyword, slug, body, pub_date):
    """Wrap article body in full HTML template with AdSense + Schema.org."""
    return f"""<!DOCTYPE html>
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
<link rel="canonical" href="{BLOG_BASE_URL}/{slug}.html">
<style>
body {{ font-family: Georgia, serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.8; color: #1a1a1a; background: #fafaf8; }}
h1 {{ font-size: 2em; line-height: 1.25; }}
h2 {{ font-size: 1.4em; margin-top: 2em; border-bottom: 1px solid #ddd; padding-bottom: 0.3em; }}
a {{ color: #8B4513; }}
.faq {{ background: #f5f0eb; padding: 20px; margin: 2em 0; border-radius: 8px; }}
.faq h3 {{ margin-top: 1em; }}
.affiliate-disclosure {{ font-size: 0.85em; color: #888; margin-top: 3em; padding-top: 1em; border-top: 1px solid #eee; }}
</style>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8049649445649586" crossorigin="anonymous"></script>
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{title}",
  "author": {{"@type": "Organization", "name": "TrendLoop USA"}},
  "publisher": {{"@type": "Organization", "name": "TrendLoop USA", "url": "{BLOG_BASE_URL}"}},
  "datePublished": "{pub_date}",
  "mainEntityOfPage": "{BLOG_BASE_URL}/{slug}.html"
}}
</script>
</head>
<body>
<article>
<h1>{title}</h1>
{body}
</article>
<p class="affiliate-disclosure"><em>This article contains affiliate links. TrendLoop USA may earn a commission at no extra cost to you.</em></p>
<footer style="margin-top:2em;padding-top:1em;border-top:1px solid #ddd;font-size:0.9em;color:#666;">
<p>&copy; 2026 <a href="{BLOG_BASE_URL}">TrendLoop USA</a></p>
</footer>
</body>
</html>"""


def batch_generate(count=TOTAL_POSTS):
    """Generate a batch of posts and save to queue."""
    log("=" * 60)
    log(f"  Batch Generation: {count} Posts")
    log("=" * 60)

    # Generate topics
    topics = generate_weekly_topics()
    if not topics:
        log("Failed to generate topics", "ERROR")
        return 0

    topics = topics[:count]

    # Create queue directory
    os.makedirs(QUEUE_DIR, exist_ok=True)

    queue_index = []
    generated = 0
    today = datetime.now(timezone.utc)

    for i, topic in enumerate(topics):
        day_offset = topic.get("day", (i // POSTS_PER_DAY) + 1) - 1
        pub_date = (today + timedelta(days=day_offset)).strftime("%Y-%m-%d")

        title = topic.get("title", f"Fashion Guide #{i+1}")
        keyword = topic.get("keyword", "fashion trends 2026")
        category = topic.get("category", "casual")
        slug_base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
        slug = f"{pub_date}-{slug_base}"

        log(f"[{i+1}/{len(topics)}] Generating: {title[:50]}...")

        body = generate_single_post(topic, i+1)
        if not body or len(body) < 500:
            log(f"  Skipped (too short or failed)", "WARN")
            continue

        full_html = wrap_full_html(title, keyword, slug, body, pub_date)

        # Save to queue
        post_file = os.path.join(QUEUE_DIR, f"{slug}.html")
        with open(post_file, "w", encoding="utf-8") as f:
            f.write(full_html)

        queue_entry = {
            "slug": slug,
            "title": title,
            "keyword": keyword,
            "category": category,
            "pub_date": pub_date,
            "file": post_file,
            "chars": len(full_html),
            "published": False,
        }
        queue_index.append(queue_entry)
        generated += 1

        log(f"  OK: {len(full_html)} chars -> {slug}")

        # Small delay to avoid rate limiting
        if (i + 1) % 5 == 0:
            log(f"  Progress: {generated}/{len(topics)}")
            time.sleep(2)

    # Save queue index
    with open(QUEUE_INDEX, "w", encoding="utf-8") as f:
        json.dump(queue_index, f, ensure_ascii=False, indent=2)

    log(f"\nBatch generation complete: {generated}/{len(topics)} posts")
    log(f"Queue saved: {QUEUE_INDEX}")

    # Summary by day
    from collections import Counter
    day_counts = Counter(e["pub_date"] for e in queue_index)
    for day, cnt in sorted(day_counts.items()):
        log(f"  {day}: {cnt} posts")

    return generated


def publish_todays_posts():
    """Publish posts scheduled for today from the queue."""
    log("=" * 60)
    log("  Publishing Today's Posts from Queue")
    log("=" * 60)

    if not os.path.exists(QUEUE_INDEX):
        log("No queue found. Run --generate first.", "WARN")
        return 0

    with open(QUEUE_INDEX, "r") as f:
        queue = json.load(f)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    todays_posts = [p for p in queue if p["pub_date"] == today and not p["published"]]

    if not todays_posts:
        log(f"No posts scheduled for {today}")
        return 0

    log(f"Found {len(todays_posts)} posts for {today}")
    published = 0

    for post in todays_posts:
        src = post["file"]
        if not os.path.exists(src):
            log(f"  Missing: {src}", "WARN")
            continue

        # Copy to docs/
        dst = os.path.join(DOCS_DIR, f"{post['slug']}.html")
        os.makedirs(DOCS_DIR, exist_ok=True)

        with open(src, "r", encoding="utf-8") as f:
            content = f.read()
        with open(dst, "w", encoding="utf-8") as f:
            f.write(content)

        post["published"] = True
        published += 1
        log(f"  Published: {post['title'][:50]}")

        # Submit to Google Indexing API
        try:
            from agents.indexing_agent import notify_url_updated
            notify_url_updated(post["slug"])
        except Exception:
            pass

    # Update queue index
    with open(QUEUE_INDEX, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

    # Rebuild site infrastructure
    if published > 0:
        try:
            from agents.marketer import update_sitemap
            from agents.index_builder import rebuild_index
            from agents.rss_builder import rebuild_rss

            existing = glob.glob(os.path.join(DOCS_DIR, "*.html"))
            all_slugs = [
                os.path.splitext(os.path.basename(f))[0]
                for f in existing if os.path.basename(f) != "index.html"
            ]
            update_sitemap(all_slugs)
            rebuild_index()
            rebuild_rss()
            log(f"Site rebuilt: {len(all_slugs)} total URLs")
        except Exception as e:
            log(f"Site rebuild error: {e}", "WARN")

    log(f"\nPublished: {published}/{len(todays_posts)} posts for {today}")
    return published


def show_queue_status():
    """Show current queue status."""
    print("=" * 60)
    print("  Post Queue Status")
    print("=" * 60)

    if not os.path.exists(QUEUE_INDEX):
        print("No queue found. Run --generate first.")
        return

    with open(QUEUE_INDEX, "r") as f:
        queue = json.load(f)

    total = len(queue)
    published = sum(1 for p in queue if p["published"])
    pending = total - published

    print(f"\nTotal: {total} | Published: {published} | Pending: {pending}")

    # Group by date
    from collections import defaultdict
    by_date = defaultdict(lambda: {"total": 0, "published": 0})
    for p in queue:
        d = p["pub_date"]
        by_date[d]["total"] += 1
        if p["published"]:
            by_date[d]["published"] += 1

    print(f"\n{'Date':<15} {'Total':>6} {'Published':>10} {'Pending':>8}")
    print("-" * 45)
    for date in sorted(by_date.keys()):
        info = by_date[date]
        pend = info["total"] - info["published"]
        status = "DONE" if pend == 0 else ""
        print(f"{date:<15} {info['total']:>6} {info['published']:>10} {pend:>8}  {status}")

    # Estimated cost
    avg_chars = sum(p.get("chars", 5000) for p in queue) / max(total, 1)
    est_tokens = (avg_chars / 4) * total
    est_cost = (est_tokens / 1_000_000) * 0.15  # Gemini Flash pricing
    print(f"\nEstimated API cost: ~${est_cost:.2f}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 batch_publisher.py --generate   # Generate 70 posts")
        print("  python3 batch_publisher.py --publish    # Publish today's posts")
        print("  python3 batch_publisher.py --status     # Queue status")
        sys.exit(0)

    action = sys.argv[1]

    if action == "--generate":
        batch_generate()
    elif action == "--publish":
        publish_todays_posts()
    elif action == "--status":
        show_queue_status()
    else:
        print(f"Unknown action: {action}")
