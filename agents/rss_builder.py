"""Auto-generate RSS feed (feed.xml) from published posts."""
import os
import re
import glob
from datetime import datetime, timezone

def rebuild_rss():
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
        date_str = date_match.group(1) if date_match else datetime.now(timezone.utc).strftime("%Y-%m-%d")

        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content)
        img_url = img_match.group(1) if img_match else ""
        if img_url.startswith("/"):
            img_url = f"https://trendloopusa.net{img_url}"

        posts.append({
            "filename": basename,
            "title": title,
            "description": desc,
            "date": date_str,
            "image": img_url,
        })

    posts.sort(key=lambda x: x["date"], reverse=True)

    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    items = ""
    for p in posts:
        pub_date = datetime.strptime(p["date"], "%Y-%m-%d").strftime("%a, %d %b %Y 00:00:00 +0000")
        link = f"https://trendloopusa.net/{p['filename']}"
        img_tag = ""
        if p["image"]:
            img_tag = f'<media:content url="{p["image"]}" medium="image" />'
        items += f"""    <item>
      <title><![CDATA[{p['title']}]]></title>
      <link>{link}</link>
      <guid>{link}</guid>
      <pubDate>{pub_date}</pubDate>
      <description><![CDATA[{p['description']}]]></description>
      {img_tag}
    </item>
"""

    feed_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>TrendLoop USA</title>
    <link>https://trendloopusa.net</link>
    <description>Curated fashion intelligence, delivered daily</description>
    <language>en-us</language>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="https://trendloopusa.net/feed.xml" rel="self" type="application/rss+xml" />
{items}  </channel>
</rss>"""

    feed_path = os.path.join(docs_dir, "feed.xml")
    with open(feed_path, "w", encoding="utf-8") as f:
        f.write(feed_xml)

    print(f"[RSS] feed.xml rebuilt with {len(posts)} post(s)")
    return len(posts)

if __name__ == "__main__":
    rebuild_rss()
