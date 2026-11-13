
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
                "cmd",
                "/c",
                "openclaw",
                "browser",
                "start",
            ]
        else:
            command = [
                "openclaw",
                "browser",
                "start",
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


def auto_login(journal="Marketing Science"):
    if journal not in JOURNALS:
        print(f"Unknown journal: {journal}")
        return False

    settings = JOURNALS[journal]

    username = keyring.get_password(
        settings["service"], "username"
    )
    password = keyring.get_password(
        settings["service"], "password"
    )

    if not username or not password:
        print(f"Credentials missing for {journal}.")
        return False

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp(CDP_URL)

            except Exception:
                print("Starting OpenClaw browser...")

                if not start_openclaw_browser():
                    return False

                for _ in range(20):
                    try:
                        browser = p.chromium.connect_over_cdp(
                            CDP_URL
                        )
                        break
                    except Exception:
                        time.sleep(1)
                else:
                    print("Could not connect to OpenClaw browser.")
                    return False

            pages = [
                page
                for context in browser.contexts
                for page in context.pages
            ]

            page = next(
                (
                    pg for pg in pages
                    if (
                        "mc.manuscriptcentral.com"
                        + settings["path"]
                    ) in pg.url
                ),
                None,
            )

            if page is None:
                print(f"Opening {journal}...")

                context = (
                    browser.contexts[0]
                    if browser.contexts
                    else browser.new_context()
                )

                page = context.new_page()
                page.goto(
                    settings["url"],
                    wait_until="domcontentloaded",
                    timeout=60000,
                )

            page.wait_for_timeout(3000)

            if not page.locator("#PASSWORD").is_visible():
                if not page.locator("#USERID").is_visible():
                    print(f"Already logged in to {journal}.")
                    return True

                print("Login form not fully loaded.")
                return False

            print(f"Logging in to {journal}...")

            page.locator("#USERID").fill(username)
            page.locator("#PASSWORD").fill(password)
            page.locator("#logInButton").click()

            page.wait_for_timeout(7000)

            if page.locator("#PASSWORD").is_visible():
                print("Login not confirmed. Check the browser.")
                return False

            print(f"Login successful: {journal}.")
            return True

    except Exception:
        print("Login automation failed. Details suppressed.")
        return False


if __name__ == "__main__":
    auto_login()
