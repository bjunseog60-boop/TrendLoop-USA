"""Agent Vision - Google Cloud Vision API for fashion image analysis.
Extracts product labels, colors, and style attributes from images.
Uses Google Cloud credits (ADC auth).
"""
import os
import json

os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "google_creds.json"),
)

from safety import tracker


def _get_client():
    """Lazy-load Vision client."""
    try:
        from google.cloud import vision
        return vision.ImageAnnotatorClient()
    except Exception as e:
        print(f"[Vision] Client init failed: {e}")
        return None


def analyze_fashion_image(image_path):
    """Analyze a fashion image and extract product details."""
    client = _get_client()
    if not client:
        return {}

    try:
        from google.cloud import vision

        with open(image_path, "rb") as f:
            content = f.read()

        image = vision.Image(content=content)

        # Label detection
        label_response = client.label_detection(image=image)
        tracker.log_api_call("vision_labels")
        labels = [
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

        # Object localization
        obj_response = client.object_localization(image=image)
        tracker.log_api_call("vision_objects")
        objects = [
            {"name": obj.name, "score": round(obj.score, 3)}
            for obj in obj_response.localized_object_annotations[:10]
        ]

        result = {
            "labels": labels,
            "dominant_colors": colors,
            "detected_objects": objects,
            "fashion_tags": _extract_fashion_tags(labels, objects),
        }

        print(f"[Vision] Analyzed: {os.path.basename(image_path)}")
        print(f"[Vision] Labels: {len(labels)}, Colors: {len(colors)}, Objects: {len(objects)}")
        return result
    except Exception as e:
        print(f"[Vision] Analysis error: {e}")
        tracker.log_error("vision")
        return {}


def _extract_fashion_tags(labels, objects):
    """Extract fashion-relevant tags from Vision API results."""
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
    for item in labels + objects:
        name = item["name"].lower()
        for kw in fashion_keywords:
            if kw in name:
                tags.add(name)
                break

    return sorted(tags)


def enrich_blog_post(blog, image_path):
    """Enrich a blog post with Vision API analysis of its featured image."""
    if not image_path or not os.path.exists(image_path):
        print("[Vision] No image to analyze. Skipping.")
        return blog

    try:
        analysis = analyze_fashion_image(image_path)

        fashion_tags = analysis.get("fashion_tags", [])
        if fashion_tags:
            extra = ", ".join(fashion_tags[:5])
            print(f"[Vision] Fashion tags added: {extra}")

        colors = analysis.get("dominant_colors", [])
        if colors:
            palette = ", ".join(c["rgb"] for c in colors[:3])
            print(f"[Vision] Color palette: {palette}")

        blog["vision_analysis"] = analysis
    except Exception as e:
        print(f"[Vision] enrich_blog_post error: {e}")

    return blog


if __name__ == "__main__":
    print("=== Vision API Test ===")
    test_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "images")
    if os.path.exists(test_dir):
        images = [f for f in os.listdir(test_dir) if f.endswith((".png", ".jpg"))]
        if images:
            path = os.path.join(test_dir, images[0])
            result = analyze_fashion_image(path)
            print(json.dumps(result, indent=2))
        else:
            print("No images found to test.")
    else:
        print(f"Image directory not found. System continues without Vision.")
