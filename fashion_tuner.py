#!/usr/bin/env python3
"""Vertex AI Fashion Model Tuner - Custom fine-tuned Gemini for TrendLoop USA.

Creates a fashion-specialized model by:
1. Extracting training data from existing high-quality posts
2. Generating synthetic training pairs via Gemini
3. Fine-tuning Gemini 2.5 Flash on our site's style/voice
4. Deploying the tuned model for content generation

Usage:
  python3 fashion_tuner.py --prepare   # Prepare training data
  python3 fashion_tuner.py --tune      # Submit tuning job
  python3 fashion_tuner.py --status    # Check tuning job status
  python3 fashion_tuner.py --test      # Test tuned model
"""
import os
import sys
import io
import re
import json
import glob
from datetime import datetime, timezone

if hasattr(sys.stdout, "buffer"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS",
    os.path.join(os.path.dirname(__file__), "google_creds.json"),
)

from config import GEMINI_API_KEY, AMAZON_TAG, BLOG_BASE_URL
from safety import tracker
from google import genai

client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-2.5-flash"

PROJECT_ID = "fashion-money-maker"
LOCATION = "us-central1"
GCS_BUCKET = f"gs://{PROJECT_ID}-training"

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TRAINING_FILE = os.path.join(DATA_DIR, "fashion_training.jsonl")
TUNED_MODEL_FILE = os.path.join(DATA_DIR, "tuned_model_id.txt")

# Our brand voice and style guidelines
BRAND_STYLE = """TrendLoop USA Brand Voice:
- Expert, authoritative but approachable fashion editor
- Target audience: US women 20-40
- Tone: confident, knowledgeable, trend-aware
- Always include practical styling advice
- Naturally weave in Amazon affiliate product recommendations
- Use SEO-optimized headings with long-tail keywords
- Include FAQ section for featured snippets
- Write 1200-1800 words per article
- No em dashes, no excessive exclamation marks
- Professional editorial quality, not generic blog content"""


def extract_post_content(html_path):
    """Extract clean text content from HTML post."""
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Extract title
    title_match = re.search(r"<title>(.*?)(?:\||<)", html)
    title = title_match.group(1).strip() if title_match else ""

    # Extract keyword
    kw_match = re.search(r'name="keywords" content="([^"]*)"', html)
    keyword = kw_match.group(1).split(",")[0].strip() if kw_match else ""

    # Extract article body
    article_match = re.search(r"<article>(.*?)</article>", html, re.DOTALL)
    if article_match:
        body = article_match.group(1)
    else:
        body_match = re.search(r"<body>(.*?)</body>", html, re.DOTALL)
        body = body_match.group(1) if body_match else html

    # Strip HTML tags for text
    text = re.sub(r"<[^>]+>", " ", body)
    text = re.sub(r"\s+", " ", text).strip()

    return {
        "title": title,
        "keyword": keyword,
        "text": text[:5000],
        "html": body[:8000],
    }


def prepare_training_data():
    """Prepare training data from existing posts + synthetic examples."""
    print("=" * 60)
    print("  Phase 1: Preparing Training Data")
    print("=" * 60)

    training_examples = []

    # --- Extract from existing posts ---
    html_files = glob.glob(os.path.join(DOCS_DIR, "*.html"))
    posts = []
    for f in html_files:
        if os.path.basename(f) == "index.html":
            continue
        post = extract_post_content(f)
        if post["title"] and len(post["text"]) > 500:
            posts.append(post)

    print(f"[Tuner] Found {len(posts)} existing posts")

    # Create input-output training pairs from existing posts
    for post in posts:
        example = {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Write a premium SEO-optimized fashion article.\n"
                        f"Title: {post['title']}\n"
                        f"Target keyword: {post['keyword']}\n"
                        f"Amazon tag: {AMAZON_TAG}\n\n"
                        f"Requirements: 1200-1800 words, expert editorial voice, "
                        f"include Amazon affiliate links, FAQ section, "
                        f"Schema.org markup ready.\n\n"
                        f"{BRAND_STYLE}"
                    )
                },
                {
                    "role": "model",
                    "content": post["html"]
                }
            ]
        }
        training_examples.append(example)

    # --- Generate synthetic training examples ---
    print("[Tuner] Generating synthetic training examples...")

    synthetic_topics = [
        ("How to Build a Capsule Wardrobe for Spring 2026", "capsule wardrobe spring 2026"),
        ("The Ultimate Guide to Workwear Blazers for Women", "women workwear blazers"),
        ("Date Night Outfit Ideas That Will Turn Heads in 2026", "date night outfit ideas 2026"),
        ("Best Budget-Friendly Summer Dresses Under $50", "summer dresses under 50"),
        ("Athleisure to Office: How to Style Sneakers Professionally", "style sneakers for work"),
        ("Minimalist Fashion Essentials Every Woman Needs", "minimalist fashion essentials"),
        ("How to Accessorize a Little Black Dress for Any Occasion", "accessorize little black dress"),
        ("Sustainable Fashion Brands Worth Your Investment in 2026", "sustainable fashion brands 2026"),
        ("Petite Style Guide: Dressing Tips to Look Taller", "petite style guide tips"),
        ("The Return of Y2K Fashion: How to Wear It in 2026", "y2k fashion trends 2026"),
        ("Wedding Guest Dress Code: What to Wear to Every Type", "wedding guest dress code"),
        ("Street Style Trends Dominating Fashion Weeks 2026", "street style trends 2026"),
        ("How to Mix High and Low Fashion Like a Pro", "mix high low fashion"),
        ("The Best Jeans for Every Body Type: A Complete Guide", "best jeans body type guide"),
        ("Transitional Outfit Ideas: Summer to Fall Wardrobe", "summer to fall transition outfits"),
    ]

    for title, keyword in synthetic_topics:
        prompt = (
            f"You are a senior fashion editor at TrendLoop USA.\n\n"
            f"Write a premium SEO-optimized article.\n"
            f"Title: {title}\n"
            f"Target keyword: {keyword}\n"
            f"Amazon tag: {AMAZON_TAG}\n\n"
            f"Requirements:\n"
            f"1. 1200-1800 words, engaging editorial voice\n"
            f"2. Use the target keyword 4-6 times naturally\n"
            f"3. Include 5-8 Amazon product links\n"
            f"4. Use H2 subheadings with related keywords\n"
            f"5. Include FAQ section (3 questions)\n"
            f"6. Practical, actionable advice\n"
            f"7. Output pure HTML.\n\n"
            f"{BRAND_STYLE}"
        )

        try:
            resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            tracker.log_api_call("gemini_flash")
            output = resp.text.strip()
            output = re.sub(r"^```html?\s*", "", output)
            output = re.sub(r"\s*```$", "", output)

            if len(output) > 500:
                example = {
                    "messages": [
                        {"role": "user", "content": prompt},
                        {"role": "model", "content": output}
                    ]
                }
                training_examples.append(example)
                print(f"  [+] {title[:50]}... ({len(output)} chars)")
            else:
                print(f"  [-] {title[:50]}... (too short, skipped)")

        except Exception as e:
            print(f"  [!] {title[:50]}... Error: {e}")

    # Save training data as JSONL
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TRAINING_FILE, "w", encoding="utf-8") as f:
        for ex in training_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"\n[Tuner] Training data saved: {TRAINING_FILE}")
    print(f"[Tuner] Total examples: {len(training_examples)}")
    print(f"[Tuner] From existing posts: {len(posts)}")
    print(f"[Tuner] Synthetic examples: {len(training_examples) - len(posts)}")

    return training_examples


def upload_to_gcs():
    """Upload training data to Google Cloud Storage."""
    print("\n[Tuner] Uploading training data to GCS...")

    try:
        from google.cloud import storage

        gcs_client = storage.Client(project=PROJECT_ID)

        bucket_name = f"{PROJECT_ID}-training"

        # Create bucket if not exists
        try:
            bucket = gcs_client.get_bucket(bucket_name)
        except Exception:
            bucket = gcs_client.create_bucket(bucket_name, location=LOCATION)
            print(f"[Tuner] Created GCS bucket: {bucket_name}")

        # Upload training file
        blob = bucket.blob("fashion_training.jsonl")
        blob.upload_from_filename(TRAINING_FILE)
        gcs_uri = f"gs://{bucket_name}/fashion_training.jsonl"
        print(f"[Tuner] Uploaded: {gcs_uri}")
        return gcs_uri

    except ImportError:
        print("[Tuner] google-cloud-storage not installed. Installing...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install",
                        "--break-system-packages", "google-cloud-storage"],
                       capture_output=True)
        return upload_to_gcs()
    except Exception as e:
        print(f"[Tuner] GCS upload error: {e}")
        return None


def submit_tuning_job(gcs_uri=None):
    """Submit a supervised fine-tuning job to Vertex AI."""
    print("\n" + "=" * 60)
    print("  Phase 2: Submitting Tuning Job")
    print("=" * 60)

    if not gcs_uri:
        gcs_uri = f"{GCS_BUCKET}/fashion_training.jsonl"

    try:
        import vertexai
        from vertexai.tuning import sft

        vertexai.init(project=PROJECT_ID, location=LOCATION)

        tuning_job = sft.train(
            source_model="gemini-2.0-flash-001",
            train_dataset=gcs_uri,
            tuned_model_display_name=f"trendloop-fashion-v1-{datetime.now().strftime('%Y%m%d')}",
            epochs=3,
            adapter_size=4,
            learning_rate_multiplier=1.0,
        )

        print(f"[Tuner] Tuning job submitted!")
        print(f"[Tuner] Job name: {tuning_job.name}")
        print(f"[Tuner] Status: {tuning_job.state}")

        # Save job info
        job_info = {
            "job_name": tuning_job.name,
            "source_model": "gemini-2.0-flash-001",
            "training_data": gcs_uri,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "status": str(tuning_job.state),
        }
        with open(os.path.join(DATA_DIR, "tuning_job.json"), "w") as f:
            json.dump(job_info, f, indent=2)

        return tuning_job

    except Exception as e:
        print(f"[Tuner] Tuning job error: {e}")
        return None


def check_tuning_status():
    """Check the status of a running tuning job."""
    job_path = os.path.join(DATA_DIR, "tuning_job.json")
    if not os.path.exists(job_path):
        print("[Tuner] No tuning job found. Run --tune first.")
        return None

    with open(job_path) as f:
        job_info = json.load(f)

    try:
        import vertexai
        from vertexai.tuning import sft

        vertexai.init(project=PROJECT_ID, location=LOCATION)

        job = sft.SupervisedTuningJob(job_info["job_name"])

        print(f"[Tuner] Job: {job.name}")
        print(f"[Tuner] Status: {job.state}")

        if hasattr(job, "tuned_model_name") and job.tuned_model_name:
            print(f"[Tuner] Tuned model: {job.tuned_model_name}")
            # Save tuned model ID
            with open(TUNED_MODEL_FILE, "w") as f:
                f.write(job.tuned_model_name)
            print(f"[Tuner] Model ID saved to {TUNED_MODEL_FILE}")

            # Update job info
            job_info["tuned_model"] = job.tuned_model_name
            job_info["status"] = str(job.state)
            with open(job_path, "w") as f:
                json.dump(job_info, f, indent=2)

        if hasattr(job, "tuned_model_endpoint_name") and job.tuned_model_endpoint_name:
            print(f"[Tuner] Endpoint: {job.tuned_model_endpoint_name}")

        return job

    except Exception as e:
        print(f"[Tuner] Status check error: {e}")
        return None


def get_tuned_model_id():
    """Get the tuned model ID if available."""
    if os.path.exists(TUNED_MODEL_FILE):
        with open(TUNED_MODEL_FILE) as f:
            return f.read().strip()
    return None


def generate_with_tuned_model(title, keyword):
    """Generate content using the tuned model."""
    tuned_model = get_tuned_model_id()

    if not tuned_model:
        print("[Tuner] No tuned model available. Using base model with enhanced prompt.")
        tuned_model = GEMINI_MODEL

    prompt = (
        f"Write a premium SEO-optimized fashion article.\n"
        f"Title: {title}\n"
        f"Target keyword: {keyword}\n"
        f"Amazon tag: {AMAZON_TAG}\n\n"
        f"Requirements: 1200-1800 words, expert editorial voice, "
        f"include 5-8 Amazon affiliate product links, "
        f"H2 subheadings, FAQ section (3 questions), "
        f"practical styling advice.\n\n"
        f"{BRAND_STYLE}\n\n"
        f"Output pure HTML only."
    )

    try:
        # Try tuned model via Vertex AI
        if tuned_model != GEMINI_MODEL and "projects/" in tuned_model:
            import vertexai
            from vertexai.generative_models import GenerativeModel

            vertexai.init(project=PROJECT_ID, location=LOCATION)
            model = GenerativeModel(tuned_model)
            response = model.generate_content(prompt)
            tracker.log_api_call("tuned_model")
            print(f"[Tuner] Generated with tuned model: {len(response.text)} chars")
            return response.text

        # Fallback to base model via API key
        resp = client.models.generate_content(model=tuned_model, contents=prompt)
        tracker.log_api_call("gemini_flash")
        return resp.text

    except Exception as e:
        print(f"[Tuner] Generation error: {e}")
        # Ultimate fallback
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        tracker.log_api_call("gemini_flash")
        return resp.text


def test_tuned_model():
    """Test the tuned model with a sample prompt."""
    print("\n" + "=" * 60)
    print("  Testing Tuned Model")
    print("=" * 60)

    test_title = "How to Style Oversized Blazers for Every Occasion in 2026"
    test_keyword = "how to style oversized blazers 2026"

    tuned_model = get_tuned_model_id()
    if tuned_model:
        print(f"[Tuner] Using tuned model: {tuned_model}")
    else:
        print("[Tuner] No tuned model yet. Testing with enhanced base model.")

    result = generate_with_tuned_model(test_title, test_keyword)

    if result:
        # Clean code fences
        result = re.sub(r"^```html?\s*", "", result)
        result = re.sub(r"\s*```$", "", result)
        print(f"[Tuner] Generated: {len(result)} chars")
        print(f"[Tuner] First 300 chars:\n{result[:300]}...")

        # Save test output
        test_path = os.path.join(DATA_DIR, "tuned_model_test.html")
        with open(test_path, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"[Tuner] Test output saved: {test_path}")
    else:
        print("[Tuner] Generation failed")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 fashion_tuner.py --prepare   # Prepare training data")
        print("  python3 fashion_tuner.py --tune      # Submit tuning job")
        print("  python3 fashion_tuner.py --status    # Check tuning status")
        print("  python3 fashion_tuner.py --test      # Test tuned model")
        print("  python3 fashion_tuner.py --all       # Full pipeline")
        sys.exit(0)

    action = sys.argv[1]

    if action == "--prepare":
        prepare_training_data()

    elif action == "--tune":
        if not os.path.exists(TRAINING_FILE):
            print("[Tuner] No training data. Preparing first...")
            prepare_training_data()
        gcs_uri = upload_to_gcs()
        if gcs_uri:
            submit_tuning_job(gcs_uri)

    elif action == "--status":
        check_tuning_status()

    elif action == "--test":
        test_tuned_model()

    elif action == "--all":
        print("[Tuner] Full pipeline: prepare -> upload -> tune")
        prepare_training_data()
        gcs_uri = upload_to_gcs()
        if gcs_uri:
            job = submit_tuning_job(gcs_uri)
            if job:
                print("\n[Tuner] Tuning job submitted. Check status with --status")
                print("[Tuner] Tuning typically takes 1-3 hours.")

    else:
        print(f"Unknown action: {action}")
