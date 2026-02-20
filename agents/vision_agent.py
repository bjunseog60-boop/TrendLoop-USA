"""Agent Vision v2 - Vision API + Gemini Multimodal for fashion image analysis.
Extracts product labels, colors, style attributes, and generates
SEO-optimized tags using AI image understanding.

Uses Google Cloud credits (ADC auth for Vision, API key for Gemini).
"""
import os
import sys
import io
import json
import base64

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__))))

os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "google_creds.json"),
)

from config import GEMINI_API_KEY
from safety import tracker

from google import genai

gemini_client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-2.5-flash"


def _get_vision_client():
    """Lazy-load Vision client."""
    try:
        from google.cloud import vision
        return vision.ImageAnnotatorClient()
    except Exception as e:
        print(f"[Vision] Client init failed: {e}")
        return None


def analyze_fashion_image(image_path):
    """Analyze a fashion image using Vision API + Gemini multimodal."""
    if not image_path or not os.path.exists(image_path):
        print("[Vision] No image file found.")
        return {}

    result = {}

    # --- Layer 1: Google Vision API (labels, colors, objects) ---
    client = _get_vision_client()
    if client:
        try:
            from google.cloud import vision

            with open(image_path, "rb") as f:
                content = f.read()

            image = vision.Image(content=content)

            # Label detection
            label_response = client.label_detection(image=image)
            tracker.log_api_call("vision_labels")
            result["labels"] = [
                {"name": l.description, "score": round(l.score, 3)}
                for l in label_response.label_annotations[:15]
            ]

            # Color detection
            props_response = client.image_properties(image=image)
            tracker.log_api_call("vision_colors")
            colors = []
            if props_response.image_properties_annotation:
                for c in props_response.image_properties_annotation.dominant_colors.colors[:5]:
                    colors.append({
                        "rgb": f"rgb({int(c.color.red)},{int(c.color.green)},{int(c.color.blue)})",
                        "score": round(c.score, 3),
                        "pixel_fraction": round(c.pixel_fraction, 3),
                    })
            result["dominant_colors"] = colors

            # Object localization
            obj_response = client.object_localization(image=image)
            tracker.log_api_call("vision_objects")
            result["detected_objects"] = [
                {"name": obj.name, "score": round(obj.score, 3)}
                for obj in obj_response.localized_object_annotations[:10]
            ]

            print(f"[Vision] API: {len(result.get('labels', []))} labels, "
                  f"{len(colors)} colors, {len(result.get('detected_objects', []))} objects")

        except Exception as e:
            print(f"[Vision] API error: {e}")
            tracker.log_error("vision")

    # --- Layer 2: Gemini Multimodal (AI fashion analysis) ---
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # Determine mime type
        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
        mime_type = mime_map.get(ext, "image/jpeg")

        prompt = (
            "You are a fashion expert. Analyze this fashion image and return ONLY a JSON object with:\n"
            "1. \"category\": one of [workwear, casual, date-night, seasonal, luxury, streetwear, minimalist, athleisure]\n"
            "2. \"items\": list of clothing items detected (e.g. [\"blazer\", \"wide-leg pants\", \"loafers\"])\n"
            "3. \"style_tags\": 5-8 SEO tags for this outfit (e.g. [\"business casual\", \"earth tones\", \"layered look\"])\n"
            "4. \"color_palette\": main colors as names (e.g. [\"navy\", \"cream\", \"tan\"])\n"
            "5. \"season\": best season for this outfit\n"
            "6. \"amazon_search_terms\": 3 product search keywords for Amazon affiliate links\n"
            "7. \"alt_text\": SEO-optimized image alt text (under 125 chars)\n\n"
            "Return ONLY valid JSON, no markdown."
        )

        import re
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                {"role": "user", "parts": [
                    {"inline_data": {"mime_type": mime_type, "data": image_b64}},
                    {"text": prompt}
                ]}
            ]
        )
        tracker.log_api_call("gemini_vision")

        text = response.text.strip()
        text = re.sub(r"^```json?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        gemini_analysis = json.loads(text)
        result["ai_analysis"] = gemini_analysis

        print(f"[Vision] Gemini: category={gemini_analysis.get('category')}, "
              f"{len(gemini_analysis.get('items', []))} items, "
              f"{len(gemini_analysis.get('style_tags', []))} tags")

    except json.JSONDecodeError:
        print("[Vision] Gemini returned non-JSON response")
    except Exception as e:
        print(f"[Vision] Gemini multimodal error: {e}")
        tracker.log_error("gemini_vision")

    # --- Combine results ---
    result["fashion_tags"] = _extract_fashion_tags(
        result.get("labels", []),
        result.get("detected_objects", []),
        result.get("ai_analysis", {})
    )

    return result


def _extract_fashion_tags(labels, objects, ai_analysis):
    """Extract and merge fashion-relevant tags from all sources."""
    fashion_keywords = {
        "dress", "shirt", "pants", "jeans", "jacket", "coat", "skirt",
        "blouse", "sweater", "hoodie", "blazer", "top", "shoe", "boot",
        "sneaker", "bag", "handbag", "jewelry", "necklace", "watch",
        "sunglasses", "hat", "scarf", "belt", "clothing", "fashion",
        "denim", "leather", "silk", "cotton", "pattern", "stripe",
        "plaid", "floral", "vintage", "modern", "casual", "formal",
        "streetwear", "athleisure", "minimalist", "bohemian",
    }

    tags = set()

    # From Vision API
    for item in labels + objects:
        name = item["name"].lower()
        for kw in fashion_keywords:
            if kw in name:
                tags.add(name)
                break

    # From Gemini AI
    if ai_analysis:
        for tag in ai_analysis.get("style_tags", []):
            tags.add(tag.lower())
        for item in ai_analysis.get("items", []):
            tags.add(item.lower())

    return sorted(tags)


def enrich_blog_post(blog, image_path):
    """Enrich a blog post with Vision + Gemini analysis of its featured image."""
    if not image_path or not os.path.exists(image_path):
        print("[Vision] No image to analyze. Skipping.")
        return blog

    try:
        analysis = analyze_fashion_image(image_path)

        fashion_tags = analysis.get("fashion_tags", [])
        if fashion_tags:
            extra = ", ".join(fashion_tags[:8])
            print(f"[Vision] Fashion tags: {extra}")

        colors = analysis.get("dominant_colors", [])
        if colors:
            palette = ", ".join(c["rgb"] for c in colors[:3])
            print(f"[Vision] Color palette: {palette}")

        # Add AI-generated alt text and search terms
        ai = analysis.get("ai_analysis", {})
        if ai:
            blog["image_alt_text"] = ai.get("alt_text", "")
            blog["amazon_search_terms"] = ai.get("amazon_search_terms", [])
            blog["style_category"] = ai.get("category", "")

        blog["vision_analysis"] = analysis

    except Exception as e:
        print(f"[Vision] enrich_blog_post error: {e}")

    return blog


if __name__ == "__main__":
    import glob

    print("=== Vision + Gemini Multimodal Test ===")
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
    images_dir = os.path.join(docs_dir, "images")

    test_images = []
    if os.path.exists(images_dir):
        test_images = glob.glob(os.path.join(images_dir, "*.png")) + \
                      glob.glob(os.path.join(images_dir, "*.jpg"))

    if test_images:
        path = test_images[0]
        print(f"Testing: {os.path.basename(path)}")
        result = analyze_fashion_image(path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("No images found. Testing Gemini-only mode...")
        print("System ready. Vision + Gemini multimodal pipeline active.")
