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
from agents.pinterest import post_blog_to_pinterest
from agents.index_builder import rebuild_index
from agents.rss_builder import rebuild_rss
from agents.reddit_bot import post_to_reddit
from agents.amazon_shorts import generate_shorts_content
from agents.tumblr_bot import post_to_tumblr
from agents.vertex_agent import analyze_trends_deep, generate_blog_images
from agents.vision_agent import enrich_blog_post
from agents.translation_agent import translate_to_all_languages
from agents.affiliate_links import inject_affiliate_links


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

    # ━━━━━━ STEP 1.5: Gemini 2.5 Pro 심층 분석 ━━━━━━
    print("[STEP 1.5] Gemini 2.5 Pro - 심층 트렌드 분석 중...")
    print("-" * 40)
    try:
        deep_analysis = analyze_trends_deep(keywords)
        print(f"[STEP 1.5] 분석 완료: {list(deep_analysis.keys())}")
    except Exception as e:
        print(f"[STEP 1.5 오류] {e}")
        deep_analysis = {}

    elapsed = time.time() - start_time
    print(f"[타이머] STEP 1.5 완료 ({elapsed:.1f}초 경과)")
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

    # ━━━━━━ STEP 2.5: Imagen 3 고화질 이미지 생성 ━━━━━━
    print("[STEP 2.5] Imagen 3 - 블로그 이미지 생성 중...")
    print("-" * 40)
    try:
        blog_images = generate_blog_images(blog["title"], keywords, blog["slug"])
        img_ok = bool(blog_images.get("featured"))
        print(f"[STEP 2.5] Featured: {blog_images.get('featured', 'N/A')}")
        print(f"[STEP 2.5] Pin: {blog_images.get('pin', 'N/A')}")
    except Exception as e:
        print(f"[STEP 2.5 오류] {e}")
        blog_images = {}
        img_ok = False

    elapsed = time.time() - start_time
    print(f"[타이머] STEP 2.5 완료 ({elapsed:.1f}초 경과)")
    print()

    # ━━━━━━ STEP 2.7: Vision API + Affiliate 보강 ━━━━━━
    print("[STEP 2.7] Vision API + Multi-Affiliate 링크 보강 중...")
    print("-" * 40)
    try:
        featured_img = blog_images.get("featured") if blog_images else None
        if featured_img:
            blog = enrich_blog_post(blog, featured_img)
            print("[STEP 2.7] Vision 분석 완료")
    except Exception as e:
        print(f"[STEP 2.7 오류] Vision: {e}")

    # Inject multi-platform affiliate links
    try:
        products = [
            {"name": kw.get("keyword", str(kw)) if isinstance(kw, dict) else str(kw),
             "keyword": kw.get("keyword", str(kw)) if isinstance(kw, dict) else str(kw)}
            for kw in keywords[:5]
        ]
        if blog.get("html"):
            blog["html"] = inject_affiliate_links(blog["html"], products)
            print(f"[STEP 2.7] {len(products)} affiliate 링크 주입 완료")
    except Exception as e:
        print(f"[STEP 2.7 오류] Affiliate: {e}")

    elapsed = time.time() - start_time
    print(f"[타이머] STEP 2.7 완료 ({elapsed:.1f}초 경과)")
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
    rebuild_index()
    rebuild_rss()
    print()


    # ━━━━━━ STEP 3.5: 에이전트 D (Pinterest) ━━━━━━
    print("[STEP 3.5] 에이전트 D (Pinterest) - 핀 자동 생성 중...")
    print("-" * 40)
    try:
        pin_ok = post_blog_to_pinterest(blog, keywords)
    except Exception as e:
        print(f"[STEP 3.5 오류] {e}")
        tracker.log_error("other")
        pin_ok = False

    elapsed = time.time() - start_time
    print(f"[타이머] STEP 3.5 완료 ({elapsed:.1f}초 경과)")
    print()

    # ━━━━━━ STEP 4: 에이전트 C (마케터) ━━━━━━
    print("[STEP 4] 에이전트 C (마케터) - 홍보 및 색인 중...")
    print("-" * 40)

    tweet_ok = post_to_twitter(blog["summary"], blog["slug"])
    index_ok = ping_google_indexing(blog["slug"])

    # ━━━━━━ STEP 5: Reddit + Tumblr ━━━━━━
    print("[STEP 5] Reddit + Tumblr - 자동 게시 중...")
    print("-" * 40)
    try:
        reddit_ok = post_to_reddit(blog, keywords)
    except Exception as e:
        print(f"[STEP 5 오류] Reddit: {e}")
        reddit_ok = False

    try:
        tumblr_ok = post_to_tumblr(blog, keywords)
    except Exception as e:
        print(f"[STEP 5 오류] Tumblr: {e}")
        tumblr_ok = False

    elapsed = time.time() - start_time
    print(f"[타이머] STEP 5 완료 ({elapsed:.1f}초 경과)")
    print()

    # ━━━━━━ STEP 6: Amazon Shorts ━━━━━━
    print('[STEP 6] Amazon Shorts - generating...')
    print('-' * 40)
    try:
        shorts = generate_shorts_content()
        shorts_ok = len(shorts) > 0
    except Exception as e:
        print(f'[STEP 6 error] {e}')
        shorts_ok = False
    print()

    # ━━━━━━ STEP 7: 다국어 번역 ━━━━━━
    print("[STEP 7] Translation API - 다국어 포스팅 생성 중...")
    print("-" * 40)
    translations = {}
    try:
        html_path = blog.get("file_path", "")
        if html_path and os.path.exists(html_path):
            with open(html_path, "r", encoding="utf-8") as f:
                html_body = f.read()
            translations = translate_to_all_languages(html_body, blog["slug"])
            print(f"[STEP 7] {len(translations)} languages translated")
        else:
            print("[STEP 7] No HTML file to translate.")
    except Exception as e:
        print(f"[STEP 7 오류] {e}")
        translations = {}

    elapsed = time.time() - start_time
    print(f"[타이머] STEP 7 완료 ({elapsed:.1f}초 경과)")
    print()

    # ━━━━━━ 결과 요약 ━━━━━━
    total_time = time.time() - start_time
    print("=" * 60)
    print("  실행 결과 요약")
    print("=" * 60)
    print(f"  키워드 추출: {len(keywords)}개")
    print(f"  블로그 글:   {blog['title']}")
    print(f"  파일 저장:   {blog['file_path']}")
    print(f"  Pinterest:   {'성공' if pin_ok else '건너뜀/실패'}")
    print(f"  트윗 게시:   {'성공' if tweet_ok else '건너뜀/실패'}")
    print(f"  검색 색인:   {'성공' if index_ok else '건너뜀/실패'}")
    print(f"  다국어 번역: {len(translations)}개 언어")
    print(f"  총 실행 시간: {total_time:.1f}초")
    print("=" * 60)

    # ── API 사용량 보고서 ──
    tracker.print_report()


if __name__ == "__main__":
    main()
