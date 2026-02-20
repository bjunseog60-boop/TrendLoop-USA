"""Auto-update index.html with links to all published posts."""
import os
import re
import glob
from datetime import datetime, timezone


def rebuild_index():
    """Scan docs/ for post HTML files and rebuild index.html."""
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
    html_files = glob.glob(os.path.join(docs_dir, "*.html"))

    posts = []
    for filepath in html_files:
        basename = os.path.basename(filepath)
        if basename in ("index.html",):
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        title_match = re.search(r"<title>(.*?)\|", content)
        title = title_match.group(1).strip() if title_match else basename.replace(".html", "").replace("-", " ").title()

        desc_match = re.search(r'<meta name="description" content="(.*?)"', content)
        desc = desc_match.group(1).strip() if desc_match else ""

        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", basename)
        date_str = date_match.group(1) if date_match else ""

        posts.append({
            "filename": basename,
            "title": title,
            "description": desc,
            "date": date_str,
        })

    posts.sort(key=lambda x: x["date"], reverse=True)

    # Also include posts/ subdirectory
    sub_posts = []
    posts_dir = os.path.join(docs_dir, "posts")
    if os.path.exists(posts_dir):
        sub_files = glob.glob(os.path.join(posts_dir, "*.html"))
        for filepath in sub_files:
            basename = os.path.basename(filepath)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            title_match = re.search(r"<title>(.*?)\|", content)
            title = title_match.group(1).strip() if title_match else basename

            desc_match = re.search(r'<meta name="description" content="(.*?)"', content)
            desc = desc_match.group(1).strip() if desc_match else ""

            sub_posts.append({
                "filename": f"posts/{basename}",
                "title": title,
                "description": desc,
                "date": "",
            })

    all_posts = sub_posts + posts

    post_cards = ""
    for p in all_posts:
        post_cards += '<div class="post-card">\n'
        post_cards += f'            <a href="/{p["filename"]}">{p["title"]}</a>\n'
        post_cards += f'            <p class="excerpt">{p["description"]}</p>\n'
        meta_date = f" -- {p['date']}" if p["date"] else ""
        post_cards += f'            <p class="meta">By TrendLoop USA Team{meta_date}</p>\n'
        post_cards += '        </div>\n        '

    if not post_cards.strip():
        post_cards = '<div class="empty"><p>No posts yet. Stay tuned!</p></div>'

    today_year = datetime.now(timezone.utc).strftime("%Y")

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TrendLoop USA - Fashion Trends Blog</title>
    <meta name="description" content="Your daily source for curated US fashion trends, powered by AI intelligence.">
    <meta name="author" content="TrendLoop USA Team">
    <link rel="canonical" href="https://trendloopusa.net/">
    <link rel="alternate" type="application/rss+xml" title="TrendLoop USA" href="https://trendloopusa.net/feed.xml">
    <meta property="og:title" content="TrendLoop USA - Fashion Trends Blog">
    <meta property="og:description" content="Your daily source for curated US fashion trends, powered by AI intelligence.">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://trendloopusa.net/">
    <meta property="og:site_name" content="TrendLoop USA">
    <meta name="twitter:card" content="summary">
    <script type="application/ld+json">
    {{{{ "@context": "https://schema.org", "@type": "WebSite", "name": "TrendLoop USA", "url": "https://trendloopusa.net", "description": "Curated fashion intelligence, delivered daily" }}}}
    </script>
    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
    <script>window.dataLayer=window.dataLayer||[];function gtag(){{{{dataLayer.push(arguments)}}}}gtag('js',new Date());gtag('config','GA_MEASUREMENT_ID');</script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Georgia, 'Times New Roman', serif; line-height: 1.6; color: #2a2a2a; background: #fdfbf9; }}
        .site-header {{ text-align: center; padding: 48px 24px 32px; border-bottom: 1px solid #e8e4e0; background: #fff; }}
        .site-header h1 {{ font-size: 2.4em; letter-spacing: 4px; text-transform: uppercase; color: #1a1a1a; }}
        .site-header .tagline {{ color: #999; font-size: 1em; margin-top: 8px; font-style: italic; }}
        .container {{ max-width: 780px; margin: 0 auto; padding: 40px 24px 60px; }}
        .post-card {{ background: #fff; padding: 28px 32px; margin: 20px 0; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); transition: box-shadow 0.2s; }}
        .post-card:hover {{ box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
        .post-card a {{ color: #1a1a1a; text-decoration: none; font-size: 1.3em; font-weight: 700; line-height: 1.3; }}
        .post-card a:hover {{ color: #c9a96e; }}
        .post-card .excerpt {{ color: #666; margin-top: 10px; font-size: 0.95em; line-height: 1.6; }}
        .post-card .meta {{ color: #aaa; font-size: 0.82em; margin-top: 12px; }}
        .post-card .post-thumb {{ width: 100%; border-radius: 8px; margin-bottom: 16px; }}
        .empty {{ text-align: center; padding: 60px; color: #aaa; }}
        .site-footer {{ text-align: center; padding: 32px 24px; border-top: 1px solid #e8e4e0; background: #fff; font-size: 0.85em; color: #999; }}
        .site-footer a {{ color: #c9a96e; text-decoration: none; }}
    </style>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8049649445649586" crossorigin="anonymous"></script>
</head>
<body>
    <header class="site-header">
        <h1>TrendLoop USA</h1>
        <p class="tagline">Curated fashion intelligence, delivered daily</p>
    </header>
    <div class="container">
        {post_cards}
    </div>
    <footer class="site-footer">
        <p>&copy; {today_year} <strong>TrendLoop USA</strong>. All rights reserved.</p>
        <p>Contact: <a href="mailto:contact@trendloopusa.net">contact@trendloopusa.net</a></p>
        <p style="margin-top:8px;">Powered by AI-curated fashion intelligence.</p>
    </footer>
</body>
</html>"""

    index_path = os.path.join(docs_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)

    print(f"[IndexBuilder] index.html rebuilt with {len(all_posts)} post(s)")
    return len(all_posts)


if __name__ == "__main__":
    rebuild_index()
