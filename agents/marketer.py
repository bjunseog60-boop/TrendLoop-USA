"""
에이전트 C - 마케터 (Marketer)
역할: 트위터 게시 + 구글 색인 + 멀티 채널 배포
라이브러리: tweepy v4 (tweepy.Client.create_tweet), requests
공식 문서: https://docs.tweepy.org/en/stable/client.html#create-tweet
"""

import requests
import tweepy
from config import (
    X_API_KEY,
    X_API_SECRET,
    X_ACCESS_TOKEN,
    X_ACCESS_TOKEN_SECRET,
    BLOG_BASE_URL,
    get_distribution_channels,
)
from safety import tracker


def post_to_twitter(summary: str, slug: str) -> bool:
    """tweepy.Client.create_tweet() - 트윗 게시"""
    if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET]):
        print("[마케터] 경고: X API 인증 정보가 불완전합니다. 트윗 게시를 건너뜁니다.")
        return False

    blog_url = f"{BLOG_BASE_URL}/{slug}.html"
    tweet_text = f"{summary}\n\nRead more: {blog_url}"

    if len(tweet_text) > 280:
        max_summary_len = 280 - len(f"\n\nRead more: {blog_url}") - 3
        tweet_text = f"{summary[:max_summary_len]}...\n\nRead more: {blog_url}"

    client = tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )

    try:
        response = client.create_tweet(text=tweet_text)
        tracker.log_api_call("twitter_write")
        tweet_id = response.data["id"]
        print(f"[마케터] 트윗 게시 성공!")
        print(f"  - 트윗 ID: {tweet_id}")
        print(f"  - URL: https://x.com/i/status/{tweet_id}")
        return True
    except tweepy.TweepyException as e:
        tracker.log_error("twitter")
        print(f"[마케터] 트윗 게시 실패: {e}")
        return False


def ping_google_indexing(slug: str) -> bool:
    """구글/Bing에 새 페이지 색인 요청"""
    page_url = f"{BLOG_BASE_URL}/{slug}.html"
    sitemap_url = f"{BLOG_BASE_URL}/sitemap.xml"
    success = False

    # Google Sitemap Ping
    try:
        resp = requests.get(f"https://www.google.com/ping?sitemap={sitemap_url}", timeout=15)
        tracker.log_api_call("google_index")
        if resp.status_code == 200:
            print("[마케터] Google sitemap ping 성공!")
            success = True
        else:
            print(f"[마케터] Google ping 응답 코드: {resp.status_code}")
    except requests.RequestException as e:
        tracker.log_error("other")
        print(f"[마케터] Google ping 실패: {e}")

    # IndexNow (Bing, Yandex)
    try:
        indexnow_payload = {
            "host": BLOG_BASE_URL.replace("https://", "").replace("http://", ""),
            "urlList": [page_url],
        }
        resp = requests.post("https://api.indexnow.org/indexnow", json=indexnow_payload, timeout=15)
        tracker.log_api_call("indexnow")
        if resp.status_code in (200, 202):
            print("[마케터] IndexNow 색인 요청 성공!")
            success = True
        else:
            print(f"[마케터] IndexNow 응답 코드: {resp.status_code}")
    except requests.RequestException as e:
        tracker.log_error("other")
        print(f"[마케터] IndexNow 요청 실패: {e}")

    if success:
        print(f"  - 색인 요청 URL: {page_url}")
    else:
        print("[마케터] 색인 요청이 모두 실패했지만, 글은 정상적으로 발행되었습니다.")

    return success


def distribute_to_channels(title: str, summary: str, slug: str) -> int:
    """
    멀티 채널 배포 엔진
    환경 변수 DISTRIBUTION_CHANNELS에 등록된 채널들로 콘텐츠를 배포합니다.

    채널 JSON 형식:
    [
        {"name": "site_a", "api_key": "...", "endpoint": "https://..."},
        {"name": "site_b", "api_key": "...", "endpoint": "https://..."}
    ]
    """
    channels = get_distribution_channels()
    if not channels:
        print("[마케터] 멀티 채널 배포 대상이 없습니다. (DISTRIBUTION_CHANNELS 미설정)")
        return 0

    blog_url = f"{BLOG_BASE_URL}/{slug}.html"
    success_count = 0

    for ch in channels:
        name = ch.get("name", "unknown")
        api_key = ch.get("api_key", "")
        endpoint = ch.get("endpoint", "")

        if not endpoint or not api_key:
            print(f"[마케터] 채널 '{name}' 설정 불완전. 건너뜁니다.")
            continue

        try:
            payload = {
                "title": title,
                "summary": summary,
                "url": blog_url,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=15)
            tracker.log_api_call("twitter_write")

            if resp.status_code in (200, 201, 202):
                print(f"[마케터] 채널 '{name}' 배포 성공!")
                success_count += 1
            else:
                print(f"[마케터] 채널 '{name}' 응답 코드: {resp.status_code}")
        except requests.RequestException as e:
            tracker.log_error("other")
            print(f"[마케터] 채널 '{name}' 배포 실패: {e}")

    print(f"[마케터] 멀티 채널 배포 결과: {success_count}/{len(channels)} 성공")
    return success_count


def update_sitemap(all_slugs: list[str]) -> None:
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


if __name__ == "__main__":
    test_slug = "2026-02-20-test-fashion-trends"
    post_to_twitter("Testing TrendLoop USA! #Fashion #Test", test_slug)
    ping_google_indexing(test_slug)
