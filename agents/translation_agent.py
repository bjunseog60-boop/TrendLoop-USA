"""Agent T - Google Cloud Translation API for multilingual posts.
Auto-translates English posts to target languages for global reach.
Uses Google Cloud credits (ADC auth).
"""
import os

os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "google_creds.json"),
)

from safety import tracker

PROJECT_ID = "fashion-money-maker"

# Target languages for fashion blog global expansion
TARGET_LANGUAGES = {
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ja": "Japanese",
    "ko": "Korean",
    "pt": "Portuguese",
    "zh-CN": "Chinese (Simplified)",
}


def _get_client():
    """Lazy-load Translation client."""
    try:
        from google.cloud import translate_v2 as translate
        return translate.Client()
    except Exception as e:
        print(f"[Translation] Client init failed: {e}")
        return None


def translate_text(text, target_lang):
    """Translate text to target language using Google Cloud Translation."""
    client = _get_client()
    if not client:
        return text  # Return original if translation unavailable

    try:
        result = client.translate(text, target_language=target_lang, format_="html")
        tracker.log_api_call("translation")
        return result["translatedText"]
    except Exception as e:
        print(f"[Translation] Error ({target_lang}): {e}")
        tracker.log_error("translation")
        return text


def translate_blog_post(html_content, slug, target_lang):
    """Translate a full blog post HTML to target language."""
    if not html_content:
        return None

    try:
        translated = translate_text(html_content, target_lang)

        docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
        lang_dir = os.path.join(docs_dir, target_lang.lower().replace("-", ""))
        os.makedirs(lang_dir, exist_ok=True)

        output_path = os.path.join(lang_dir, f"{slug}.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(translated)

        print(f"[Translation] {TARGET_LANGUAGES.get(target_lang, target_lang)}: {output_path}")
        return output_path
    except Exception as e:
        print(f"[Translation] Error ({target_lang}): {e}")
        tracker.log_error("translation")
        return None


def translate_to_all_languages(html_content, slug):
    """Translate blog post to all target languages."""
    print(f"[Translation] Translating '{slug}' to {len(TARGET_LANGUAGES)} languages...")
    results = {}

    for lang_code, lang_name in TARGET_LANGUAGES.items():
        path = translate_blog_post(html_content, slug, lang_code)
        if path:
            results[lang_code] = path

    print(f"[Translation] Complete: {len(results)}/{len(TARGET_LANGUAGES)} languages")
    return results


if __name__ == "__main__":
    print("=== Translation API Test ===")
    test_html = "<h1>Summer Fashion Trends 2026</h1><p>Wide leg jeans are the must-have item this season.</p>"
    result = translate_text(test_html, "es")
    print(f"Spanish: {result}")
