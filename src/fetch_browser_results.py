
import asyncio
import json
import re
from pathlib import Path
from playwright.async_api import async_playwright

CDP_URL = "http://127.0.0.1:18800"
RESULTS_FILE = Path.home() / ".scholarone-monitor" / "browser_results.json"


async def find_scholarone_page(browser):
    for context in browser.contexts:
        for page in context.pages:
            if "mc.manuscriptcentral.com/mksc" in page.url:
                return page

    raise RuntimeError("No ScholarOne tab found. Open ScholarOne in Brave first.")



async def go_to_author_dashboard(page):
    # Check which menu item is currently active.
    active_item = page.locator("li.nav-submenu.active")

    active_text = ""
    if await active_item.count() > 0:
        active_text = await active_item.first.inner_text()

    if "Manuscripts with Decisions" in active_text:
        print("Already on Manuscripts with Decisions.")
    else:
        print("Navigating to Manuscripts with Decisions...")

        decisions_link = page.get_by_role(
            "link",
            name=re.compile(r"Manuscripts with Decisions", re.I)
        )

        if await decisions_link.count() == 0:
            raise RuntimeError(
                "Could not find Manuscripts with Decisions link."
            )

        await decisions_link.first.click()

        # Wait until the correct sidebar item becomes active.
        await page.wait_for_function("""
            () => {
                const active = document.querySelector(
                    'li.nav-submenu.active'
                );
                return active &&
                    active.innerText.includes(
                        'Manuscripts with Decisions'
                    );
            }
        """, timeout=20000)

        await page.wait_for_timeout(3000)

    await page.locator("#authorDashboardQueue").wait_for(
        state="visible",
        timeout=15000
    )



async def set_page_size(page):
    dropdown = page.locator(
        'select[name="authorDashboardQueue_length"]'
    ).first

    if await dropdown.count() > 0:
        await dropdown.select_option("50")
        await page.wait_for_timeout(2000)



async def scrape_current_table(page, source):
    for attempt in range(5):
        try:
            await page.locator("#authorDashboardQueue").wait_for(
                state="visible", timeout=15000
            )

            await set_page_size(page)

            # Give ScholarOne time to finish any table refresh.
            await page.wait_for_timeout(3000)

            records = await page.locator(
                "#authorDashboardQueue tbody tr"
            ).evaluate_all(
                """(rows, source) => rows.map(row => {
                    const id = row.querySelector('td[data-label="ID"]');
                    const title = row.querySelector('td[data-label="title"]');
                    const statusCell = row.querySelector('td[data-label="status"]');

                    if (!id || !title || !statusCell) return null;

                    const statusSpans = Array.from(
                        statusCell.querySelectorAll("span.pagecontents")
                    );

                    const statusSpan = statusSpans.find(span =>
                        /\\(\\d{1,2}-[A-Za-z]{3}-\\d{4}\\)/.test(span.innerText)
                    );

                    const statusText = statusSpan
                        ? statusSpan.innerText.trim()
                        : statusCell.innerText.trim();

                    const dateMatch = statusText.match(
                        /\\((\\d{1,2}-[A-Za-z]{3}-\\d{4})\\)/
                    );

                    const status = statusText
                        .replace(/\\s*\\(\\d{1,2}-[A-Za-z]{3}-\\d{4}\\)/, "")
                        .trim();

                    return {
                        manuscript_id: id.innerText.trim(),
                        title: title.innerText.trim(),
                        status: status,
                        status_date: dateMatch ? dateMatch[1] : null,
                        source: source
                    };
                }).filter(Boolean)""",
                source
            )

            print(f"{source}: {len(records)} manuscripts found.")
            return records

        except Exception as e:
            if attempt == 4:
                raise

            print(
                f"Table refresh detected (attempt {attempt + 1}/5). "
                "Retrying..."
            )
            await page.wait_for_timeout(3000)

    return []



async def go_to_coauthored_page(page, previous_ids):
    print("Opening Manuscripts I Have Co-Authored...")

    # Trigger the exact ScholarOne navigation action from the menu.
    await page.evaluate("""
        () => {
            setField('DATATABLE_CURRENT_PAGE_AUTHOR_CENTER', 0);
            setField('DATATABLE_PAGE_LENGTH_AUTHOR_CENTER', 10);
            setDataAndNextPage(
                'MS_LIST_TO_DISPLAY',
                5,
                'AUTHOR_VIEW_MANUSCRIPTS'
            );
        }
    """)

    # Wait for ScholarOne to finish updating the table.
    await page.wait_for_timeout(5000)

    await page.locator("#authorDashboardQueue").wait_for(
        state="visible",
        timeout=20000
    )

    print("Co-authored page navigation requested.")



async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)

        page = await find_scholarone_page(browser)
        print("ScholarOne tab found.")

        await go_to_author_dashboard(page)

        print("Scraping Author Dashboard...")
        author_records = await scrape_current_table(
            page, "Author Dashboard"
        )

        author_ids = [
            record["manuscript_id"] for record in author_records
        ]

        await go_to_coauthored_page(page, author_ids)

        print("Scraping co-authored manuscripts...")
        coauthored_records = await scrape_current_table(
            page, "Co-Authored"
        )

        # Combine both queues and remove duplicate manuscript IDs.
        combined = []
        seen_ids = set()

        for record in author_records + coauthored_records:
            manuscript_id = record["manuscript_id"]

            if manuscript_id not in seen_ids:
                combined.append(record)
                seen_ids.add(manuscript_id)

        RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(combined, f, indent=4, ensure_ascii=False)

        print()
        print(f"Author Dashboard: {len(author_records)}")
        print(f"Co-Authored: {len(coauthored_records)}")
        print(f"Combined unique manuscripts: {len(combined)}")
        print(f"Saved to: {RESULTS_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
