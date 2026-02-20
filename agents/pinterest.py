"""
에이전트 D - Pinterest 마케터 (Pinterest Auto-Poster)
역할: Pinterest API v5로 패션 핀 자동 생성 + 벌크 포스팅
API 문서: https://developers.pinterest.com/docs/api/v5/
"""

import os
import re
import base64
import requests
from config import (
    PINTEREST_ACCESS_TOKEN,
    PINTEREST_BOARD_ID,
    PINTEREST_REFRESH_TOKEN,
    PINTEREST_APP_ID,
    PINTEREST_APP_SECRET,
    BLOG_BASE_URL,
)
from safety import tracker

PINTEREST_API = "https://api.pinterest.com/v5"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 토큰 관리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_current_token = None


def _get_token() -> str:
    global _current_token
    if _current_token:
        return _current_token
    _current_token = PINTEREST_ACCESS_TOKEN
    return _current_token


def refresh_access_token() -> str | None:
    """Refresh token으로 새 access token을 발급받습니다."""
    global _current_token
    if not all([PINTEREST_REFRESH_TOKEN, PINTEREST_APP_ID, PINTEREST_APP_SECRET]):
        print("[Pinterest] Refresh token 미설정. 토큰 갱신 불가.")
        return None

    try:
        resp = requests.post(
            "https://api.pinterest.com/v5/oauth/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": PINTEREST_REFRESH_TOKEN,
            },
            auth=(PINTEREST_APP_ID, PINTEREST_APP_SECRET),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            _current_token = data.get("access_token", "")
            print(f"[Pinterest] 토큰 갱신 성공! (만료: {data.get('expires_in', '?')}초)")
            tracker.log_api_call("pinterest")
            return _current_token
        else:
            print(f"[Pinterest] 토큰 갱신 실패 ({resp.status_code}): {resp.text[:200]}")
            tracker.log_error("other")
    except Exception as e:
        print(f"[Pinterest] 토큰 갱신 오류: {e}")
        tracker.log_error("other")
    return None


def _headers():
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type": "application/json",
    }


def _is_configured() -> bool:
    token = _get_token()
    return bool(token) and token not in ("", "placeholder")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 보드 조회
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def list_boards() -> list[dict]:
    if not _is_configured():
        return []
    try:
        resp = requests.get(
            f"{PINTEREST_API}/boards",
            headers=_headers(),
            timeout=15,
        )
        if resp.status_code == 200:
            boards = resp.json().get("items", [])
            for b in boards:
                print(f"  [보드] {b.get('name', '?')} (ID: {b.get('id', '?')})")
            tracker.log_api_call("pinterest")
            return boards
        elif resp.status_code == 401:
            print("[Pinterest] 토큰 만료. 갱신 시도 중...")
            if refresh_access_token():
                return list_boards()
        print(f"[Pinterest] 보드 조회 실패 ({resp.status_code})")
    except Exception as e:
        print(f"[Pinterest] 보드 조회 오류: {e}")
        tracker.log_error("other")
    return []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 핀 생성
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_pin(title: str, description: str, link: str,
               image_path: str = None, image_url: str = None) -> dict | None:
    if not _is_configured():
        print("[Pinterest] 토큰 미설정. 핀 생성을 건너뜁니다.")
        return None

    if not PINTEREST_BOARD_ID:
        print("[Pinterest] PINTEREST_BOARD_ID 미설정. 핀 생성을 건너뜁니다.")
        return None

    pin_data = {
        "board_id": PINTEREST_BOARD_ID,
        "title": title[:100],
        "description": description[:500],
        "link": link,
    }

    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        mime = "image/png" if image_path.endswith(".png") else "image/jpeg"
        pin_data["media_source"] = {
            "source_type": "image_base64",
            "content_type": mime,
            "data": img_b64,
        }
    elif image_url:
        pin_data["media_source"] = {
            "source_type": "image_url",
            "url": image_url,
        }
    else:
        print("[Pinterest] 이미지 없음. 핀 생성을 건너뜁니다.")
        return None

    try:
        resp = requests.post(
            f"{PINTEREST_API}/pins",
            json=pin_data,
            headers=_headers(),
            timeout=30,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            pin_id = data.get("id", "?")
            print(f"[Pinterest] 핀 생성 성공! (ID: {pin_id})")
            tracker.log_api_call("pinterest")
            return data
        elif resp.status_code == 401:
            print("[Pinterest] 토큰 만료. 갱신 후 재시도...")
            if refresh_access_token():
                return create_pin(title, description, link, image_path, image_url)
        print(f"[Pinterest] 핀 생성 실패 ({resp.status_code}): {resp.text[:200]}")
        tracker.log_error("other")
    except Exception as e:
        print(f"[Pinterest] 핀 생성 오류: {e}")
        tracker.log_error("other")
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 블로그 포스트 → 핀 자동 변환
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def post_blog_to_pinterest(blog: dict, keywords: list[dict] = None) -> bool:
    if not _is_configured():
        print("[Pinterest] 설정 미완료. Pinterest 게시를 건너뜁니다.")
        return False

    title = blog.get("title", "Fashion Trend")
    slug = blog.get("slug", "")
    summary = blog.get("summary", "")
    blog_url = f"{BLOG_BASE_URL}/{slug}.html"

    # 해시태그 생성
    hashtags = ["FashionTrends", "USFashion", "TrendLoopUSA", "OOTD"]
    if keywords:
        for kw in keywords[:5]:
            tag = kw.get("keyword", "").replace(" ", "").replace("-", "")
            tag = re.sub(r"[^a-zA-Z0-9]", "", tag)
            if tag and len(tag) > 2:
                hashtags.append(tag)

    description = f"{title}\n\n"
    if summary:
        clean_summary = re.sub(r"#\S+", "", summary).strip()
        if clean_summary:
            description += f"{clean_summary}\n\n"
    description += " ".join(f"#{tag}" for tag in hashtags[:10])

    # 블로그 HTML에서 첫 번째 이미지 URL 추출
    image_url = None
    html_content = blog.get("html", "")
    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html_content)
    if img_match:
        image_url = img_match.group(1)
        if image_url.startswith("/"):
            image_url = f"{BLOG_BASE_URL}{image_url}"

    # docs/ 폴더에서 관련 이미지 파일 검색
    image_path = None
    if not image_url:
        docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            candidate = os.path.join(docs_dir, f"{slug}{ext}")
            if os.path.exists(candidate):
                image_path = candidate
                break

    if not image_url and not image_path:
        print("[Pinterest] 이미지를 찾을 수 없습니다. OG 이미지를 사용합니다.")
        image_url = f"{BLOG_BASE_URL}/og-image.png"

    result = create_pin(
        title=title[:100],
        description=description[:500],
        link=blog_url,
        image_path=image_path,
        image_url=image_url,
    )

    if result:
        pin_url = f"https://www.pinterest.com/pin/{result.get('id', '')}"
        print(f"[Pinterest] 게시 완료!")
        print(f"  - 핀 URL: {pin_url}")
        print(f"  - 블로그 링크: {blog_url}")
        return True

    return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 벌크 포스팅 (과거 글 일괄 핀)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def bulk_pin_existing_posts(max_pins: int = 10) -> int:
    if not _is_configured():
        print("[Pinterest] 설정 미완료. 벌크 핀을 건너뜁니다.")
        return 0

    docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
    if not os.path.exists(docs_dir):
        print("[Pinterest] docs/ 폴더가 없습니다.")
        return 0

    html_files = sorted(
        [f for f in os.listdir(docs_dir) if f.endswith(".html") and f != "index.html"],
        reverse=True,
    )

    created = 0
    for filename in html_files[:max_pins]:
        slug = filename.replace(".html", "")
        filepath = os.path.join(docs_dir, filename)

        with open(filepath, "r", encoding="utf-8") as f:
            html = f.read()

        title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
        title = title_match.group(1).replace(" | TrendLoop USA", "") if title_match else slug

        blog_url = f"{BLOG_BASE_URL}/{filename}"
        description = f"{title}\n\n#FashionTrends #USFashion #TrendLoopUSA"

        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html)
        image_url = img_match.group(1) if img_match else None

        result = create_pin(
            title=title[:100],
            description=description[:500],
            link=blog_url,
            image_url=image_url,
        )

        if result:
            created += 1
            print(f"  [{created}/{max_pins}] 핀 생성: {title[:50]}...")

    print(f"[Pinterest] 벌크 핀 완료: {created}/{len(html_files[:max_pins])}개 성공")
    return created


if __name__ == "__main__":
    print("=== Pinterest 에이전트 테스트 ===\n")
    if _is_configured():
        print("[상태] Pinterest API 토큰 설정됨")
        print("\n[보드 목록]")
        list_boards()
    else:
        print("[상태] Pinterest API 토큰 미설정")
        print("  -> .env에 PINTEREST_ACCESS_TOKEN, PINTEREST_BOARD_ID 설정 필요")
