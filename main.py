"""
main.py - TrendLoop USA 오케스트레이터 (지휘자)
역할: 에이전트 A, B, C를 순서대로 실행합니다.

비용 안전장치:
  - 전체 실행 시간 제한 (기본 5분)
  - 연속 에러 감지 시 즉시 종료
  - Gemini API 일일 호출 횟수 제한
  - GitHub Actions ephemeral runner에서만 실행 (서버 비용 0원)
"""

import os
import glob
import sys
import signal
import time

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(__file__))

from config import MAX_TOTAL_RUNTIME_SECONDS, MAX_CONSECUTIVE_ERRORS
from agents.analyst import fetch_trending_keywords
from agents.writer import generate_blog_post
from agents.marketer import post_to_twitter, ping_google_indexing, update_sitemap


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 전체 실행 시간 제한 (타임아웃 폭탄)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _timeout_handler(signum, frame):
    """최대 실행 시간 초과 시 강제 종료"""
    print(f"\n[안전장치] 최대 실행 시간 {MAX_TOTAL_RUNTIME_SECONDS}초 초과! 강제 종료합니다.")
    sys.exit(1)


def _setup_timeout():
    """프로그램 전체 타임아웃을 설정합니다 (Unix 전용, GitHub Actions에서 작동)"""
    try:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(MAX_TOTAL_RUNTIME_SECONDS)
        print(f"[안전장치] 전체 타임아웃: {MAX_TOTAL_RUNTIME_SECONDS}초")
    except AttributeError:
        # Windows에서는 SIGALRM이 없음 - 스레드 방식으로 대체
        import threading

        def _force_exit():
            print(f"\n[안전장치] 최대 실행 시간 {MAX_TOTAL_RUNTIME_SECONDS}초 초과! 강제 종료합니다.")
            os._exit(1)

        timer = threading.Timer(MAX_TOTAL_RUNTIME_SECONDS, _force_exit)
        timer.daemon = True
        timer.start()
        print(f"[안전장치] 전체 타임아웃: {MAX_TOTAL_RUNTIME_SECONDS}초 (Windows 모드)")


def main():
    start_time = time.time()

    # ── 타임아웃 설정 ──
    _setup_timeout()

    print("=" * 60)
    print("  TrendLoop USA - 자동 패션 트렌드 블로그 시스템")
    print("=" * 60)
    print()

    # ── 비용 안전장치 상태 출력 ──
    print("[안전장치] 활성화된 보호 기능:")
    print(f"  - 전체 실행 제한: {MAX_TOTAL_RUNTIME_SECONDS}초")
    print(f"  - 연속 에러 한도: {MAX_CONSECUTIVE_ERRORS}회")
    print(f"  - GitHub Actions ephemeral runner (서버 비용 0원)")
    print()

    consecutive_step_errors = 0

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 1: 에이전트 A (분석가) 실행
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("[STEP 1] 에이전트 A (분석가) - 트렌드 키워드 추출 중...")
    print("-" * 40)
    try:
        keywords = fetch_trending_keywords()
    except Exception as e:
        print(f"[STEP 1 오류] 예상치 못한 에러: {e}")
        keywords = None
        consecutive_step_errors += 1

    if not keywords:
        print("[오류] 키워드를 추출하지 못했습니다. 종료합니다.")
        sys.exit(1)

    elapsed = time.time() - start_time
    print(f"[타이머] STEP 1 완료 ({elapsed:.1f}초 경과)")
    print()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 2: 에이전트 B (작가) 실행
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("[STEP 2] 에이전트 B (작가) - 블로그 글 작성 중...")
    print("-" * 40)
    try:
        blog = generate_blog_post(keywords)
    except Exception as e:
        print(f"[STEP 2 오류] 예상치 못한 에러: {e}")
        blog = None
        consecutive_step_errors += 1

    # ── 비정상 동작 감지 ──
    if consecutive_step_errors >= MAX_CONSECUTIVE_ERRORS:
        print(f"[안전장치] 연속 {consecutive_step_errors}회 에러! 비정상 동작으로 판단. 즉시 종료합니다.")
        sys.exit(1)

    if not blog:
        print("[오류] 블로그 글을 생성하지 못했습니다. 종료합니다.")
        sys.exit(1)

    consecutive_step_errors = 0  # 성공하면 리셋
    elapsed = time.time() - start_time
    print(f"[타이머] STEP 2 완료 ({elapsed:.1f}초 경과)")
    print()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 3: 사이트맵 업데이트
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("[STEP 3] 사이트맵 업데이트 중...")
    print("-" * 40)

    docs_dir = os.path.join(os.path.dirname(__file__), "docs")
    existing_files = glob.glob(os.path.join(docs_dir, "*.html"))
    all_slugs = [
        os.path.splitext(os.path.basename(f))[0] for f in existing_files
    ]
    if blog["slug"] not in all_slugs:
        all_slugs.append(blog["slug"])

    update_sitemap(all_slugs)
    print()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 4: 에이전트 C (마케터) 실행
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("[STEP 4] 에이전트 C (마케터) - 홍보 및 색인 중...")
    print("-" * 40)

    tweet_ok = post_to_twitter(blog["summary"], blog["slug"])
    index_ok = ping_google_indexing(blog["slug"])

    print()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 결과 요약
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    total_time = time.time() - start_time
    print("=" * 60)
    print("  실행 결과 요약")
    print("=" * 60)
    print(f"  키워드 추출: {len(keywords)}개")
    print(f"  블로그 글:   {blog['title']}")
    print(f"  파일 저장:   {blog['file_path']}")
    print(f"  트윗 게시:   {'성공' if tweet_ok else '건너뜀/실패'}")
    print(f"  검색 색인:   {'성공' if index_ok else '건너뜀/실패'}")
    print(f"  총 실행 시간: {total_time:.1f}초")
    print("=" * 60)


if __name__ == "__main__":
    main()
