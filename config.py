"""
config.py - 환경 변수에서 API 키와 설정을 불러오는 파일

GitHub Secrets에 아래 값들을 등록해야 합니다:
  - X_BEARER_TOKEN      : X(트위터) Bearer Token (검색용)
  - X_API_KEY           : X(트위터) API Key
  - X_API_SECRET        : X(트위터) API Secret
  - X_ACCESS_TOKEN      : X(트위터) Access Token
  - X_ACCESS_TOKEN_SECRET: X(트위터) Access Token Secret
  - GEMINI_API_KEY      : Google Gemini API Key
  - AMAZON_TAG          : 아마존 어소시에이트 추적 태그 (예: mytag-20)
  - BLOG_BASE_URL       : 블로그 기본 URL (GitHub Pages 주소)
"""

import os

# ── X (Twitter) API 인증 정보 ──
X_BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN", "")
X_API_KEY = os.environ.get("X_API_KEY", "")
X_API_SECRET = os.environ.get("X_API_SECRET", "")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", "")
X_ACCESS_TOKEN_SECRET = os.environ.get("X_ACCESS_TOKEN_SECRET", "")

# ── Gemini API ──
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ── Amazon Associates ──
AMAZON_TAG = os.environ.get("AMAZON_TAG", "trendloop-20")

# ── 블로그 설정 ──
BLOG_BASE_URL = os.environ.get("BLOG_BASE_URL", "https://yourusername.github.io/TrendLoop-USA")

# ── 트렌드 검색 설정 ──
FASHION_SEED_QUERIES = [
    "fashion trend 2026",
    "outfit of the day OOTD",
    "streetwear trend USA",
    "spring fashion must have",
    "trending fashion style",
]
MAX_KEYWORDS = 5

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 비용 안전장치 설정
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# API 호출 타임아웃 (초)
API_TIMEOUT_SECONDS = 30

# 전체 프로그램 최대 실행 시간 (초) - 5분
MAX_TOTAL_RUNTIME_SECONDS = 300

# Gemini API 하루 최대 호출 횟수
GEMINI_DAILY_CALL_LIMIT = 5

# 연속 에러 최대 허용 횟수 (이 횟수 초과 시 즉시 종료)
MAX_CONSECUTIVE_ERRORS = 3
