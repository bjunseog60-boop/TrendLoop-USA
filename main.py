"""
main.py - TrendLoop USA 오케스트레이터 (지휘자)

보안 & 안전장치:
  - 전체 실행 시간 제한 (5분)
  - 비정상 동작 감지 시 즉시 종료
  - 파일 삭제 대신 _deleted_items/ 이동
  - 실행 전 자동 백업
  - API 사용량 보고서 출력
"""

import os
import glob
import sys
import signal
import time

sys.path.insert(0, os.path.dirname(__file__))

from config import MAX_TOTAL_RUNTIME_SECONDS, MAX_CONSECUTIVE_ERRORS
from safety import tracker, create_backup, print_recovery_commands
from agents.analyst import fetch_trending_keywords
from agents.writer import generate_blog_post
from agents.marketer import post_to_twitter, ping_google_indexing, update_sitemap


def _timeout_handler(signum, frame):
    print(f"\n[안전장치] 최대 실행 시간 {MAX_TOTAL_RUNTIME_SECONDS}초 초과! 강제 종료합니다.")
    tracker.print_report()
    sys.exit(1)


def _setup_timeout():
    try:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(MAX_TOTAL_RUNTIME_SECONDS)
        print(f"[안전장치] 전체 타임아웃: {MAX_TOTAL_RUNTIME_SECONDS}초")
    except AttributeError:
        import threading

        def _force_exit():
            print(f"\n[안전장치] 최대 실행 시간 {MAX_TOTAL_RUNTIME_SECONDS}초 초과! 강제 종료합니다.")
            tracker.print_report()
            os._exit(1)

        timer = threading.Timer(MAX_TOTAL_RUNTIME_SECONDS, _force_exit)
        timer.daemon = True
        timer.start()
        print(f"[안전장치] 전체 타임아웃: {MAX_TOTAL_RUNTIME_SECONDS}초 (Windows 모드)")


def main():
    start_time = time.time()
    _setup_timeout()

    print("=" * 60)
    print("  TrendLoop USA - 자동 패션 트렌드 블로그 시스템")
    print("=" * 60)
    print()

    # ── 보안 상태 출력 ──
    print("[안전장치] 활성화된 보호 기능:")
    print(f"  - 전체 실행 제한:    {MAX_TOTAL_RUNTIME_SECONDS}초")
    print(f"  - 연속 에러 한도:    {MAX_CONSECUTIVE_ERRORS}회")
    print(f"  - 파일 삭제 보호:    _deleted_items/ 이동 방식")
    print(f"  - 자동 백업:         실행 전 docs/ 스냅샷")
    print(f"  - 서버 비용:         $0 (GitHub Actions ephemeral)")
    print()

    # ── 실행 전 자동 백업 ──
    create_backup()
    print()

    # ── 비상 복구 명령어 안내 ──
    print_recovery_commands()
    print()

    # ━━━━━━ STEP 1: 에이전트 A (분석가) ━━━━━━
    print("[STEP 1] 에이전트 A (분석가) - 트렌드 키워드 추출 중...")
    print("-" * 40)
    try:
        keywords = fetch_trending_keywords()
    except Exception as e:
        print(f"[STEP 1 오류] {e}")
        tracker.log_error("twitter")
        keywords = None

    if not keywords:
        print("[오류] 키워드를 추출하지 못했습니다. 종료합니다.")
        tracker.print_report()
        sys.exit(1)

    elapsed = time.time() - start_time
    print(f"[타이머] STEP 1 완료 ({elapsed:.1f}초 경과)")
    print()

    # ── 비정상 동작 체크 ──
    if tracker.is_abnormal(MAX_CONSECUTIVE_ERRORS):
        print("[안전장치] 비정상 동작 감지! 즉시 종료합니다.")
        tracker.print_report()
        sys.exit(1)

    # ━━━━━━ STEP 2: 에이전트 B (작가) ━━━━━━
    print("[STEP 2] 에이전트 B (작가) - 블로그 글 작성 중...")
    print("-" * 40)
    try:
        blog = generate_blog_post(keywords)
    except Exception as e:
        print(f"[STEP 2 오류] {e}")
        tracker.log_error("gemini")
        blog = None

    if tracker.is_abnormal(MAX_CONSECUTIVE_ERRORS):
        print("[안전장치] 비정상 동작 감지! 즉시 종료합니다.")
        tracker.print_report()
        sys.exit(1)

    if not blog:
        print("[오류] 블로그 글을 생성하지 못했습니다. 종료합니다.")
        tracker.print_report()
        sys.exit(1)

    elapsed = time.time() - start_time
    print(f"[타이머] STEP 2 완료 ({elapsed:.1f}초 경과)")
    print()

    # ━━━━━━ STEP 3: 사이트맵 업데이트 ━━━━━━
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

    # ━━━━━━ STEP 4: 에이전트 C (마케터) ━━━━━━
    print("[STEP 4] 에이전트 C (마케터) - 홍보 및 색인 중...")
    print("-" * 40)

    tweet_ok = post_to_twitter(blog["summary"], blog["slug"])
    index_ok = ping_google_indexing(blog["slug"])

    print()

    # ━━━━━━ 결과 요약 ━━━━━━
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

    # ── API 사용량 보고서 ──
    tracker.print_report()


if __name__ == "__main__":
    main()
