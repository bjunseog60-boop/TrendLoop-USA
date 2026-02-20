"""
  에이전트 C - 마케터 (Marketer)
  역할: 완성된 블로그 글을 트위터에 게시하고 구글 검색 색인을 요청합니다.

  작동 방식:
    1. 블로그 글 요약 + 링크를 트위터에 게시
    2. Google Indexing API로 새 글 URL을 색인 요청
  """

  import requests
  import tweepy
  from config import (
      X_API_KEY,
      X_API_SECRET,
      X_ACCESS_TOKEN,
      X_ACCESS_TOKEN_SECRET,
      BLOG_BASE_URL,
  )


  def post_to_twitter(summary: str, slug: str) -> bool:
      """
      트위터에 블로그 글 홍보 트윗을 게시합니다.

      매개변수:
          summary: 트윗 본문 (요약)
          slug: 블로그 글 URL 슬러그

      반환값:
          성공 여부 (True/False)
      """
      if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET]):
          print("[마케터] 경고: X API 인증 정보가 불완전합니다. 트윗 게시를 건너뜁니다.")
          return False

      # ── 블로그 URL 만들기 ──
      blog_url = f"{BLOG_BASE_URL}/{slug}.html"

      # ── 트윗 텍스트 구성 ──
      tweet_text = f"{summary}\n\nRead more: {blog_url}"

      # 280자 제한 확인
      if len(tweet_text) > 280:
          max_summary_len = 280 - len(f"\n\nRead more: {blog_url}") - 3
          tweet_text = f"{summary[:max_summary_len]}...\n\nRead more: {blog_url}"

      # ── 트위터 API v2 클라이언트 (쓰기용) ──
      client = tweepy.Client(
          consumer_key=X_API_KEY,
          consumer_secret=X_API_SECRET,
          access_token=X_ACCESS_TOKEN,
          access_token_secret=X_ACCESS_TOKEN_SECRET,
      )

      try:
          response = client.create_tweet(text=tweet_text)
          tweet_id = response.data["id"]
          print(f"[마케터] 트윗 게시 성공!")
          print(f"  - 트윗 ID: {tweet_id}")
          print(f"  - URL: https://x.com/i/status/{tweet_id}")
          return True
      except tweepy.TweepyException as e:
          print(f"[마케터] 트윗 게시 실패: {e}")
          return False


  def ping_google_indexing(slug: str) -> bool:
      """
      구글에 새 페이지 URL을 알려줍니다 (색인 요청).

      방법 1: Google 'ping' 방식 (Sitemap ping - 간단)
      방법 2: IndexNow API (Bing/Yandex/기타 검색엔진도 지원)

      매개변수:
          slug: 블로그 글 URL 슬러그

      반환값:
          성공 여부 (True/False)
      """
      page_url = f"{BLOG_BASE_URL}/{slug}.html"
      sitemap_url = f"{BLOG_BASE_URL}/sitemap.xml"
      success = False

      # ── 방법 1: Google Sitemap Ping ──
      try:
          google_ping = f"https://www.google.com/ping?sitemap={sitemap_url}"
          resp = requests.get(google_ping, timeout=15)
          if resp.status_code == 200:
              print(f"[마케터] Google sitemap ping 성공!")
              success = True
          else:
              print(f"[마케터] Google ping 응답 코드: {resp.status_code}")
      except requests.RequestException as e:
          print(f"[마케터] Google ping 실패: {e}")

      # ── 방법 2: IndexNow (Bing, Yandex 등) ──
      try:
          indexnow_payload = {
              "host": BLOG_BASE_URL.replace("https://", "").replace("http://", ""),
              "urlList": [page_url],
          }
          resp = requests.post(
              "https://api.indexnow.org/indexnow",
              json=indexnow_payload,
              timeout=15,
          )
          if resp.status_code in (200, 202):
              print(f"[마케터] IndexNow 색인 요청 성공!")
              success = True
          else:
              print(f"[마케터] IndexNow 응답 코드: {resp.status_code}")
      except requests.RequestException as e:
          print(f"[마케터] IndexNow 요청 실패: {e}")

      if success:
          print(f"  - 색인 요청 URL: {page_url}")
      else:
          print(f"[마케터] 색인 요청이 모두 실패했지만, 글은 정상적으로 발행되었습니다.")

      return success


  def update_sitemap(all_slugs: list[str]) -> None:
      """
      docs/sitemap.xml 파일을 업데이트합니다.
      GitHub Pages에서 검색엔진이 이 파일을 참고합니다.
      """
      import os
      from datetime import datetime, timezone

      today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
      output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")

      urls_xml = ""
      for slug in all_slugs:
          urls_xml += f"""  <url>
      <loc>{BLOG_BASE_URL}/{slug}.html</loc>
      <lastmod>{today}</lastmod>
      <changefreq>daily</changefreq>
    </url>
  """

      sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
  <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  {urls_xml}</urlset>"""

      sitemap_path = os.path.join(output_dir, "sitemap.xml")
      with open(sitemap_path, "w", encoding="utf-8") as f:
          f.write(sitemap)

      print(f"[마케터] sitemap.xml 업데이트 완료 ({len(all_slugs)}개 URL)")
