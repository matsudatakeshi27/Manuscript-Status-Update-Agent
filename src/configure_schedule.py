import json
import math
import os
import plistlib
import subprocess
import sys

from paths import (
    CONFIG_FILE,
    DATA_DIR,
    LOG_DIR,
    LOG_FILE,
    ERROR_LOG_FILE,
    APP_DIR
)

LABEL = "com.scholarone.monitor.downloadable"

PLIST_FILE = (
    DATA_DIR / f"{LABEL}.plist"
)

def main():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    hours = config.get("monitoring_interval_hours")

    if isinstance(hours, bool) or not isinstance(hours, (int, float)):
        raise ValueError("Monitoring interval must be a number.")

    if not math.isfinite(hours) or hours <= 0:
        raise ValueError("Monitoring interval must be positive.")

    interval_seconds = round(hours * 3600)

    if interval_seconds < 60:
        raise ValueError("Minimum interval is 1 minute.")

    plist = {
        "Label": LABEL,
        "ProgramArguments": [
            sys.executable,
            str(APP_DIR / "monitor.py")
        ],
        "WorkingDirectory": str(APP_DIR.parent),
        "StartInterval": interval_seconds,
        "EnvironmentVariables": {
            "PATH": (
                "/opt/homebrew/bin:"
                "/opt/homebrew/opt/node/bin:"
                "/usr/bin:/bin:/usr/sbin:/sbin"
            )
        },
        "StandardOutPath": str(LOG_FILE),
        "StandardErrorPath": str(ERROR_LOG_FILE)
    }

    with open(PLIST_FILE, "wb") as f:
        plistlib.dump(plist, f)

    print(f"Monitoring interval: {hours} hours")
    print(f"Interval in seconds: {interval_seconds}")
    print(f"LaunchAgent saved: {PLIST_FILE}")

    domain = f"gui/{os.getuid()}"

    subprocess.run(
        ["/bin/launchctl", "bootout", domain, str(PLIST_FILE)],
        capture_output=True,
        text=True
    )

    result = subprocess.run(
        ["/bin/launchctl", "bootstrap", domain, str(PLIST_FILE)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Could not load LaunchAgent: {result.stderr}"
        )

    print("LaunchAgent successfully loaded.")
    print("Automatic monitoring schedule is now active.")


if __name__ == "__main__":
    main()
