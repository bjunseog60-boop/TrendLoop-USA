"""
에이전트 B - 작가 (Writer)
역할: Gemini API를 사용해 트렌드 키워드 기반 블로그 글을 작성합니다.
     아마존 어소시에이트 링크가 자연스럽게 포함됩니다.

작동 방식:
  1. 분석가로부터 받은 키워드 리스트를 프롬프트에 넣기
  2. Gemini API로 SEO 최적화된 블로그 글 생성
  3. 아마존 검색 링크 (어소시에이트 태그 포함) 자동 삽입
  4. HTML 파일로 저장
"""

import os
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus
import google.generativeai as genai
from config import GEMINI_API_KEY, AMAZON_TAG


def _make_amazon_link(keyword: str) -> str:
    """키워드로 아마존 검색 링크를 만듭니다 (어소시에이트 태그 포함)"""
    encoded = quote_plus(keyword)
    return f"https://www.amazon.com/s?k={encoded}&tag={AMAZON_TAG}"


def generate_blog_post(keywords: list[dict]) -> dict:
    """
    키워드 리스트를 받아서 블로그 글을 생성합니다.

    매개변수:
        keywords: [{"keyword": "coquette", "count": 42}, ...]

    반환값:
        {
            "title": "글 제목",
            "slug": "url-friendly-slug",
            "html": "완성된 HTML 문자열",
            "summary": "트위터 게시용 요약 (280자 이내)",
            "file_path": "저장된 파일 경로",
        }
    """
    if not GEMINI_API_KEY:
        print("[작가] 오류: GEMINI_API_KEY가 설정되지 않았습니다.")
        return {}

    # ── 키워드 및 아마존 링크 준비 ──
    keyword_names = [kw["keyword"] for kw in keywords]
    amazon_links = {kw: _make_amazon_link(kw) for kw in keyword_names}

    links_text = "\n".join(
        f"- {kw}: {url}" for kw, url in amazon_links.items()
    )

    # ── Gemini API 설정 ──
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")

    # ── 블로그 글 생성 프롬프트 ──
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
        response = model.generate_content(prompt)
        article_html = response.text
    except Exception as e:
        print(f"[작가] Gemini API 오류: {e}")
        return {}

    # ── 제목 추출 ──
    title_match = re.search(r"<h1[^>]*>(.*?)</h1>", article_html, re.IGNORECASE)
    title = title_match.group(1) if title_match else f"Fashion Trends: {keyword_names[0].title()}"
    title = re.sub(r"<[^>]+>", "", title)  # HTML 태그 제거

    # ── URL 슬러그 생성 ──
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug_base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:50]
    slug = f"{today}-{slug_base}"

    # ── 트위터 요약 생성 ──
    summary_prompt = f"""Summarize this fashion blog post title in a compelling tweet (max 250 chars).
Include 2-3 relevant hashtags. Do NOT use markdown.

Title: {title}
Keywords: {', '.join(keyword_names)}

Tweet:"""

    try:
        summary_response = model.generate_content(summary_prompt)
        summary = summary_response.text.strip()[:250]
    except Exception:
        summary = f"New fashion trends alert! {', '.join(keyword_names[:3])} #Fashion #Trending"

    # ── 완성된 HTML 페이지 만들기 ──
    full_html = _wrap_in_html_page(title, article_html, today)

    # ── 파일 저장 ──
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{slug}.html")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"[작가] 블로그 글 생성 완료!")
    print(f"  - 제목: {title}")
    print(f"  - 파일: {file_path}")
    print(f"  - 요약: {summary}")

    return {
        "title": title,
        "slug": slug,
        "html": full_html,
        "summary": summary,
        "file_path": file_path,
    }


def _wrap_in_html_page(title: str, article_html: str, date: str) -> str:
    """글을 완성된 HTML 페이지로 감쌉니다"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | TrendLoop USA</title>
    <meta name="description" content="{title} - Discover the latest fashion trends in the USA.">
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
        &copy; {date[:4]} TrendLoop USA. All rights reserved.
    </footer>
</body>
</html>"""


# ── 테스트용 ──
if __name__ == "__main__":
    test_keywords = [
        {"keyword": "coquette fashion", "count": 10},
        {"keyword": "quiet luxury", "count": 8},
    ]
    result = generate_blog_post(test_keywords)
    if result:
        print("\n생성 성공:", result["title"])
