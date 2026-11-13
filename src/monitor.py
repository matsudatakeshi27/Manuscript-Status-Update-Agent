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

JOURNALS = [
    "Marketing Science",
    "Journal of Marketing Research"
]


def load_json(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def parse_status_date(date_string):
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

    journal_name = manuscript["journal"]

    subject = (
        f"Manuscript Status Update: {manuscript['title']}"
    )

    body = f"""Hello,

This paper titled '{manuscript['title']}' in the journal
'{journal_name}' has changed its status from
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


def retrieve_all_browser_results():
    """
    Retrieve results from both journals before modifying the database.
    If either journal fails, stop the monitoring run.
    """

    all_manuscripts = []

    for journal in JOURNALS:

        print(f"\nChecking {journal}...")

        if not auto_login(journal):
            raise RuntimeError(
                f"Login failed for {journal}. "
                "Monitoring stopped. Database was not modified."
            )

        subprocess.run(
            [
                sys.executable,
                str(APP_DIR / "fetch_browser_results.py"),
                journal
            ],
            cwd=str(APP_DIR.parent),
            check=True
        )

        journal_results = load_json(RESULTS_FILE)

        if not isinstance(journal_results, list):
            raise ValueError(
                f"Invalid browser results for {journal}."
            )

        if not journal_results:
            raise ValueError(
                f"No manuscripts retrieved for {journal}. "
                "Database was not modified."
            )

        for item in journal_results:

            if not isinstance(item, dict):
                raise ValueError(
                    f"Invalid record returned by {journal}."
                )

            if not all([
                item.get("manuscript_id"),
                item.get("title"),
                item.get("status")
            ]):
                raise ValueError(
                    f"Incomplete manuscript record from {journal}."
                )

            if item.get("journal") != journal:
                raise ValueError(
                    f"Journal mismatch in browser results for {journal}. "
                    "Database was not modified."
                )

        print(
            f"Manuscripts retrieved from {journal}: "
            f"{len(journal_results)}"
        )

        all_manuscripts.extend(journal_results)

    print(
        f"\nTotal manuscripts retrieved: "
        f"{len(all_manuscripts)}"
    )

    return all_manuscripts


def process_browser_results():

    config = load_json(CONFIG_FILE)

    notifications_enabled = config.get(
        "notification_enabled",
        True
    )

    print("Starting manuscript monitoring...")

    # Retrieve both journals before touching the database.
    new_manuscripts = retrieve_all_browser_results()

    manuscripts = load_json(DATABASE_FILE)

    if not isinstance(manuscripts, list):
        raise ValueError(
            "Manuscript database must be a JSON list."
        )

    if not all(isinstance(m, dict) for m in manuscripts):
        raise ValueError(
            "Database contains invalid manuscript records."
        )

    # Preserve compatibility with the existing MS database.
    for manuscript in manuscripts:
        if not manuscript.get("journal"):
            manuscript["journal"] = "Marketing Science"

    # Identify records using both journal and manuscript ID.
    existing = {}
    record_indices = {}

    for index, manuscript in enumerate(manuscripts):

        key = (
            manuscript["journal"],
            manuscript["manuscript_id"]
        )

        if key in existing:
            raise ValueError(
                f"Duplicate database record: {key}"
            )

        existing[key] = manuscript
        record_indices[key] = index

    now = datetime.now(timezone.utc).isoformat()

    for item in new_manuscripts:

        journal = item["journal"]
        manuscript_id = item["manuscript_id"]
        title = item["title"]
        new_status = item["status"]
        new_status_date = item.get("status_date") or ""

        key = (journal, manuscript_id)

        # First time seeing a manuscript:
        # save its baseline without sending an email.

        if key not in existing:

            new_record = {
                "journal": journal,
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

            existing[key] = new_record
            record_indices[key] = len(manuscripts) - 1

            print(
                f"New manuscript recorded: "
                f"[{journal}] {manuscript_id}"
            )

            continue

        manuscript = existing[key]

        previous_status = manuscript["status"]
        previous_status_date = manuscript.get("status_date") or ""

        # No status change.

        if previous_status == new_status:

            manuscript["title"] = title
            manuscript["status_date"] = new_status_date
            manuscript["last_checked"] = now

            print(
                f"No status change: "
                f"[{journal}] {manuscript_id}"
            )

            continue

        # A status change was detected.

        print(
            f"Status change detected: [{journal}] "
            f"{manuscript_id} "
            f"({previous_status} -> {new_status})"
        )

        updated_record = dict(manuscript)

        updated_record["journal"] = journal
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

        # If notifications are disabled, update without email.

        if not notifications_enabled:

            index = record_indices[key]
            manuscripts[index] = updated_record
            existing[key] = updated_record

            print(
                "Notification disabled. "
                "Status updated without email."
            )

            continue

        # Send email before updating the database.
        # If email fails, the old status is preserved.

        email_sent = send_notification(
            updated_record,
            previous_status,
            new_status,
            previous_status_date,
            new_status_date
        )

        if email_sent:

            index = record_indices[key]
            manuscripts[index] = updated_record
            existing[key] = updated_record

            print(
                f"Status updated: [{journal}] {manuscript_id}"
            )

        else:

            print(
                "Status not updated. Notification will be "
                f"retried on the next check: [{journal}] "
                f"{manuscript_id}"
            )

    save_json(DATABASE_FILE, manuscripts)

    print("\nManuscript database saved.")
    print("Monitoring completed.")


def main():
    process_browser_results()


if __name__ == "__main__":
    main()