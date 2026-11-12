import os
import sys
import json
import subprocess
import smtplib

from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

from paths import (
    CONFIG_FILE,
    ENV_FILE,
    DATABASE_FILE,
    RESULTS_FILE,
    APP_DIR
)

load_dotenv(ENV_FILE)


def load_json(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def send_notification(manuscript, previous_status, new_status):
    gmail_address = os.getenv("GMAIL_ADDRESS")
    gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")
    recipient_email = os.getenv("NOTIFICATION_EMAIL")

    if not all([gmail_address, gmail_app_password, recipient_email]):
        print("Error: Missing email configuration.")
        return False

    subject = f"Manuscript Status Update: {manuscript['title']}"

    body = f"""
Manuscript Status Update:

Title: {manuscript['title']}
Manuscript ID: {manuscript['manuscript_id']}
Previous Status: {previous_status}
New Status: {new_status}
Last Checked: {manuscript['last_checked']}
"""

    msg = MIMEMultipart()
    msg["From"] = gmail_address
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    server = None

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=30)
        server.starttls()
        server.login(gmail_address, gmail_app_password)
        server.sendmail(
            gmail_address,
            recipient_email,
            msg.as_string()
        )
        print("Email sent successfully!")
        return True

    except Exception as e:
        print(f"Email failed: {type(e).__name__}: {e}")
        return False

    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                pass


def process_browser_results():
    config = load_json(CONFIG_FILE)

    if not config.get("notification_enabled", True):
        notifications_enabled = False
    else:
        notifications_enabled = True

    print("Checking ScholarOne...")

    subprocess.run(
        [sys.executable, str(APP_DIR / "fetch_browser_results.py")],
        cwd=str(APP_DIR.parent),
        check=True
    )

    new_manuscripts = load_json(RESULTS_FILE)
    manuscripts = load_json(DATABASE_FILE)

    if not isinstance(new_manuscripts, list):
        raise ValueError("Browser results must be a JSON list.")

    if not isinstance(manuscripts, list):
        raise ValueError("Manuscript database must be a JSON list.")

    if not all(isinstance(m, dict) for m in manuscripts):
        raise ValueError("Database contains invalid manuscript records.")

    existing = {m["manuscript_id"]: m for m in manuscripts}

    if not new_manuscripts:
        print("No manuscripts found. No notifications needed.")

    for item in new_manuscripts:
        manuscript_id = item["manuscript_id"]
        title = item["title"]
        new_status = item["status"]

        if not all([manuscript_id, title, new_status]):
            raise ValueError("A manuscript record has missing fields.")

        now = datetime.now(timezone.utc).isoformat()

        # First time seeing a manuscript: save its baseline status.
        if manuscript_id not in existing:
            new_record = {
                "manuscript_id": manuscript_id,
                "title": title,
                "status": new_status,
                "last_checked": now,
                "status_history": [
                    {"status": new_status, "timestamp": now}
                ]
            }

            manuscripts.append(new_record)
            existing[manuscript_id] = new_record

            print(f"New manuscript recorded: {manuscript_id}")
            continue

        manuscript = existing[manuscript_id]
        previous_status = manuscript["status"]

        manuscript["title"] = title
        manuscript["last_checked"] = now

        if previous_status == new_status:
            print(f"No status change: {manuscript_id}")
            continue

        updated_record = dict(manuscript)
        updated_record["status_history"] = list(
            manuscript.get("status_history", [])
        )

        updated_record["status"] = new_status
        updated_record["status_history"].append({
            "status": new_status,
            "timestamp": now
        })

        print(
            f"Status change detected: {manuscript_id} "
            f"({previous_status} -> {new_status})"
        )

        if not notifications_enabled:
            existing[manuscript_id] = updated_record
            index = manuscripts.index(manuscript)
            manuscripts[index] = updated_record
            print("Notification disabled. Status updated without email.")
            continue

        if send_notification(
            updated_record,
            previous_status,
            new_status
        ):
            existing[manuscript_id] = updated_record
            index = manuscripts.index(manuscript)
            manuscripts[index] = updated_record
            print(f"Status updated: {manuscript_id}")

        else:
            print(
                "Status not updated. Notification will be retried "
                f"on the next check: {manuscript_id}"
            )

    save_json(DATABASE_FILE, manuscripts)
    print("Manuscript database saved.")


def main():
    process_browser_results()


if __name__ == "__main__":
    main()
