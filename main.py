"""
main.py - TrendLoop USA 오케스트레이터 (지휘자)
역할: 에이전트 A, B, C를 순서대로 실행합니다.

실행 흐름:
  1. 에이전트 A (분석가) → 트렌드 키워드 추출
  2. 에이전트 B (작가)  → 블로그 글 생성
  3. 에이전트 C (마케터) → 트위터 게시 + 구글 색인
"""

import os
import glob
import sys

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(__file__))

from agents.analyst import fetch_trending_keywords
from agents.writer import generate_blog_post
from agents.marketer import post_to_twitter, ping_google_indexing, update_sitemap


def main():
    print("=" * 60)
    print("  TrendLoop USA - 자동 패션 트렌드 블로그 시스템")
    print("=" * 60)
    print()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 1: 에이전트 A (분석가) 실행
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("[STEP 1] 에이전트 A (분석가) - 트렌드 키워드 추출 중...")
    print("-" * 40)
    keywords = fetch_trending_keywords()

    if not keywords:
        print("[오류] 키워드를 추출하지 못했습니다. 종료합니다.")
        sys.exit(1)

    print()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 2: 에이전트 B (작가) 실행
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("[STEP 2] 에이전트 B (작가) - 블로그 글 작성 중...")
    print("-" * 40)
    blog = generate_blog_post(keywords)

    if not blog:
        print("[오류] 블로그 글을 생성하지 못했습니다. 종료합니다.")
        sys.exit(1)

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

    # 트위터 게시
    tweet_ok = post_to_twitter(blog["summary"], blog["slug"])

    # 구글 색인 요청
    index_ok = ping_google_indexing(blog["slug"])

    print()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 결과 요약
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("=" * 60)
    print("  실행 결과 요약")
    print("=" * 60)
    print(f"  키워드 추출: {len(keywords)}개")
    print(f"  블로그 글:   {blog['title']}")
    print(f"  파일 저장:   {blog['file_path']}")
    print(f"  트윗 게시:   {'성공' if tweet_ok else '건너뜀/실패'}")
    print(f"  검색 색인:   {'성공' if index_ok else '건너뜀/실패'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
