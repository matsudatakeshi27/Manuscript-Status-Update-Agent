import keyring
import subprocess
import time

from playwright.sync_api import sync_playwright

SERVICE = "scholarone-monitor"
CDP_URL = "http://127.0.0.1:18800"
SCHOLARONE_URL = "https://mc.manuscriptcentral.com/mksc"


def auto_login():

    username = keyring.get_password(SERVICE, "username")
    password = keyring.get_password(SERVICE, "password")

    if not username or not password:
        print("Credentials missing from Keychain.")
        return False

    try:
        with sync_playwright() as p:

            # Connect to OpenClaw browser.
            try:
                browser = p.chromium.connect_over_cdp(CDP_URL)

            except Exception:
                print("Starting OpenClaw browser...")

                subprocess.run(
                    ["openclaw", "browser", "start"],
                    check=True,
                    capture_output=True,
                    text=True
                )

                for _ in range(20):
                    try:
                        browser = p.chromium.connect_over_cdp(CDP_URL)
                        break
                    except Exception:
                        time.sleep(1)
                else:
                    print("Could not start browser.")
                    return False

            # Find an existing ScholarOne tab.
            pages = [
                page
                for context in browser.contexts
                for page in context.pages
            ]

            page = next(
                (
                    pg for pg in pages
                    if "mc.manuscriptcentral.com/mksc" in pg.url
                ),
                None
            )

            # Open ScholarOne if no tab exists.
            if page is None:
                print("Opening ScholarOne...")
                context = (
                    browser.contexts[0]
                    if browser.contexts
                    else browser.new_context()
                )
                page = context.new_page()
                page.goto(
                    SCHOLARONE_URL,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

            page.wait_for_timeout(3000)

            # Check whether login is required.
            if not page.locator("#PASSWORD").is_visible():

                if not page.locator("#USERID").is_visible():
                    print("Already logged in. Proceeding.")
                    return True

                print("Login form not fully loaded.")
                return False

            print("Login form detected. Logging in...")

            page.locator("#USERID").fill(username)
            page.locator("#PASSWORD").fill(password)
            page.locator("#logInButton").click()

            page.wait_for_timeout(7000)

            if page.locator("#PASSWORD").is_visible():
                print("Login not confirmed. Check the browser.")
                return False

            print("Login successful. Proceeding.")
            return True

    except Exception:
        print("Login automation failed. Details suppressed.")
        return False


if __name__ == "__main__":
    auto_login()