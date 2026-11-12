import keyring
from playwright.sync_api import sync_playwright

SERVICE = "scholarone-monitor"
CDP_URL = "http://127.0.0.1:18800"


def auto_login():
    username = keyring.get_password(SERVICE, "username")
    password = keyring.get_password(SERVICE, "password")

    if not username or not password:
        print("Credentials missing from Keychain.")
        return False

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(CDP_URL)

            pages = [
                page
                for context in browser.contexts
                for page in context.pages
            ]

            page = next(
                (pg for pg in pages
                 if "mc.manuscriptcentral.com/mksc" in pg.url),
                None
            )

            if page is None:
                print("ScholarOne tab not found.")
                return False

            if not page.locator("#PASSWORD").is_visible():
                if not page.locator("#USERID").is_visible():
                    print("Already logged in. Skipping login.")
                    return True

                print("Login form detected, but password field is not visible.")
                return False

            page.locator("#USERID").fill(username)
            page.locator("#PASSWORD").fill(password)
            page.locator("#logInButton").click()

            page.wait_for_timeout(7000)

            if page.locator("#PASSWORD").is_visible():
                print("Login not confirmed. Check the browser.")
                return False

            print("Login form disappeared. Proceeding.")
            return True

    except Exception:
        print("Login automation failed. Details suppressed.")
        return False


if __name__ == "__main__":
    auto_login()
