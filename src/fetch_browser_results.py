
import asyncio
import json
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright

CDP_URL = "http://127.0.0.1:18800"

RESULTS_FILE = (
    Path.home() / ".scholarone-monitor" / "browser_results.json"
)

JOURNALS = {
    "Marketing Science": "/mksc",
    "Journal of Marketing Research": "/ama_jmr",
}


async def find_scholarone_page(browser, journal):
    expected_path = JOURNALS[journal]

    for context in browser.contexts:
        for page in context.pages:
            if (
                "mc.manuscriptcentral.com" in page.url
                and expected_path in page.url
            ):
                return page

    raise RuntimeError(f"No open ScholarOne tab found for {journal}.")


async def ensure_author_menu(page):
    decisions = page.get_by_role(
        "link",
        name=re.compile(r"Manuscripts with Decisions", re.I),
    )

    if await decisions.count() == 0:
        print("Opening Author menu...")

        author = page.get_by_text("Author", exact=True).first
        await author.click()
        await page.wait_for_timeout(2000)

    return page.get_by_role(
        "link",
        name=re.compile(r"Manuscripts with Decisions", re.I),
    )


async def open_queue(page, label, required=False):
    """Navigate to a dashboard queue using its visible menu link."""

    await ensure_author_menu(page)

    link = page.get_by_role(
        "link",
        name=re.compile(re.escape(label), re.I),
    )

    if await link.count() == 0:
        if required:
            raise RuntimeError(f"Required queue not found: {label}")

        print(f"{label}: tab not available; skipping.")
        return False

    # Avoid clicking again if this queue is already selected.
    active = await page.locator(
        "li.nav-submenu.active"
    ).all_inner_texts()

    if any(label.lower() in item.lower() for item in active):
        print(f"{label}: already selected.")
    else:
        print(f"Opening {label}...")
        await link.first.click()
        await page.wait_for_timeout(4000)

    await page.locator("#authorDashboardQueue").wait_for(
        state="visible",
        timeout=20000,
    )

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
            await page.locator("#authorDashboardQueue").wait_for(
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
                {"source": source, "journal": journal},
            )

            print(f"{source}: {len(records)} manuscripts found.")
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
        browser = await p.chromium.connect_over_cdp(CDP_URL)

        page = await find_scholarone_page(browser, journal)

        print(f"ScholarOne tab found: {journal}")

        # Required queue
        available = await open_queue(
            page,
            "Manuscripts with Decisions",
            required=True,
        )

        author_records = await scrape_current_table(
            page,
            "Manuscripts with Decisions",
            journal,
        )

        # Optional queue
        submitted_records = []

        if await open_queue(
            page,
            "Submitted Manuscripts",
        ):
            submitted_records = await scrape_current_table(
                page,
                "Submitted Manuscripts",
                journal,
            )

        # Optional queue
        coauthored_records = []

        if await open_queue(
            page,
            "Manuscripts I Have Co-Authored",
        ):
            coauthored_records = await scrape_current_table(
                page,
                "Co-Authored",
                journal,
            )

        # Deduplicate by manuscript ID within this journal.
        combined = []
        seen_ids = set()

        all_records = (
            author_records
            + submitted_records
            + coauthored_records
        )

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
        print(
            f"Manuscripts with Decisions: "
            f"{len(author_records)}"
        )
        print(
            f"Submitted Manuscripts: "
            f"{len(submitted_records)}"
        )
        print(
            f"Co-Authored: "
            f"{len(coauthored_records)}"
        )
        print(
            f"Combined unique manuscripts: "
            f"{len(combined)}"
        )
        print(f"Saved to: {RESULTS_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
