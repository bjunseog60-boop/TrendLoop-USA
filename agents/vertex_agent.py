"""Agent V - Premium Content Pipeline for TrendLoop USA.
Uses Gemini 2.5 Pro for advanced trend analysis and Imagen 3 for image generation.
Gemini: via google-genai (API key).  Imagen 3: via Vertex AI (ADC).
"""
import os
import re
import json
from datetime import datetime, timezone

os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "google_creds.json"),
)

from google import genai
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from config import GEMINI_API_KEY, AMAZON_TAG, BLOG_BASE_URL
from safety import tracker

PROJECT_ID = "fashion-money-maker"
LOCATION = "us-central1"

vertexai.init(project=PROJECT_ID, location=LOCATION)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_FALLBACK = "gemini-2.5-pro"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Gemini 2.5 Pro - Advanced Trend Analysis
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def analyze_trends_deep(keywords):
    """Deep trend analysis using Gemini 2.5 Pro."""
    keyword_list = ", ".join(
        kw.get("keyword", str(kw)) if isinstance(kw, dict) else str(kw)
        for kw in keywords[:10]
    )

    prompt = f"""You are an elite fashion industry analyst for TrendLoop USA.

Trending keywords: {keyword_list}

Perform a deep trend analysis:

1. **TREND OVERVIEW**: Summarize the current fashion landscape based on these keywords.

2. **MICRO-TRENDS** (3-5): Identify specific micro-trends emerging from these keywords.
   For each: name, description, target demographic, longevity forecast.

3. **PRODUCT OPPORTUNITIES** (5-8): Specific Amazon product categories that align.
   For each: product type, search keyword, estimated demand level (high/medium/low).

4. **CONTENT CALENDAR**: Suggest 7 blog post titles for the next week based on these trends.

5. **SOCIAL STRATEGY**: Platform-specific posting recommendations for Pinterest, Tumblr, and TikTok.

6. **COMPETITOR GAPS**: What angles are most fashion blogs missing?

Format as structured JSON with these keys:
trend_overview, micro_trends, product_opportunities, content_calendar, social_strategy, competitor_gaps"""

    for model_name in [GEMINI_MODEL, GEMINI_FALLBACK]:
        try:
            response = gemini_client.models.generate_content(
                model=model_name, contents=prompt,
            )
            tracker.log_api_call("gemini_flash")
            text = response.text

            json_match = re.search(r"\{[\s\S]+\}", text)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    print(f"[Gemini] Trend analysis OK (model={model_name})")
                    return data
                except json.JSONDecodeError:
                    pass

            return {"raw_analysis": text}
        except Exception as e:
            print(f"[Gemini] {model_name} failed: {e}")
            if model_name == GEMINI_FALLBACK:
                tracker.log_error("gemini_flash")
                return {}
            print(f"[Gemini] Trying fallback: {GEMINI_FALLBACK}")


def write_premium_article(topic, keywords):
    """Generate premium long-form article using Gemini 2.5 Pro."""
    keyword_list = ", ".join(
        kw.get("keyword", str(kw)) if isinstance(kw, dict) else str(kw)
        for kw in keywords[:5]
    )

    prompt = f"""You are a senior fashion editor at TrendLoop USA writing a premium, in-depth article.

Topic: {topic}
Keywords: {keyword_list}
Amazon affiliate tag: {AMAZON_TAG}

Write a 1500-2000 word premium article that:
1. Opens with a compelling hook
2. Includes expert-level fashion analysis
3. References current runway shows and designer collections
4. Provides 5-8 specific product recommendations with Amazon search links
   Format: <a href="https://www.amazon.com/s?k=KEYWORD&tag={AMAZON_TAG}" target="_blank" rel="nofollow">Product Name</a>
5. Includes styling tips for different body types
6. Ends with a seasonal forecast
7. Uses H2 subheadings
8. Includes a "Shop the Look" section at the end

Output pure HTML (no markdown, no code fences). Include the affiliate disclosure at the bottom."""

    for model_name in [GEMINI_MODEL, GEMINI_FALLBACK]:
        try:
            response = gemini_client.models.generate_content(
                model=model_name, contents=prompt,
            )
            tracker.log_api_call("gemini_flash")
            print(f"[Gemini] Article OK (model={model_name})")
            return response.text
        except Exception as e:
            print(f"[Gemini] {model_name} failed: {e}")
            if model_name == GEMINI_FALLBACK:
                tracker.log_error("gemini_flash")
                return ""
            print(f"[Gemini] Trying fallback: {GEMINI_FALLBACK}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Imagen 3 - High Quality Image Generation (Vertex AI)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_fashion_image(prompt_text, output_path):
    """Generate a fashion image using Imagen 3 via Vertex AI."""
    try:
        model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")

        response = model.generate_images(
            prompt=prompt_text,
            number_of_images=1,
            aspect_ratio="16:9",
            safety_filter_level="block_few",
        )
        tracker.log_api_call("vertex_imagen")

        if response.images:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            response.images[0].save(location=output_path)
            size_kb = os.path.getsize(output_path) / 1024
            print(f"[Imagen3] Image saved: {output_path} ({size_kb:.1f} KB)")
            return output_path
        else:
            print("[Imagen3] No image generated.")
            return None
    except Exception as e:
        print(f"[Imagen3] Error: {e}")
        tracker.log_error("vertex_imagen")
        return None


def generate_blog_images(title, keywords, slug):
    """Generate featured image + Pinterest pin for a blog post."""
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
    images_dir = os.path.join(docs_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    keyword_str = ", ".join(
        kw.get("keyword", str(kw)) if isinstance(kw, dict) else str(kw)
        for kw in keywords[:3]
    )

    # Featured image
    featured_prompt = (
        f"Editorial fashion photography for article: {title}. "
        f"Featuring: {keyword_str}. "
        f"Professional studio lighting, high-end magazine aesthetic, "
        f"clean composition, no text overlay, photorealistic."
    )

    featured_path = os.path.join(images_dir, f"{slug}-featured.png")
    featured = generate_fashion_image(featured_prompt, featured_path)

    # Pinterest pin image (vertical)
    pin_prompt = (
        f"Pinterest-style vertical fashion mood board for: {title}. "
        f"Aesthetic flat lay with {keyword_str}, "
        f"minimalist background, soft natural lighting, aspirational lifestyle."
    )

    pin_path = os.path.join(images_dir, f"{slug}-pin.png")
    pin = generate_fashion_image(pin_prompt, pin_path)

    return {"featured": featured, "pin": pin}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Combined Pipeline
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_vertex_pipeline(keywords):
    """Full premium pipeline: analyze + write + generate images."""
    print("[Premium] Starting premium content pipeline (Gemini 2.5 Pro + Imagen 3)...")

    # Step 1: Deep trend analysis
    print("[Premium] Step 1: Deep trend analysis with Gemini 2.5 Pro...")
    analysis = analyze_trends_deep(keywords)

    # Get content calendar suggestion
    calendar = analysis.get("content_calendar", [])
    topic = calendar[0] if calendar else "Today's Hottest Fashion Trends"
    if isinstance(topic, dict):
        topic = topic.get("title", str(topic))

    # Step 2: Premium article
    print(f"[Premium] Step 2: Writing premium article: {topic}")
    article_html = write_premium_article(topic, keywords)

    if not article_html:
        print("[Premium] Article generation failed.")
        return {}

    # Generate slug
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug_base = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:50]
    slug = f"{today}-{slug_base}"

    # Step 3: Generate images with Imagen 3
    print("[Premium] Step 3: Generating images with Imagen 3...")
    images = generate_blog_images(topic, keywords, slug)

    # Save analysis
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    analysis_path = os.path.join(data_dir, f"{today}-analysis.json")
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    print(f"[Premium] Analysis saved: {analysis_path}")

    return {
        "topic": topic,
        "slug": slug,
        "article_html": article_html,
        "analysis": analysis,
        "images": images,
    }


if __name__ == "__main__":
    print("=== Premium Pipeline Test (Gemini 2.5 Pro + Imagen 3) ===")

    test_keywords = [
        {"keyword": "wide leg denim 2026"},
        {"keyword": "minimalist jewelry"},
        {"keyword": "oversized blazer women"},
    ]

    result = run_vertex_pipeline(test_keywords)
    if result:
        print(f"\nTopic: {result['topic']}")
        print(f"Slug: {result['slug']}")
        print(f"Article length: {len(result.get('article_html', ''))} chars")
        print(f"Images: {result.get('images', {})}")
    else:
        print("Pipeline failed.")
