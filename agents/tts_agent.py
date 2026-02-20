"""Agent H - Google Cloud TTS for TrendLoop USA shortform audio."""
import os
from google.cloud import texttospeech
from google import genai
from config import GEMINI_API_KEY, AMAZON_TAG
from safety import tracker

os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "google_creds.json"),
)

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "audio")


def generate_script(item_name, asin):
    """Generate a short-form script with Gemini."""
    link = f"https://www.amazon.com/dp/{asin}/?tag={AMAZON_TAG}"
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""You are TrendLoop USA's fashion AI agent.
Write a 30-second voiceover script for a short-form video about [{item_name}].
- Trendy, confident, Gen Z friendly tone
- Mention it's a 2026 must-have
- End with: "Link in bio to shop now"
- English only, natural spoken style
- No emojis, no hashtags, just the spoken script
- Keep it under 100 words"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    tracker.log_api_call("gemini")
    return response.text.strip(), link


def text_to_speech(text, output_path):
    """Convert text to speech using Google Cloud TTS."""
    tts_client = texttospeech.TextToSpeechClient()

    response = tts_client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text),
        voice=texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Neural2-F",
        ),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.05,
        ),
    )
    tracker.log_api_call("gcloud_tts")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(response.audio_content)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"[TTS] Audio saved: {output_path} ({size_kb:.1f} KB)")
    return output_path


def create_trend_shortform(item_name, asin):
    """Full pipeline: script generation + TTS audio."""
    print(f"[TTS] Processing: {item_name} (ASIN: {asin})")

    script, link = generate_script(item_name, asin)
    print(f"[TTS] Script: {script[:100]}...")
    print(f"[TTS] Affiliate link: {link}")

    safe_name = item_name.lower().replace(" ", "-")[:30]
    output_path = os.path.join(DOCS_DIR, f"{safe_name}.mp3")

    audio_path = text_to_speech(script, output_path)
    print(f"[TTS] Complete: {item_name}")

    return {
        "item_name": item_name,
        "asin": asin,
        "script": script,
        "affiliate_link": link,
        "audio_path": audio_path,
    }


if __name__ == "__main__":
    print("=== TrendLoop TTS Test ===")
    result = create_trend_shortform("Wide Leg Denim", "B0CH1M6X9Q")
    print(f"\nResult: {result}")
