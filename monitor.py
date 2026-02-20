"""Server monitoring script for TrendLoop USA.
Checks CPU, memory, disk usage and sends alerts via webhook/email.
Runs via cron every 5 minutes.
"""
import os
import json
import shutil
import subprocess
from datetime import datetime, timezone

ALERT_THRESHOLDS = {
    "cpu_percent": 85,
    "memory_percent": 85,
    "disk_percent": 90,
}

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
ALERT_LOG = os.path.join(LOG_DIR, "monitor_alerts.log")
STATUS_FILE = os.path.join(LOG_DIR, "server_status.json")

# Slack/Discord webhook URL (set in .env)
WEBHOOK_URL = os.environ.get("MONITOR_WEBHOOK_URL", "")


def get_cpu_usage():
    """Get CPU usage percentage."""
    try:
        result = subprocess.run(
            ["top", "-bn1"],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.split("\n"):
            if "Cpu(s)" in line or "%Cpu" in line:
                # Parse idle percentage, calculate usage
                parts = line.split(",")
                for part in parts:
                    if "id" in part:
                        idle = float(part.strip().split()[0])
                        return round(100 - idle, 1)
    except Exception:
        pass
    return 0


def get_memory_usage():
    """Get memory usage percentage."""
    try:
        result = subprocess.run(
            ["free", "-m"],
            capture_output=True, text=True, timeout=10,
        )
        lines = result.stdout.strip().split("\n")
        for line in lines:
            if line.startswith("Mem:"):
                parts = line.split()
                total = int(parts[1])
                used = int(parts[2])
                return round(used / total * 100, 1) if total > 0 else 0
    except Exception:
        pass
    return 0


def get_disk_usage():
    """Get disk usage percentage."""
    try:
        usage = shutil.disk_usage("/")
        return round(usage.used / usage.total * 100, 1)
    except Exception:
        return 0


def check_process_running(name="python3"):
    """Check if a specific process is running."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", name],
            capture_output=True, text=True, timeout=5,
        )
        pids = result.stdout.strip().split("\n")
        return len([p for p in pids if p.strip()])
    except Exception:
        return 0


def send_alert(message):
    """Send alert via webhook and log."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    alert_text = f"[{timestamp}] ALERT: {message}"

    # Log to file
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(ALERT_LOG, "a", encoding="utf-8") as f:
        f.write(alert_text + "\n")

    print(alert_text)

    # Send to webhook if configured
    if WEBHOOK_URL:
        try:
            import urllib.request
            payload = json.dumps({"content": f"[TrendLoop Server] {message}"})
            req = urllib.request.Request(
                WEBHOOK_URL,
                data=payload.encode(),
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            print(f"[Monitor] Webhook failed: {e}")


def run_health_check():
    """Run full server health check."""
    cpu = get_cpu_usage()
    memory = get_memory_usage()
    disk = get_disk_usage()
    python_procs = check_process_running("python3")

    status = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu_percent": cpu,
        "memory_percent": memory,
        "disk_percent": disk,
        "python_processes": python_procs,
        "alerts": [],
    }

    # Check thresholds
    if cpu > ALERT_THRESHOLDS["cpu_percent"]:
        msg = f"High CPU usage: {cpu}% (threshold: {ALERT_THRESHOLDS['cpu_percent']}%)"
        status["alerts"].append(msg)
        send_alert(msg)

    if memory > ALERT_THRESHOLDS["memory_percent"]:
        msg = f"High memory usage: {memory}% (threshold: {ALERT_THRESHOLDS['memory_percent']}%)"
        status["alerts"].append(msg)
        send_alert(msg)

    if disk > ALERT_THRESHOLDS["disk_percent"]:
        msg = f"High disk usage: {disk}% (threshold: {ALERT_THRESHOLDS['disk_percent']}%)"
        status["alerts"].append(msg)
        send_alert(msg)

    # Save status
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2)

    # Print summary
    health = "OK" if not status["alerts"] else "WARNING"
    print(f"[Monitor] Health: {health} | CPU: {cpu}% | MEM: {memory}% | DISK: {disk}%")

    return status


if __name__ == "__main__":
    status = run_health_check()
    if status["alerts"]:
        print(f"\n{len(status['alerts'])} alert(s) triggered!")
    else:
        print("\nAll systems normal.")
