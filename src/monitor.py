
import os
import sys
import json
import subprocess
import smtplib

from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv
from auto_login import auto_login

from paths import (
    CONFIG_FILE,
    ENV_FILE,
    DATABASE_FILE,
    RESULTS_FILE,
    APP_DIR
)


load_dotenv(ENV_FILE)

JOURNAL_NAME = "Marketing Science"


def load_json(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def parse_status_date(date_string):
    """Convert ScholarOne dates such as 26-Oct-2026 into date objects."""

    if not date_string:
        return None

    formats = [
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%Y-%m-%d"
    ]

    for date_format in formats:
        try:
            return datetime.strptime(
                date_string.strip(),
                date_format
            ).date()
        except ValueError:
            continue

    return None


def calculate_days_between(previous_date, new_date):
    """Calculate elapsed days between two status dates."""

    previous = parse_status_date(previous_date)
    new = parse_status_date(new_date)

    if previous is None or new is None:
        return None

    return (new - previous).days


def send_notification(
    manuscript,
    previous_status,
    new_status,
    previous_status_date,
    new_status_date
):
    gmail_address = os.getenv("GMAIL_ADDRESS")
    gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")
    recipient_email = os.getenv("NOTIFICATION_EMAIL")

    if not all([
        gmail_address,
        gmail_app_password,
        recipient_email
    ]):
        print("Error: Missing email configuration.")
        return False

    days_elapsed = calculate_days_between(
        previous_status_date,
        new_status_date
    )

    if days_elapsed is not None:
        duration_text = f"It took {days_elapsed} days"
    else:
        duration_text = (
            "The elapsed time could not be calculated "
            "because one or both status dates are unavailable"
        )

    previous_date_text = previous_status_date or "Unavailable"
    new_date_text = new_status_date or "Unavailable"

    subject = (
        f"Manuscript Status Update: {manuscript['title']}"
    )

    body = f"""Hello,

This paper titled '{manuscript['title']}' in the journal
'{JOURNAL_NAME}' has changed its status from
'{previous_status}' to '{new_status}'.

{duration_text}, from {previous_date_text} to {new_date_text}.

Manuscript ID: {manuscript['manuscript_id']}

Best,
Manuscript Status Monitor
"""

    msg = MIMEMultipart()
    msg["From"] = gmail_address
    msg["To"] = recipient_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    server = None

    try:
        server = smtplib.SMTP(
            "smtp.gmail.com",
            587,
            timeout=30
        )

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

    notifications_enabled = config.get(
        "notification_enabled",
        True
    )

    print("Checking ScholarOne...")

    if not auto_login():
        print(
            "Could not confirm ScholarOne login. "
            "Monitoring stopped."
        )
        return

    subprocess.run(
        [
            sys.executable,
            str(APP_DIR / "fetch_browser_results.py")
        ],
        cwd=str(APP_DIR.parent),
        check=True
    )

    new_manuscripts = load_json(RESULTS_FILE)

    if not isinstance(new_manuscripts, list):
        raise ValueError(
            "Browser results must be a JSON list."
        )

    if not new_manuscripts:
        raise ValueError(
            "Browser results are empty. "
            "Database was not modified."
        )

    if not all(
        isinstance(m, dict)
        and m.get("manuscript_id")
        and m.get("title")
        and m.get("status")
        for m in new_manuscripts
    ):
        raise ValueError(
            "Browser results contain incomplete records. "
            "Database was not modified."
        )

    print(
        f"Manuscripts retrieved: {len(new_manuscripts)}"
    )

    manuscripts = load_json(DATABASE_FILE)

    if not isinstance(manuscripts, list):
        raise ValueError(
            "Manuscript database must be a JSON list."
        )

    if not all(
        isinstance(m, dict)
        for m in manuscripts
    ):
        raise ValueError(
            "Database contains invalid manuscript records."
        )

    existing = {
        m["manuscript_id"]: m
        for m in manuscripts
    }

    record_indices = {
        m["manuscript_id"]: index
        for index, m in enumerate(manuscripts)
    }

    now = datetime.now(timezone.utc).isoformat()

    for item in new_manuscripts:

        manuscript_id = item["manuscript_id"]
        title = item["title"]
        new_status = item["status"]
        new_status_date = item.get("status_date") or ""

        # First time seeing a manuscript:
        # save its baseline without sending an email.

        if manuscript_id not in existing:

            new_record = {
                "manuscript_id": manuscript_id,
                "title": title,
                "status": new_status,
                "status_date": new_status_date,
                "last_checked": now,
                "status_history": [
                    {
                        "status": new_status,
                        "status_date": new_status_date,
                        "timestamp": now
                    }
                ]
            }

            manuscripts.append(new_record)

            existing[manuscript_id] = new_record
            record_indices[manuscript_id] = (
                len(manuscripts) - 1
            )

            print(
                f"New manuscript recorded: {manuscript_id}"
            )

            continue

        manuscript = existing[manuscript_id]

        previous_status = manuscript["status"]

        previous_status_date = (
            manuscript.get("status_date") or ""
        )

        # No status change: update the latest check information.

        if previous_status == new_status:

            manuscript["title"] = title
            manuscript["status_date"] = new_status_date
            manuscript["last_checked"] = now

            print(
                f"No status change: {manuscript_id}"
            )

            continue

        # A status change was detected.

        print(
            f"Status change detected: {manuscript_id} "
            f"({previous_status} -> {new_status})"
        )

        updated_record = dict(manuscript)

        updated_record["title"] = title
        updated_record["status"] = new_status
        updated_record["status_date"] = new_status_date
        updated_record["last_checked"] = now

        updated_record["status_history"] = list(
            manuscript.get("status_history", [])
        )

        updated_record["status_history"].append({
            "status": new_status,
            "status_date": new_status_date,
            "timestamp": now
        })

        # If notifications are disabled, save the new status.

        if not notifications_enabled:

            index = record_indices[manuscript_id]
            manuscripts[index] = updated_record
            existing[manuscript_id] = updated_record

            print(
                "Notification disabled. "
                "Status updated without email."
            )

            continue

        # Send an email before updating the database.
        # If sending fails, the old status and date are preserved.

        email_sent = send_notification(
            updated_record,
            previous_status,
            new_status,
            previous_status_date,
            new_status_date
        )

        if email_sent:

            index = record_indices[manuscript_id]
            manuscripts[index] = updated_record
            existing[manuscript_id] = updated_record

            print(
                f"Status updated: {manuscript_id}"
            )

        else:

            print(
                "Status not updated. Notification will be "
                f"retried on the next check: {manuscript_id}"
            )

    save_json(DATABASE_FILE, manuscripts)

    print("Manuscript database saved.")


def main():
    process_browser_results()


if __name__ == "__main__":
    main()
