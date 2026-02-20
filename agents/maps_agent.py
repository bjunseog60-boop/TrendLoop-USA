"""Agent Maps - Google Maps API for fashion store trend analysis.
Collects location-based fashion data for regional trend insights.
Gracefully skips if MAPS_API_KEY is not set.
"""
import os
import json
from datetime import datetime, timezone

from safety import tracker

MAPS_API_KEY = os.environ.get("MAPS_API_KEY", "")

# Fashion retail categories to track
FASHION_CATEGORIES = [
    "fashion boutique",
    "women clothing store",
    "designer outlet",
    "vintage clothing store",
    "streetwear shop",
]

# Key US fashion cities
FASHION_CITIES = {
    "New York": (40.7128, -74.0060),
    "Los Angeles": (34.0522, -118.2437),
    "Miami": (25.7617, -80.1918),
    "Chicago": (41.8781, -87.6298),
    "San Francisco": (37.7749, -122.4194),
}


def _get_client():
    """Lazy-load Maps client."""
    if not MAPS_API_KEY:
        return None
    try:
        import googlemaps
        return googlemaps.Client(key=MAPS_API_KEY)
    except Exception as e:
        print(f"[Maps] Client init failed: {e}")
        return None


def search_fashion_stores(city_name, category, radius=5000):
    """Search for fashion stores near a city center."""
    gmaps = _get_client()
    if not gmaps:
        return []

    lat, lng = FASHION_CITIES.get(city_name, (40.7128, -74.0060))

    try:
        results = gmaps.places_nearby(
            location=(lat, lng),
            radius=radius,
            keyword=category,
            type="clothing_store",
        )
        tracker.log_api_call("maps")

        stores = []
        for place in results.get("results", [])[:10]:
            stores.append({
                "name": place.get("name"),
                "rating": place.get("rating", 0),
                "total_ratings": place.get("user_ratings_total", 0),
                "address": place.get("vicinity", ""),
                "types": place.get("types", []),
                "price_level": place.get("price_level", 0),
            })
        return stores
    except Exception as e:
        print(f"[Maps] Search error ({city_name}, {category}): {e}")
        tracker.log_error("maps")
        return []


def analyze_city_fashion_trends(city_name):
    """Analyze fashion store trends in a specific city."""
    if not MAPS_API_KEY:
        return {}

    print(f"[Maps] Analyzing fashion trends in {city_name}...")

    city_data = {}
    for category in FASHION_CATEGORIES:
        stores = search_fashion_stores(city_name, category)
        if stores:
            avg_rating = sum(s["rating"] for s in stores) / len(stores)
            city_data[category] = {
                "store_count": len(stores),
                "avg_rating": round(avg_rating, 2),
                "top_stores": stores[:3],
            }

    return city_data


def generate_regional_trend_report():
    """Generate fashion trend report across major US cities."""
    if not MAPS_API_KEY:
        print("[Maps] MAPS_API_KEY not set. Skipping regional report.")
        return {}

    print("[Maps] Generating regional fashion trend report...")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cities": {},
    }

    for city in FASHION_CITIES:
        report["cities"][city] = analyze_city_fashion_trends(city)

    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)
    report_path = os.path.join(data_dir, "regional_trends.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"[Maps] Report saved: {report_path}")
    return report


def get_location_based_recommendations(city_name):
    """Get fashion recommendations based on local store trends."""
    if not MAPS_API_KEY:
        return []

    data = analyze_city_fashion_trends(city_name)
    if not data:
        return []

    recommendations = []
    for category, info in data.items():
        if info["store_count"] > 3 and info["avg_rating"] > 4.0:
            recommendations.append({
                "trend": category,
                "city": city_name,
                "confidence": "high",
                "reason": f"{info['store_count']} popular stores (avg {info['avg_rating']} stars)",
            })

    return recommendations


if __name__ == "__main__":
    print("=== Maps API Test ===")
    if MAPS_API_KEY:
        result = analyze_city_fashion_trends("New York")
        print(json.dumps(result, indent=2))
    else:
        print("MAPS_API_KEY not set. Set it in .env to enable maps features.")
        print("System will continue without maps - no crash.")
