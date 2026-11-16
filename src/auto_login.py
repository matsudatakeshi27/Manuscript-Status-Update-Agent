
import os
import subprocess
import time
import keyring

from playwright.sync_api import sync_playwright

CDP_URL = os.getenv(
    "OPENCLAW_CDP_URL",
    "http://127.0.0.1:18800"
)

JOURNALS = {
    "Marketing Science": {
        "service": "marketingscience-monitor",
        "url": "https://mc.manuscriptcentral.com/mksc",
        "path": "/mksc",
    },
    "Journal of Marketing Research": {
        "service": "jmr-monitor",
        "url": "https://mc.manuscriptcentral.com/ama_jmr",
        "path": "/ama_jmr",
    },
}


def start_openclaw_browser():
    try:
        if os.name == "nt":
            command = [
                "cmd", "/c", "openclaw", "browser", "start"
            ]
        else:
            command = [
                "openclaw", "browser", "start"
            ]

        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
        return True

    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Could not start OpenClaw browser.")
        return False


def connect_browser(p):
    try:
        return p.chromium.connect_over_cdp(CDP_URL)

    except Exception:
        print("Starting OpenClaw browser...")

        if not start_openclaw_browser():
            return None

        for _ in range(20):
            try:
                return p.chromium.connect_over_cdp(CDP_URL)
            except Exception:
                time.sleep(1)

        print("Could not connect to OpenClaw browser.")
        return None


def find_journal_page(browser, journal):
    expected_path = JOURNALS[journal]["path"]

    for context in browser.contexts:
        for page in context.pages:
            if (
                "mc.manuscriptcentral.com" in page.url
                and expected_path in page.url
            ):
                return page

    return None


def verify_logged_in(page):
    try:
        username_field = page.locator("#USERID")
        password_field = page.locator("#PASSWORD")

        # If the login form is visible, the user is logged out.
        if (
            username_field.count() > 0
            and username_field.is_visible()
        ):
            return False

        if (
            password_field.count() > 0
            and password_field.is_visible()
        ):
            return False

        # Require an actual logged-in navigation element.
        logout = page.get_by_text("Log Out", exact=True)

        if logout.count() == 0 or not logout.first.is_visible():
            return False

        return True

    except Exception:
        return False


def auto_login(journal="Marketing Science"):
    if journal not in JOURNALS:
        print(f"Unknown journal: {journal}")
        return False

    settings = JOURNALS[journal]

    username = keyring.get_password(
        settings["service"],
        "username",
    )

    password = keyring.get_password(
        settings["service"],
        "password",
    )

    if not username or not password:
        print(f"Credentials missing for {journal}.")
        return False

    try:
        with sync_playwright() as p:
            browser = connect_browser(p)

            if browser is None:
                return False

            page = find_journal_page(browser, journal)

            if page is None:
                print(f"Opening {journal}...")

                if browser.contexts:
                    context = browser.contexts[0]
                else:
                    context = browser.new_context()

                page = context.new_page()

                page.goto(
                    settings["url"],
                    wait_until="domcontentloaded",
                    timeout=60000,
                )

            page.wait_for_timeout(3000)

            username_field = page.locator("#USERID")
            password_field = page.locator("#PASSWORD")
            login_button = page.locator("#logInButton")

            # First check whether the dashboard is already available.
            if verify_logged_in(page):
                print(f"Already logged in to {journal}.")
                return True

            # Confirm that the login form is available.
            if (
                username_field.count() == 0
                or password_field.count() == 0
                or login_button.count() == 0
            ):
                print(f"Login form not found for {journal}.")
                return False

            if (
                not username_field.is_visible()
                or not password_field.is_visible()
                or not login_button.is_visible()
            ):
                print(f"Login form is not visible for {journal}.")
                return False

            print(f"Logging in to {journal}...")

            username_field.fill(username)
            password_field.fill(password)
            login_button.click()

            # Wait for the dashboard rather than relying only
            # on the disappearance of the password field.
            if not verify_logged_in(page):
                print(
                    f"Login not confirmed for {journal}. "
                    "Check the browser."
                )
                return False

            print(f"Login successful: {journal}.")
            return True

    except Exception:
        print("Login automation failed. Details suppressed.")
        return False


if __name__ == "__main__":
    auto_login()
