"""
config.py - 환경 변수 기반 보안 설정 (키 하드코딩 절대 금지)

모든 API 키는 GitHub Secrets → 환경 변수로만 참조합니다.
로컬 테스트 시에는 .env 파일을 만들어 사용하되, .gitignore가 차단합니다.
"""

import os
import json

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# X (Twitter) API 인증 정보
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
X_BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN", "")
X_API_KEY = os.environ.get("X_API_KEY", "")
X_API_SECRET = os.environ.get("X_API_SECRET", "")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", "")
X_ACCESS_TOKEN_SECRET = os.environ.get("X_ACCESS_TOKEN_SECRET", "")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Gemini API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Amazon Associates
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AMAZON_TAG = os.environ.get("AMAZON_TAG", "trendloop-20")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 블로그 설정
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BLOG_BASE_URL = os.environ.get("BLOG_BASE_URL", "https://bjunseog60-boop.github.io/TrendLoop-USA")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 트렌드 검색 설정
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FASHION_SEED_QUERIES = [
    "fashion trend 2026",
    "outfit of the day OOTD",
    "streetwear trend USA",
    "spring fashion must have",
    "trending fashion style",
]
MAX_KEYWORDS = 5

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 비용 안전장치
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
API_TIMEOUT_SECONDS = 30
MAX_TOTAL_RUNTIME_SECONDS = 300
GEMINI_DAILY_CALL_LIMIT = 5
MAX_CONSECUTIVE_ERRORS = 3

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 멀티 채널 배포 설정 (확장용)
# 환경 변수 DISTRIBUTION_CHANNELS에 JSON 배열로 등록
# 예: [{"name":"site_a","api_key":"...","endpoint":"..."}]
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_distribution_channels() -> list[dict]:
    """멀티 채널 배포 대상 목록을 환경 변수에서 불러옵니다."""
    raw = os.environ.get("DISTRIBUTION_CHANNELS", "[]")
    try:
        channels = json.loads(raw)
        return channels if isinstance(channels, list) else []
    except json.JSONDecodeError:
        return []

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Adobe Firefly API (확장 준비)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADOBE_CLIENT_ID = os.environ.get("ADOBE_CLIENT_ID", "")
ADOBE_CLIENT_SECRET = os.environ.get("ADOBE_CLIENT_SECRET", "")
