#!/usr/bin/env python3
"""TrendLoop USA Master Agent - 24/7 systemd daemon.

Schedules:
  - Every 6h:  TrendLoop + StyleMeDaily content generation
  - Every 1h:  SEO check + sitemap update
  - Every 12h: Pinterest + Twitter auto-posting
  - Auto-restart on errors
  - Full logging to /home/ubuntu/TrendLoop-USA/logs/master_agent.log

Runs as: systemctl start trendloop-master
"""
import os
import sys
import io
import time
import json
import glob
import signal
import traceback
import threading
from datetime import datetime, timezone, timedelta

# Force UTF-8 only when running interactively (not under systemd)
if hasattr(sys.stdout, "buffer") and sys.stdout.writable() and os.isatty(sys.stdout.fileno() if hasattr(sys.stdout, 'fileno') else -1):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

# Project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

# Load .env
env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "master_agent.log")
STATE_FILE = os.path.join(LOG_DIR, "master_state.json")

# Schedule intervals (seconds)
CONTENT_INTERVAL = 6 * 3600      # 6 hours
SEO_INTERVAL = 1 * 3600          # 1 hour
SOCIAL_INTERVAL = 12 * 3600      # 12 hours
HEARTBEAT_INTERVAL = 300          # 5 minutes

running = True


def log(msg, level="INFO"):
    """Write to log file and optionally stdout."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] [{level}] {msg}"
    # Write to file first (always works)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    # Print to stdout (may fail under systemd)
    try:
        print(line, flush=True)
    except Exception:
        pass


def load_state():
    """Load last-run timestamps."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_state(state):
    """Save last-run timestamps."""
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log(f"State save error: {e}", "WARN")


def seconds_since(iso_str):
    """Seconds elapsed since an ISO timestamp."""
    if not iso_str:
        return float("inf")
    try:
        last = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - last).total_seconds()
    except Exception:
        return float("inf")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# TASK 1: Content Generation (every 6 hours)
# ============================================================
def task_content_generation():
    """Generate TrendLoop posts + sync to StyleMeDaily."""
    log("=" * 50)
    log("TASK: Content Generation (TrendLoop + StyleMeDaily)")
    log("=" * 50)

    generated = 0

    # --- Batch Publisher: Publish pre-generated posts ---
    try:
        from batch_publisher import publish_todays_posts
        batch_count = publish_todays_posts()
        if batch_count > 0:
            log(f"Batch Publisher: {batch_count} pre-generated posts published")
    except Exception as e:
        try:
            log(f"Batch publisher: {e}", "WARN")
        except Exception:
            pass

    # --- TrendLoop: Content Scheduler (5 posts/day) ---
    results = []
    try:
        from agents.content_scheduler import run_daily_schedule
        results = run_daily_schedule() or []
        generated = len(results)
        log(f"TrendLoop: {generated} posts generated")
    except Exception as e:
        try:
            log(f"TrendLoop content error: {e}", "ERROR")
        except Exception:
            pass

    # --- Google Indexing API: Submit new posts ---
    if generated > 0:
        try:
            from agents.indexing_agent import notify_url_updated
            for r in (results or []):
                slug = r.get("slug", "") if isinstance(r, dict) else str(r)
                if slug:
                    notify_url_updated(slug)
        except Exception as e:
            log(f"Indexing error: {e}", "WARN")

    # --- StyleMeDaily Sync ---
    try:
        from data.stylemedaily_sync import sync_trendloop_to_stylemedaily
        synced = sync_trendloop_to_stylemedaily()
        log(f"StyleMeDaily: {len(synced)} guides synced")
    except ImportError:
        log("StyleMeDaily sync module not found. Skipping.", "WARN")
    except Exception as e:
        log(f"StyleMeDaily sync error: {e}", "ERROR")

    log(f"Content generation complete: {generated} posts")
    return generated


# ============================================================
# TASK 2: SEO Check + Sitemap Update (every 1 hour)
# ============================================================
def task_seo_update():
    """Update sitemap, index, RSS feed."""
    log("=" * 50)
    log("TASK: SEO Check + Sitemap Update")
    log("=" * 50)

    try:
        from agents.marketer import update_sitemap
        from agents.index_builder import rebuild_index
        from agents.rss_builder import rebuild_rss

        docs_dir = os.path.join(BASE_DIR, "docs")
        existing = glob.glob(os.path.join(docs_dir, "*.html"))
        all_slugs = [
            os.path.splitext(os.path.basename(f))[0]
            for f in existing if os.path.basename(f) != "index.html"
        ]

        update_sitemap(all_slugs)
        log(f"Sitemap updated: {len(all_slugs)} URLs")

        rebuild_index()
        log("Index page rebuilt")

        rebuild_rss()
        log("RSS feed rebuilt")

    except Exception as e:
        log(f"SEO update error: {e}", "ERROR")
        log(traceback.format_exc(), "ERROR")

    # --- Analytics-driven topic suggestion ---
    try:
        from agents.analytics_data_agent import generate_smart_topics
        report = generate_smart_topics()
        if report:
            log(f"Analytics: focus categories = {report.get('suggested_focus', [])}")
    except Exception as e:
        log(f"Analytics check: {e}", "WARN")

    log("SEO update complete")


# ============================================================
# TASK 3: Social Media Posting (every 12 hours)
# ============================================================
def task_social_posting():
    """Post latest content to Pinterest + Twitter."""
    log("=" * 50)
    log("TASK: Social Media Posting (Pinterest + Twitter)")
    log("=" * 50)

    # Find most recent post
    docs_dir = os.path.join(BASE_DIR, "docs")
    html_files = sorted(
        glob.glob(os.path.join(docs_dir, "*.html")),
        key=os.path.getmtime, reverse=True
    )

    recent_posts = []
    for f in html_files[:3]:
        name = os.path.basename(f)
        if name == "index.html":
            continue
        slug = os.path.splitext(name)[0]

        # Extract title from file
        title = slug
        try:
            with open(f, "r", encoding="utf-8") as fh:
                content = fh.read(2000)
            import re
            tm = re.search(r"<title>(.*?)(?:\||<)", content)
            if tm:
                title = tm.group(1).strip()
        except Exception:
            pass

        recent_posts.append({"slug": slug, "title": title, "file_path": f})

    if not recent_posts:
        log("No posts found for social sharing")
        return

    posted = 0

    for post in recent_posts[:2]:
        # --- Twitter ---
        try:
            from agents.marketer import post_to_twitter
            summary = f"{post['title']} - Read more on TrendLoop USA!"
            ok = post_to_twitter(summary, post["slug"])
            if ok:
                log(f"Twitter: posted '{post['title'][:50]}'")
                posted += 1
        except Exception as e:
            log(f"Twitter error: {e}", "WARN")

        # --- Pinterest ---
        try:
            from agents.pinterest import post_blog_to_pinterest
            blog = {"title": post["title"], "slug": post["slug"], "file_path": post["file_path"]}
            ok = post_blog_to_pinterest(blog, [])
            if ok:
                log(f"Pinterest: pinned '{post['title'][:50]}'")
                posted += 1
        except Exception as e:
            log(f"Pinterest error: {e}", "WARN")

    # --- Amazon Fashion Shorts ---
    try:
        from agents.amazon_shorts import generate_shorts_content
        shorts = generate_shorts_content()
        shorts_count = len(shorts) if shorts else 0
        log(f"Amazon Shorts: {shorts_count} scripts generated")
    except Exception as e:
        try:
            log(f"Amazon Shorts error: {e}", "WARN")
        except Exception:
            pass

    log(f"Social posting complete: {posted} posts shared")


# ============================================================
# TASK 4: Health Check / Heartbeat (every 5 minutes)
# ============================================================
def task_heartbeat():
    """Quick health check + heartbeat ping."""
    try:
        import shutil
        cpu_idle = 0
        try:
            import subprocess
            result = subprocess.run(
                ["top", "-bn1"], capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.split("\n"):
                if "Cpu" in line:
                    for part in line.split(","):
                        if "id" in part:
                            cpu_idle = float(part.strip().split()[0])
                            break
                    break
        except Exception:
            pass

        cpu = round(100 - cpu_idle, 1)
        disk = shutil.disk_usage("/")
        disk_pct = round(disk.used / disk.total * 100, 1)

        # Only log if something is concerning
        if cpu > 70 or disk_pct > 85:
            log(f"Heartbeat: CPU={cpu}% DISK={disk_pct}%", "WARN")

    except Exception:
        pass


# ============================================================
# MAIN LOOP
# ============================================================
def signal_handler(signum, frame):
    global running
    log(f"Received signal {signum}. Shutting down gracefully...")
    running = False


def main():
    global running

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    log("=" * 60)
    log("  TrendLoop USA Master Agent - Starting")
    log(f"  PID: {os.getpid()}")
    log(f"  Base: {BASE_DIR}")
    log("=" * 60)

    state = load_state()
    cycle = 0

    while running:
        cycle += 1
        now = datetime.now(timezone.utc)
        hour = now.hour

        try:
            # --- Content Generation: every 6 hours ---
            elapsed = seconds_since(state.get("last_content"))
            if elapsed >= CONTENT_INTERVAL:
                log(f"[Cycle {cycle}] Content generation due (last: {state.get('last_content', 'never')})")
                try:
                    task_content_generation()
                    state["last_content"] = now_iso()
                    state["last_content_status"] = "ok"
                except Exception as e:
                    log(f"Content generation FAILED: {e}", "ERROR")
                    log(traceback.format_exc(), "ERROR")
                    state["last_content_status"] = f"error: {str(e)[:100]}"
                save_state(state)

            # --- SEO Update: every 1 hour ---
            elapsed = seconds_since(state.get("last_seo"))
            if elapsed >= SEO_INTERVAL:
                log(f"[Cycle {cycle}] SEO update due")
                try:
                    task_seo_update()
                    state["last_seo"] = now_iso()
                    state["last_seo_status"] = "ok"
                except Exception as e:
                    log(f"SEO update FAILED: {e}", "ERROR")
                    state["last_seo_status"] = f"error: {str(e)[:100]}"
                save_state(state)

            # --- Social Posting: every 12 hours ---
            elapsed = seconds_since(state.get("last_social"))
            if elapsed >= SOCIAL_INTERVAL:
                log(f"[Cycle {cycle}] Social posting due")
                try:
                    task_social_posting()
                    state["last_social"] = now_iso()
                    state["last_social_status"] = "ok"
                except Exception as e:
                    log(f"Social posting FAILED: {e}", "ERROR")
                    state["last_social_status"] = f"error: {str(e)[:100]}"
                save_state(state)

            # --- Heartbeat: every 5 minutes ---
            elapsed = seconds_since(state.get("last_heartbeat"))
            if elapsed >= HEARTBEAT_INTERVAL:
                task_heartbeat()
                state["last_heartbeat"] = now_iso()
                state["cycles"] = cycle
                save_state(state)

        except Exception as e:
            log(f"[Cycle {cycle}] Unexpected error: {e}", "ERROR")
            log(traceback.format_exc(), "ERROR")
            # Don't crash - sleep and retry
            time.sleep(60)
            continue

        # Sleep 60 seconds between checks
        for _ in range(60):
            if not running:
                break
            time.sleep(1)

    log("Master Agent stopped gracefully.")
    save_state(state)


if __name__ == "__main__":
    main()
