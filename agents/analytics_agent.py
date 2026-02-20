"""Agent Analytics - GA4 Data API for intelligent content scheduling.
Analyzes visitor data to prioritize popular topics for content generation.
Gracefully skips if GA4_PROPERTY_ID is not set.
"""
import os
import json
from datetime import datetime, timezone

os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "google_creds.json"),
)

from safety import tracker

# GA4 Property ID (set in .env)
GA4_PROPERTY_ID = os.environ.get("GA4_PROPERTY_ID", "")


def _get_client():
    """Lazy-load Analytics client."""
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        return BetaAnalyticsDataClient()
    except Exception as e:
        print(f"[Analytics] Client init failed: {e}")
        return None


def get_top_pages(days=30, limit=20):
    """Get top performing pages by pageviews."""
    if not GA4_PROPERTY_ID:
        print("[Analytics] GA4_PROPERTY_ID not set. Skipping.")
        return []

    client = _get_client()
    if not client:
        return []

    try:
        from google.analytics.data_v1beta.types import (
            RunReportRequest, DateRange, Dimension, Metric, OrderBy,
        )

        request = RunReportRequest(
            property=f"properties/{GA4_PROPERTY_ID}",
            date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
            dimensions=[Dimension(name="pagePath"), Dimension(name="pageTitle")],
            metrics=[
                Metric(name="screenPageViews"),
                Metric(name="averageSessionDuration"),
                Metric(name="bounceRate"),
            ],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)],
            limit=limit,
        )

        response = client.run_report(request)
        tracker.log_api_call("analytics")

        pages = []
        for row in response.rows:
            pages.append({
                "path": row.dimension_values[0].value,
                "title": row.dimension_values[1].value,
                "pageviews": int(row.metric_values[0].value),
                "avg_duration": float(row.metric_values[1].value),
                "bounce_rate": float(row.metric_values[2].value),
            })
        return pages
    except Exception as e:
        print(f"[Analytics] get_top_pages error: {e}")
        tracker.log_error("analytics")
        return []


def get_top_search_queries(days=30, limit=20):
    """Get top search queries driving traffic."""
    if not GA4_PROPERTY_ID:
        return []

    client = _get_client()
    if not client:
        return []

    try:
        from google.analytics.data_v1beta.types import (
            RunReportRequest, DateRange, Dimension, Metric, OrderBy,
        )

        request = RunReportRequest(
            property=f"properties/{GA4_PROPERTY_ID}",
            date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
            dimensions=[Dimension(name="sessionDefaultChannelGroup"), Dimension(name="pagePath")],
            metrics=[Metric(name="sessions"), Metric(name="newUsers")],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
            limit=limit,
        )

        response = client.run_report(request)
        tracker.log_api_call("analytics")

        queries = []
        for row in response.rows:
            queries.append({
                "channel": row.dimension_values[0].value,
                "page": row.dimension_values[1].value,
                "sessions": int(row.metric_values[0].value),
                "new_users": int(row.metric_values[1].value),
            })
        return queries
    except Exception as e:
        print(f"[Analytics] get_top_search_queries error: {e}")
        tracker.log_error("analytics")
        return []


def suggest_topics(days=30):
    """Analyze analytics data and suggest high-potential topics."""
    top_pages = get_top_pages(days=days)
    if not top_pages:
        print("[Analytics] No data available. Skipping topic suggestions.")
        return []

    from collections import Counter
    word_freq = Counter()
    for page in top_pages:
        title = page.get("title", "")
        words = [w.lower().strip() for w in title.split() if len(w) > 3]
        weight = page.get("pageviews", 1)
        for w in words:
            word_freq[w] += weight

    stop_words = {"the", "and", "for", "with", "your", "that", "this", "from", "have", "best", "most", "style", "fashion", "trend"}
    suggestions = [
        {"keyword": word, "score": count}
        for word, count in word_freq.most_common(30)
        if word not in stop_words
    ][:15]

    if suggestions:
        print(f"[Analytics] Top keywords: {[s['keyword'] for s in suggestions[:5]]}")
    return suggestions


def get_content_performance_report():
    """Generate a full content performance report."""
    if not GA4_PROPERTY_ID:
        print("[Analytics] GA4_PROPERTY_ID not set. Skipping report.")
        return {}

    top_pages = get_top_pages(days=30)
    search_data = get_top_search_queries(days=30)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "top_pages": top_pages,
        "traffic_sources": search_data,
        "suggested_topics": suggest_topics(days=30),
    }

    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)
    report_path = os.path.join(data_dir, "analytics_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"[Analytics] Report saved: {report_path}")
    return report


if __name__ == "__main__":
    print("=== Analytics API Test ===")
    if GA4_PROPERTY_ID:
        report = get_content_performance_report()
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("GA4_PROPERTY_ID not set. Set it in .env to enable analytics.")
        print("System will continue without analytics - no crash.")
