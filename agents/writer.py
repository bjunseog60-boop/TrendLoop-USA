"""
에이전트 B - 작가 (Writer)
역할: Gemini API로 블로그 글 생성 + 아마존 어소시에이트 링크 삽입
라이브러리: google-genai v1+ (google.genai.Client)
공식 문서: https://ai.google.dev/gemini-api/docs
"""

import os
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus
from google import genai  # google-genai 패키지 (신규)
from config import GEMINI_API_KEY, AMAZON_TAG, GEMINI_DAILY_CALL_LIMIT
from safety import tracker


_gemini_call_count = 0


def _check_gemini_limit() -> bool:
    global _gemini_call_count
    if _gemini_call_count >= GEMINI_DAILY_CALL_LIMIT:
        print(f"[작가] Gemini API 일일 한도 {GEMINI_DAILY_CALL_LIMIT}회 도달. 추가 호출 차단.")
        return False
    return True


def _call_gemini(client, prompt: str) -> str:
    """Gemini API 호출 + 사용량 기록"""
    global _gemini_call_count

    if not _check_gemini_limit():
        return ""

    _gemini_call_count += 1
    print(f"[작가] Gemini API 호출 {_gemini_call_count}/{GEMINI_DAILY_CALL_LIMIT}")

    # client.models.generate_content() - Gemini API v1 텍스트 생성
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    tracker.log_api_call("gemini")
    return response.text


def _make_amazon_link(keyword: str) -> str:
    encoded = quote_plus(keyword)
    return f"https://www.amazon.com/s?k={encoded}&tag={AMAZON_TAG}"


def generate_blog_post(keywords: list[dict]) -> dict:
    """키워드 → Gemini로 블로그 글 생성 → HTML 파일 저장"""
    if not GEMINI_API_KEY:
        print("[작가] 오류: GEMINI_API_KEY가 설정되지 않았습니다.")
        return {}

    keyword_names = [kw["keyword"] for kw in keywords]
    amazon_links = {kw: _make_amazon_link(kw) for kw in keyword_names}
    links_text = "\n".join(f"- {kw}: {url}" for kw, url in amazon_links.items())

    # genai.Client() - API 키 기반 인증
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""You are a professional fashion blogger writing for a US audience.

Write an engaging, SEO-optimized blog post about today's hottest fashion trends.

**Trending keywords to cover:** {', '.join(keyword_names)}

**Amazon affiliate links to include naturally in the article:**
{links_text}

**Requirements:**
1. Write a catchy title (H1)
2. Write 800-1200 words
3. Include each keyword at least twice for SEO
4. Naturally embed the Amazon links as product recommendations (use HTML <a> tags with target="_blank")
5. Add a "Shop the Look" section at the end with all Amazon links
6. Use a friendly, conversational tone
7. Include an intro paragraph and a conclusion
8. Use H2 subheadings for each trend
9. Output pure HTML content (no ```html``` markers, no <html>/<head>/<body> tags - just the article content)
10. Add a small disclaimer at the bottom: "This post contains affiliate links. We may earn a commission at no extra cost to you."

Write the blog post now:"""

    try:
        article_html = _call_gemini(client, prompt)
        if not article_html:
            return {}
    except Exception as e:
        print(f"[작가] Gemini API 오류: {e}")
        tracker.log_error("gemini")
        return {}

    # 제목 추출
    title_match = re.search(r"<h1[^>]*>(.*?)</h1>", article_html, re.IGNORECASE)
    title = title_match.group(1) if title_match else f"Fashion Trends: {keyword_names[0].title()}"
    title = re.sub(r"<[^>]+>", "", title)

    # URL 슬러그
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug_base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:50]
    slug = f"{today}-{slug_base}"

    # 트위터 요약
    summary_prompt = f"""Summarize this fashion blog post title in a compelling tweet (max 250 chars).
Include 2-3 relevant hashtags. Do NOT use markdown.

Title: {title}
Keywords: {', '.join(keyword_names)}

Tweet:"""

    try:
        summary = _call_gemini(client, summary_prompt)
        summary = summary.strip()[:250] if summary else ""
    except Exception:
        tracker.log_error("gemini")
        summary = ""

    if not summary:
        summary = f"New fashion trends alert! {', '.join(keyword_names[:3])} #Fashion #Trending"

    full_html = _wrap_in_html_page(title, article_html, today)

    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{slug}.html")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"[작가] 블로그 글 생성 완료!")
    print(f"  - 제목: {title}")
    print(f"  - 파일: {file_path}")
    print(f"  - 요약: {summary}")
    print(f"  - Gemini API 총 호출: {_gemini_call_count}회")

    return {
        "title": title,
        "slug": slug,
        "html": full_html,
        "summary": summary,
        "file_path": file_path,
    }


def _wrap_in_html_page(title: str, article_html: str, date: str) -> str:
    slug_for_url = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:50]
    canonical = f"https://trendloopusa.net/{date}-{slug_for_url}.html"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | TrendLoop USA</title>
    <meta name="description" content="{title} - Discover the latest fashion trends in the USA.">
    <meta name="author" content="TrendLoop USA Team">
    <link rel="canonical" href="{canonical}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{title} - Discover the latest fashion trends in the USA.">
    <meta property="og:type" content="article">
    <meta property="og:site_name" content="TrendLoop USA">
    <meta property="og:url" content="{canonical}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{title} - Discover the latest fashion trends.">
    <link rel="alternate" type="application/rss+xml" title="TrendLoop USA" href="https://trendloopusa.net/feed.xml">
    <script type="application/ld+json">
    {{{{
      "@context": "https://schema.org",
      "@type": "Article",
      "headline": "{title}",
      "author": {{{{ "@type": "Organization", "name": "TrendLoop USA Team" }}}},
      "publisher": {{{{ "@type": "Organization", "name": "TrendLoop USA", "url": "https://trendloopusa.net" }}}},
      "datePublished": "{date}",
      "dateModified": "{date}",
      "mainEntityOfPage": {{{{ "@type": "WebPage", "@id": "{canonical}" }}}}
    }}}}
    </script>
    <!-- Google AdSense -->
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8049649445649586" crossorigin="anonymous"></script>
    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
    <script>window.dataLayer=window.dataLayer||[];function gtag(){{{{dataLayer.push(arguments)}}}}gtag('js',new Date());gtag('config','GA_MEASUREMENT_ID');</script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            line-height: 1.8;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #fafafa;
        }}
        header {{
            text-align: center;
            padding: 30px 0;
            border-bottom: 2px solid #e0e0e0;
            margin-bottom: 30px;
        }}
        header .brand {{ font-size: 14px; color: #888; text-transform: uppercase; letter-spacing: 2px; }}
        header .date {{ font-size: 13px; color: #aaa; margin-top: 5px; }}
        article h1 {{ font-size: 2em; margin: 20px 0; color: #1a1a1a; }}
        article h2 {{ font-size: 1.4em; margin: 25px 0 10px; color: #2a2a2a; }}
        article p {{ margin: 12px 0; }}
        article a {{ color: #c0392b; text-decoration: none; font-weight: 500; }}
        article a:hover {{ text-decoration: underline; }}
        .disclaimer {{ margin-top: 40px; padding: 15px; background: #f0f0f0; border-radius: 8px; font-size: 13px; color: #777; }}
        footer {{ text-align: center; margin-top: 50px; padding: 20px 0; font-size: 12px; color: #aaa; }}
    </style>
</head>
<body>
    <header>
        <div class="brand">TrendLoop USA</div>
        <div class="date">{date}</div>
    </header>
    <article>
        {article_html}
    </article>
    <footer>
        <p>By <strong>TrendLoop USA Team</strong></p>
        <p>Contact: <a href="mailto:contact@trendloopusa.net">contact@trendloopusa.net</a></p>
        <p>&copy; {date[:4]} TrendLoop USA. All rights reserved.</p>
    </footer>
</body>
</html>"""


if __name__ == "__main__":
    test_keywords = [
        {"keyword": "coquette fashion", "count": 10},
        {"keyword": "quiet luxury", "count": 8},
    ]
    result = generate_blog_post(test_keywords)
    if result:
        print("\n생성 성공:", result["title"])
