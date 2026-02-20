"""
에이전트 A - 분석가 (Analyst)
역할: X(트위터)에서 미국 패션 트렌드 키워드를 검색하고 추출합니다.

작동 방식:
  1. X API v2로 패션 관련 영어 트윗을 검색
  2. 자주 등장하는 단어/해시태그를 세어서 인기 키워드 추출
  3. 상위 키워드 리스트를 반환
"""

import re
from collections import Counter
import tweepy
from config import X_BEARER_TOKEN, FASHION_SEED_QUERIES, MAX_KEYWORDS


# ── 무시할 일반적인 단어들 (불용어) ──
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
    "neither", "each", "every", "all", "any", "few", "more", "most",
    "other", "some", "such", "no", "only", "own", "same", "than", "too",
    "very", "just", "because", "as", "until", "while", "of", "at", "by",
    "for", "with", "about", "against", "between", "through", "during",
    "before", "after", "above", "below", "to", "from", "up", "down",
    "in", "out", "on", "off", "over", "under", "again", "further",
    "then", "once", "here", "there", "when", "where", "why", "how",
    "this", "that", "these", "those", "i", "me", "my", "myself", "we",
    "our", "you", "your", "he", "him", "his", "she", "her", "it", "its",
    "they", "them", "their", "what", "which", "who", "whom", "rt",
    "https", "http", "amp", "like", "get", "got", "new", "one", "im",
    "dont", "ive", "cant", "really", "love", "best", "want", "know",
}


def fetch_trending_keywords() -> list[dict]:
    """
    X API에서 패션 관련 트윗을 검색하고,
    인기 키워드를 추출해서 리스트로 반환합니다.

    반환 형식 예시:
    [
        {"keyword": "coquette", "count": 42},
        {"keyword": "baggy jeans", "count": 35},
        ...
    ]
    """
    if not X_BEARER_TOKEN:
        print("[분석가] 경고: X_BEARER_TOKEN이 설정되지 않았습니다.")
        print("[분석가] 기본 샘플 키워드를 사용합니다.")
        return _fallback_keywords()

    # ── X API v2 클라이언트 생성 ──
    client = tweepy.Client(bearer_token=X_BEARER_TOKEN)

    all_texts: list[str] = []
    all_hashtags: list[str] = []

    for query in FASHION_SEED_QUERIES:
        try:
            # 영어 트윗만, 리트윗 제외, 최근 트윗 검색
            search_query = f"{query} lang:en -is:retweet"
            response = client.search_recent_tweets(
                query=search_query,
                max_results=20,        # 쿼리당 최대 20개
                tweet_fields=["text", "entities"],
            )

            if response.data:
                for tweet in response.data:
                    all_texts.append(tweet.text)

                    # 해시태그 추출
                    if tweet.entities and "hashtags" in tweet.entities:
                        for tag in tweet.entities["hashtags"]:
                            all_hashtags.append(tag["tag"].lower())

        except tweepy.TooManyRequests:
            print(f"[분석가] API 호출 제한 도달. 현재까지 수집된 데이터로 진행합니다.")
            break
        except tweepy.TweepyException as e:
            print(f"[분석가] 검색 오류 ({query}): {e}")
            continue

    if not all_texts and not all_hashtags:
        print("[분석가] 트윗을 가져오지 못했습니다. 기본 키워드를 사용합니다.")
        return _fallback_keywords()

    # ── 키워드 빈도 분석 ──
    word_counter = Counter()

    # 해시태그 빈도 (가중치 2배)
    for tag in all_hashtags:
        if tag not in STOP_WORDS and len(tag) > 2:
            word_counter[tag] += 2

    # 트윗 본문에서 의미 있는 단어 추출
    for text in all_texts:
        words = re.findall(r"[a-zA-Z]{3,}", text.lower())
        for word in words:
            if word not in STOP_WORDS:
                word_counter[word] += 1

    # ── 상위 키워드 반환 ──
    top_keywords = word_counter.most_common(MAX_KEYWORDS)
    results = [{"keyword": kw, "count": count} for kw, count in top_keywords]

    print(f"[분석가] 추출된 트렌드 키워드 {len(results)}개:")
    for item in results:
        print(f"  - {item['keyword']} (언급 {item['count']}회)")

    return results


def _fallback_keywords() -> list[dict]:
    """API를 사용할 수 없을 때 쓰는 기본 키워드 목록"""
    fallback = [
        {"keyword": "coquette fashion", "count": 0},
        {"keyword": "quiet luxury", "count": 0},
        {"keyword": "streetwear aesthetic", "count": 0},
        {"keyword": "baggy jeans trend", "count": 0},
        {"keyword": "minimalist outfit", "count": 0},
    ]
    print("[분석가] 기본 샘플 키워드를 사용합니다:")
    for item in fallback:
        print(f"  - {item['keyword']}")
    return fallback


# ── 이 파일을 직접 실행할 때 테스트용 ──
if __name__ == "__main__":
    keywords = fetch_trending_keywords()
    print("\n최종 결과:", keywords)
