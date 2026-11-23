
import json
import os
import re
import sys
import time
import subprocess

from datetime import datetime
from urllib.parse import (
    urljoin,
    urlparse,
    parse_qs,
    urlencode,
    urlunparse,
)

import keyring

from playwright.sync_api import sync_playwright


CDP_URL = os.getenv(
    "OPENCLAW_CDP_URL",
    "http://127.0.0.1:18800"
)

IJRM_URL = "https://www.editorialmanager.com/ijrm/"
KEYRING_SERVICE = "ijrm-monitor"

RESULTS_FILE = os.path.expanduser(
    "~/Library/Application Support/"
    "ScholarOneMonitor/browser_results.json"
)

JOURNAL_NAME = "International Journal of Research in Marketing"


# --------------------------------------------------
# CREDENTIALS
# --------------------------------------------------

def get_credentials():
    username = keyring.get_password(
        KEYRING_SERVICE, "username"
    )

    password = keyring.get_password(
        KEYRING_SERVICE, "password"
    )

    if not username or not password:
        raise RuntimeError(
            "IJRM credentials are missing from Keychain."
        )

    return username, password


# --------------------------------------------------
# BROWSER CONNECTION
# --------------------------------------------------

def connect_browser(p):
    """
    Connect to the OpenClaw browser.

    If OpenClaw is not running, start it and retry
    the CDP connection for up to 60 seconds.
    """

    print("\nConnecting to OpenClaw browser...")

    # First, try connecting to an existing browser.
    try:
        browser = p.chromium.connect_over_cdp(
            CDP_URL,
            timeout=5000
        )

        print("Connected to existing OpenClaw browser.")
        return browser

    except Exception:
        print("OpenClaw browser is not reachable.")

    # Start OpenClaw browser.
    print("\nStarting OpenClaw browser...")

    try:
        result = subprocess.run(
            ["openclaw", "browser", "start"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.stdout.strip():
            print(result.stdout.strip())

        if result.stderr.strip():
            print(result.stderr.strip())

    except FileNotFoundError as exc:
        raise RuntimeError(
            "Could not find the openclaw command. "
            "Make sure OpenClaw is installed and available "
            "in the PATH used by this Python process."
        ) from exc

    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "The OpenClaw browser start command timed out."
        ) from exc

    # Retry the connection.
    print("\nWaiting for OpenClaw browser to become available...")

    deadline = time.monotonic() + 60
    last_error = None

    while time.monotonic() < deadline:
        try:
            browser = p.chromium.connect_over_cdp(
                CDP_URL,
                timeout=5000
            )

            print("Successfully connected to OpenClaw browser.")
            return browser

        except Exception as exc:
            last_error = exc
            time.sleep(2)

    raise RuntimeError(
        "Could not connect to OpenClaw browser after "
        "starting it and retrying for 60 seconds. "
        f"Last error: {last_error}"
    )


# --------------------------------------------------
# LOGIN DIAGNOSTICS
# --------------------------------------------------

def print_login_diagnostics(page):
    print("\nLogin form diagnostics:")
    print("Page title:", page.title())
    print("Current URL:", page.url)

    summaries = page.locator("summary").all_inner_texts()
    print("Summary elements:", summaries)

    for selector in (
        "#traditionalLoginContent",
        "#username",
        "#passwordTextbox",
        'input[name="authorLogin"]',
    ):
        locator = page.locator(selector)

        print(
            f"{selector}: "
            f"count={locator.count()}, "
            f"visible={locator.first.is_visible() if locator.count() else False}"
        )

    inputs = page.locator("input")

    print("\nVisible input fields:")

    for i in range(inputs.count()):
        element = inputs.nth(i)

        if element.is_visible():
            print({
                "type": element.get_attribute("type"),
                "id": element.get_attribute("id"),
                "name": element.get_attribute("name"),
                "value": element.get_attribute("value"),
            })


# --------------------------------------------------
# IJRM LOGIN
# --------------------------------------------------


def accept_cookies(page):
    print("\nChecking for cookie consent banner...")

    for frame in page.frames:
        try:
            # Try the OneTrust accept button.
            button = frame.locator("#onetrust-accept-btn-handler")

            if button.count() and button.first.is_visible():
                button.first.evaluate("(element) => element.click()")
                print("Accepted cookies using OneTrust button.")
                page.wait_for_timeout(2000)
                return

            # Fallback: find the button by its text.
            button = frame.get_by_role(
                "button",
                name=re.compile(r"accept all cookies", re.IGNORECASE)
            )

            if button.count() and button.first.is_visible():
                button.first.evaluate("(element) => element.click()")
                print("Accepted cookies using button text.")
                page.wait_for_timeout(2000)
                return

        except Exception as exc:
            print(f"Cookie handler check: {exc}")
            continue

    # Check whether the overlay is still visible.
    overlay = page.locator(".onetrust-pc-dark-filter")

    if overlay.count() and overlay.first.is_visible():
        raise RuntimeError(
            "Cookie consent overlay is still visible. "
            "Cannot safely proceed with IJRM login."
        )

    print("No active cookie consent overlay found.")


def login(page, username, password):
    print("\nOpening IJRM Editorial Manager...")

    page.goto(
        IJRM_URL,
        wait_until="domcontentloaded",
        timeout=60000
    )

    page.wait_for_timeout(4000)

    accept_cookies(page)

    print("Page title:", page.title())

    def find_dashboard():
        for frame in page.frames:
            dashboard = frame.locator("#twoColLayoutItems")

            if (
                dashboard.count() > 0
                and dashboard.first.is_visible()
            ):
                return frame

        return None

    # Check whether the Author Main Menu is already available.
    dashboard_frame = find_dashboard()

    if dashboard_frame:
        print("Author dashboard already available.")
        return dashboard_frame

    # Check whether we are already logged in.
    logged_in = False

    for frame in page.frames:
        try:
            if "logout" in frame.locator("body").inner_text().lower():
                logged_in = True
                break
        except Exception:
            continue

    if logged_in:
        print("Already logged in.")

        main_menu_link = page.get_by_role(
            "link",
            name="Main Menu",
            exact=True
        )

        if main_menu_link.count() == 0:
            raise RuntimeError(
                "Logged in, but the Main Menu link was not found."
            )

        main_menu_link.first.click()
        page.wait_for_timeout(3000)

        dashboard_frame = find_dashboard()

        if dashboard_frame:
            print("Author Main Menu found.")
            return dashboard_frame

        raise RuntimeError(
            "Clicked Main Menu, but the Author dashboard "
            "was not found."
        )

    # If not logged in, locate the login frame.
    print("Not logged in. Looking for login frame...")

    login_frame = None

    for frame in page.frames:
        if re.search(r"/login\.asp", frame.url, re.IGNORECASE):
            login_frame = frame
            break

    if login_frame is None:
        page.wait_for_timeout(5000)

        for frame in page.frames:
            if re.search(r"/login\.asp", frame.url, re.IGNORECASE):
                login_frame = frame
                break

    if login_frame is None:
        raise RuntimeError(
            "Neither an author dashboard nor a login frame "
            "was found."
        )

    print("Found IJRM login frame.")

    # Expand traditional username/password login.
    login_section = login_frame.locator(
        "#traditionalLoginCollapsible"
    )

    login_section.wait_for(
        state="attached",
        timeout=20000
    )

    login_section.evaluate(
        "(element) => { element.open = true; }"
    )

    # Fill credentials.
    username_field = login_frame.locator("#username")
    password_field = login_frame.locator("#passwordTextbox")

    username_field.wait_for(
        state="visible",
        timeout=15000
    )

    password_field.wait_for(
        state="visible",
        timeout=15000
    )

    username_field.fill(username)
    password_field.fill(password)

    print("Clicking Author Login...")

    login_frame.locator(
        '#emLoginButtonsDiv input[name="authorLogin"]'
    ).click()

    # Wait for the Author Main Menu.
    for _ in range(30):
        page.wait_for_timeout(1000)

        dashboard_frame = find_dashboard()

        if dashboard_frame:
            print("IJRM login successful.")
            return dashboard_frame

    raise RuntimeError(
        "Login was submitted, but the Author dashboard "
        "did not appear."
    )


# --------------------------------------------------
# DISCOVER MANUSCRIPT QUEUES
# --------------------------------------------------

def discover_queues(frame):
    print("\nDiscovering available IJRM manuscript queues...")

    menu = frame.locator("#twoColLayoutItems")

    if menu.count() == 0:
        raise RuntimeError(
            "Author Main Menu not found in the dashboard frame."
        )

    links = menu.locator("a[href]")

    queues = []
    seen = set()

    for i in range(links.count()):
        link = links.nth(i)

        if not link.is_visible():
            continue

        name = link.inner_text().strip()
        href = link.get_attribute("href")

        if not name or not href:
            continue

        lower_name = name.lower()
        lower_href = href.lower()

        if "submit new manuscript" in lower_name:
            continue

        if "submit_manuscript.asp" in lower_href:
            continue

        if "incomplete" in lower_name:
            continue

        if lower_href.startswith("javascript:"):
            continue

        queue_url = urljoin(frame.url, href)

        if queue_url not in seen:
            queues.append({
                "name": name,
                "url": queue_url
            })

            seen.add(queue_url)

    for queue in queues:
        print(f"  Found: {queue['name']}")

    print(f"Total clickable queues: {len(queues)}")

    return queues


# --------------------------------------------------
# DATE NORMALIZATION
# --------------------------------------------------

def normalize_date(value):
    value = value.strip()

    if not value:
        return None

    formats = (
        "%b %d, %Y",
        "%B %d, %Y",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%Y-%m-%d",
    )

    for fmt in formats:
        try:
            return datetime.strptime(
                value, fmt
            ).strftime("%d-%b-%Y")

        except ValueError:
            continue

    return value


# --------------------------------------------------
# TABLE EXTRACTION
# --------------------------------------------------

def get_column_index(headers, expected):
    for i, header in enumerate(headers):
        if header.strip().lower() == expected.lower():
            return i

    return None


def scrape_table_page(page, queue_name):
    table = page.locator("#datatable")

    if table.count() == 0:
        print(f"  No manuscript table in {queue_name}.")
        return []

    headers = [
        h.strip()
        for h in table.locator("thead th").all_inner_texts()
    ]

    id_index = get_column_index(
        headers, "Manuscript Number"
    )

    title_index = get_column_index(
        headers, "Title"
    )

    date_index = get_column_index(
        headers, "Status Date"
    )

    status_index = get_column_index(
        headers, "Current Status"
    )

    required = {
        "Manuscript Number": id_index,
        "Title": title_index,
        "Status Date": date_index,
        "Current Status": status_index,
    }

    missing = [
        name
        for name, index in required.items()
        if index is None
    ]

    if missing:
        raise RuntimeError(
            f"Unexpected IJRM table columns in "
            f"{queue_name}. Missing: {missing}. "
            f"Found headers: {headers}"
        )

    records = []
    rows = table.locator("tbody tr")

    for i in range(rows.count()):
        cells = rows.nth(i).locator("td").all_inner_texts()

        if not cells:
            continue

        max_index = max(required.values())

        if len(cells) <= max_index:
            continue

        manuscript_id = cells[id_index].strip()
        title = cells[title_index].strip()
        status_date = cells[date_index].strip()
        status = cells[status_index].strip()

        if not manuscript_id:
            continue

        records.append({
            "manuscript_id": manuscript_id,
            "title": title,
            "status": status,
            "status_date": normalize_date(status_date),
            "source": queue_name,
            "journal": JOURNAL_NAME,
        })

    return records


# --------------------------------------------------
# PAGINATION
# --------------------------------------------------

def get_pagination_info(page):
    pagination = page.locator("td.pagination")

    if pagination.count() == 0:
        return 1

    text = pagination.first.inner_text()

    match = re.search(
        r"Page:\s*\d+\s+of\s+(\d+)",
        text,
        re.IGNORECASE
    )

    return int(match.group(1)) if match else 1


def set_page_number(url, page_number):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    params["currentPage"] = [str(page_number)]

    new_query = urlencode(params, doseq=True)

    return urlunparse(
        parsed._replace(query=new_query)
    )


# --------------------------------------------------
# SCRAPE EACH QUEUE
# --------------------------------------------------

def scrape_queue(frame, queue):
    queue_name = queue["name"]
    queue_url = queue["url"]

    print(f"\nChecking queue: {queue_name}")

    frame.goto(
        queue_url,
        wait_until="domcontentloaded",
        timeout=60000
    )

    frame.wait_for_timeout(2000)

    table = frame.locator("#datatable")

    if table.count() == 0:
        print("  No manuscript table found.")
        print("  Current frame URL:", frame.url)
        print("  Page text:", frame.locator("body").inner_text()[:2000])
        return []

    total_pages = get_pagination_info(frame)

    print(f"  Pages available: {total_pages}")

    all_records = []

    for page_number in range(1, total_pages + 1):
        if page_number > 1:
            next_url = set_page_number(
                queue_url, page_number
            )

            frame.goto(
                next_url,
                wait_until="domcontentloaded",
                timeout=60000
            )

            frame.wait_for_timeout(1500)

        records = scrape_table_page(
            frame, queue_name
        )

        print(
            f"  Page {page_number}: "
            f"{len(records)} manuscripts found."
        )

        all_records.extend(records)

    return all_records


# --------------------------------------------------
# SAVE RESULTS
# --------------------------------------------------

def save_results(records):
    if not records:
        raise RuntimeError(
            "No IJRM manuscripts were extracted. "
            "Existing results were not overwritten."
        )

    unique_records = []
    seen_ids = set()

    for record in records:
        manuscript_id = record["manuscript_id"]

        if manuscript_id not in seen_ids:
            unique_records.append(record)
            seen_ids.add(manuscript_id)

    os.makedirs(
        os.path.dirname(RESULTS_FILE),
        exist_ok=True
    )

    with open(
        RESULTS_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            unique_records,
            f,
            indent=4,
            ensure_ascii=False
        )

    print("\nIJRM scraping completed.")
    print(f"Unique manuscripts: {len(unique_records)}")
    print(f"Saved to: {RESULTS_FILE}")


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    username, password = get_credentials()

    with sync_playwright() as p:
        browser = connect_browser(p)

        if not browser.contexts:
            raise RuntimeError(
                "No browser context found. "
                "Check the OpenClaw browser connection."
            )

        context = browser.contexts[0]
        page = context.new_page()

        try:
            # Log in or detect an existing logged-in session.
            dashboard_frame = login(
                page,
                username,
                password
            )

            # Discover clickable manuscript queues.
            queues = discover_queues(dashboard_frame)

            if not queues:
                raise RuntimeError(
                    "No clickable IJRM manuscript queues found."
                )

            all_records = []

            # Scrape each queue.
            for queue in queues:
                records = scrape_queue(
                    dashboard_frame,
                    queue
                )

                all_records.extend(records)

            # Save results only if manuscripts were extracted.
            save_results(all_records)

            print(
                f"\nIJRM scraping completed. "
                f"Total manuscripts extracted: {len(all_records)}"
            )

        finally:
            print("\nClosing IJRM tab...")
            page.close()
            print("Tab closed.")


if __name__ == "__main__":
    try:
        main()

    except Exception as e:
        print(f"IJRM monitoring failed: {e}")
        raise
