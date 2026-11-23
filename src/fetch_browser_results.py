
import asyncio
import json
import re
import sys
import os
import keyring

from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)
from paths import RESULTS_FILE


CDP_URL = os.getenv(
    "OPENCLAW_CDP_URL",
    "http://127.0.0.1:18800"
)


JOURNALS = {
    "Marketing Science": {
        "service": "marketingscience-monitor",
        "url": "https://mc.manuscriptcentral.com/mksc",
    },
    "Management Science": {
        "service": "managementscience-monitor",
        "url": "https://mc.manuscriptcentral.com/ms",
    },
    "Journal of Marketing Research": {
        "service": "jmr-monitor",
        "url": "https://mc.manuscriptcentral.com/ama_jmr",
    },
    "Journal of Marketing": {
        "service": "journalofmarketing-monitor",
        "url": "https://mc.manuscriptcentral.com/ama_jm",
    },
    "Journal of Consumer Research": {
        "service": "jconres-monitor",
        "url": "https://mc.manuscriptcentral.com/jconres",
    },
    "Information Systems Research": {
        "service": "isr-monitor",
        "url": "https://mc.manuscriptcentral.com/isr",
    },
    "International Journal of Research in Marketing": {
        "service": "ijrm-monitor",
        "url": "https://www.editorialmanager.com/ijrm",
    },
    "Production and Operations Management": {
        "service": "poms-monitor",
        "url": "https://mc.manuscriptcentral.com/poms",
    },
}


QUEUE_PATTERN = re.compile(
    r"Manuscripts with Decisions|"
    r"Submitted Manuscripts|"
    r"Manuscripts I Have Co-Authored",
    re.I,
)


async def connect_browser(p):
    try:
        return await p.chromium.connect_over_cdp(CDP_URL)
    except Exception as exc:
        raise RuntimeError(
            "Could not connect to OpenClaw browser. "
            "Start it with: openclaw browser start"
        ) from exc


async def accept_cookies(page):
    """Accept a visible cookie banner when one is present."""
    print("Checking for cookie consent banner...")

    selectors = [
        "#onetrust-accept-btn-handler",
        'button:has-text("Accept All Cookies")',
        'button:has-text("Accept all")',
    ]

    for selector in selectors:
        try:
            button = page.locator(selector).first

            if await button.count() and await button.is_visible():
                await button.evaluate(
                    "(element) => element.click()"
                )
                print("Cookie consent accepted.")
                await page.wait_for_timeout(1500)
                return

        except Exception:
            continue

    overlay = page.locator(".onetrust-pc-dark-filter")

    if await overlay.count() and await overlay.first.is_visible():
        raise RuntimeError(
            "Cookie consent overlay is still visible, "
            "but no supported accept button was found."
        )

    print("No active cookie consent overlay found.")


async def login(page, journal):
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
        raise RuntimeError(
            f"Credentials missing for {journal} in Keychain."
        )

    print(f"Opening {journal} login page...")

    await page.goto(
        settings["url"],
        wait_until="domcontentloaded",
        timeout=60000,
    )

    await accept_cookies(page)

    username_field = page.locator("#USERID")
    password_field = page.locator("#PASSWORD")
    login_button = page.locator("#logInButton")

    await username_field.wait_for(
        state="visible",
        timeout=30000,
    )

    await password_field.wait_for(
        state="visible",
        timeout=30000,
    )

    print(f"Logging in to {journal}...")

    await username_field.fill(username)
    await password_field.fill(password)
    await login_button.click()

    logout = page.get_by_text("Log Out", exact=True)

    await logout.wait_for(
        state="visible",
        timeout=30000,
    )

    if await password_field.is_visible():
        raise RuntimeError(
            f"Login could not be verified for {journal}."
        )

    print(f"Login successful: {journal}.")


async def ensure_author_menu(page):
    queue_links = page.get_by_role(
        "link",
        name=QUEUE_PATTERN,
    )

    for i in range(await queue_links.count()):
        if await queue_links.nth(i).is_visible():
            return True

    print("Opening Author menu...")

    author = page.get_by_text(
        "Author",
        exact=True,
    ).first

    await author.wait_for(
        state="visible",
        timeout=15000,
    )

    await author.click()
    await page.wait_for_timeout(2000)

    for i in range(await queue_links.count()):
        if await queue_links.nth(i).is_visible():
            print("Author menu is ready.")
            return True

    print("No manuscript queues found in Author menu.")
    return False


async def open_queue(page, label):
    menu_ready = await ensure_author_menu(page)

    if not menu_ready:
        print(f"{label}: unavailable; skipping.")
        return False

    link = page.get_by_role(
        "link",
        name=re.compile(re.escape(label), re.I),
    )

    if await link.count() == 0 or not await link.first.is_visible():
        print(f"{label}: tab not available; skipping.")
        return False

    active = await page.locator(
        "li.nav-submenu.active"
    ).all_inner_texts()

    if any(label.lower() in item.lower() for item in active):
        print(f"{label}: already selected.")
    else:
        print(f"Opening {label}...")

        await link.first.click()
        await page.wait_for_timeout(4000)

    try:
        await page.locator(
            "#authorDashboardQueue"
        ).wait_for(
            state="visible",
            timeout=20000,
        )
    except PlaywrightTimeoutError:
        print(f"{label}: dashboard table unavailable; skipping.")
        return False

    return True


async def set_page_size(page):
    dropdown = page.locator(
        'select[name="authorDashboardQueue_length"]'
    ).first

    if await dropdown.count() > 0:
        try:
            await dropdown.select_option("50")
            await page.wait_for_timeout(2000)
        except Exception:
            pass


async def scrape_current_table(page, source, journal):
    for attempt in range(5):
        try:
            await page.locator(
                "#authorDashboardQueue"
            ).wait_for(
                state="visible",
                timeout=15000,
            )

            await set_page_size(page)
            await page.wait_for_timeout(2000)

            records = await page.locator(
                "#authorDashboardQueue tbody tr"
            ).evaluate_all(
                r"""(rows, args) => rows.map(row => {
                    const id = row.querySelector(
                        'td[data-label="ID"]'
                    );

                    const title = row.querySelector(
                        'td[data-label="title"]'
                    );

                    const statusCell = row.querySelector(
                        'td[data-label="status"]'
                    );

                    if (!id || !title || !statusCell) {
                        return null;
                    }

                    const statusSpans = Array.from(
                        statusCell.querySelectorAll(
                            "span.pagecontents"
                        )
                    );

                    const statusSpan = statusSpans.find(span =>
                        /\(\d{1,2}-[A-Za-z]{3}-\d{4}\)/.test(
                            span.innerText
                        )
                    );

                    const statusText = statusSpan
                        ? statusSpan.innerText.trim()
                        : statusCell.innerText.trim();

                    const dateMatch = statusText.match(
                        /\((\d{1,2}-[A-Za-z]{3}-\d{4})\)/
                    );

                    const status = statusText
                        .replace(
                            /\s*\(\d{1,2}-[A-Za-z]{3}-\d{4}\)/,
                            ""
                        )
                        .trim();

                    return {
                        manuscript_id: id.innerText.trim(),
                        title: title.innerText.trim(),
                        status: status,
                        status_date: dateMatch
                            ? dateMatch[1]
                            : null,
                        source: args.source,
                        journal: args.journal
                    };
                }).filter(Boolean)""",
                {
                    "source": source,
                    "journal": journal,
                },
            )

            print(
                f"{source}: {len(records)} manuscripts found."
            )

            return records

        except Exception:
            if attempt == 4:
                raise

            print(
                f"Table refresh detected "
                f"(attempt {attempt + 1}/5). Retrying..."
            )

            await page.wait_for_timeout(3000)

    return []


async def scrape_journal(page, journal):
    all_records = []
    available_queues = 0

    if await open_queue(
        page,
        "Manuscripts with Decisions",
    ):
        available_queues += 1

        author_records = await scrape_current_table(
            page,
            "Manuscripts with Decisions",
            journal,
        )

        all_records.extend(author_records)

    if await open_queue(
        page,
        "Submitted Manuscripts",
    ):
        available_queues += 1

        submitted_records = await scrape_current_table(
            page,
            "Submitted Manuscripts",
            journal,
        )

        all_records.extend(submitted_records)

    if await open_queue(
        page,
        "Manuscripts I Have Co-Authored",
    ):
        available_queues += 1

        coauthored_records = await scrape_current_table(
            page,
            "Co-Authored",
            journal,
        )

        all_records.extend(coauthored_records)

    if available_queues == 0:
        raise RuntimeError(
            f"No manuscript queues were accessible for {journal}. "
            "Results were not saved."
        )

    combined = []
    seen_ids = set()

    for record in all_records:
        manuscript_id = record["manuscript_id"]

        if manuscript_id not in seen_ids:
            combined.append(record)
            seen_ids.add(manuscript_id)

    RESULTS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        RESULTS_FILE,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            combined,
            f,
            indent=4,
            ensure_ascii=False,
        )

    print()
    print(f"Journal: {journal}")
    print(f"Available queues: {available_queues}")
    print(f"Combined unique manuscripts: {len(combined)}")
    print(f"Saved to: {RESULTS_FILE}")


async def main():
    journal = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Marketing Science"
    )

    if journal not in JOURNALS:
        raise ValueError(
            f"Unknown journal: {journal}. "
            f"Choose one of: {', '.join(JOURNALS)}"
        )

    async with async_playwright() as p:
        browser = await connect_browser(p)

        if not browser.contexts:
            raise RuntimeError(
                "OpenClaw browser has no available browser context."
            )

        context = browser.contexts[0]
        page = await context.new_page()

        try:
            await login(page, journal)
            await scrape_journal(page, journal)

        finally:
            if not page.is_closed():
                print(f"\nClosing {journal} tab...")
                await page.close()
                print("Tab closed.")


if __name__ == "__main__":
    asyncio.run(main())
