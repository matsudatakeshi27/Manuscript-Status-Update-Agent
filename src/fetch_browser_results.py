import json
from playwright.sync_api import sync_playwright
from paths import RESULTS_FILE

CDP_URL = "http://127.0.0.1:18800"

JS = r"""() => {
    const bodyText = document.body?.innerText || "";
    const tables = [...document.querySelectorAll("table")];
    const records = [];
    let foundManuscriptTable = false;

    for (const table of tables) {
        const rows = [...table.querySelectorAll("tr")]
            .map(tr => [...tr.querySelectorAll(":scope > th, :scope > td")]
                .map(cell => (cell.innerText || "").trim()))
            .filter(row => row.length > 0);

        const headerIndex = rows.findIndex(row =>
            /manuscript\s*(id|number|#)/i.test(row.join(" ")) &&
            /title/i.test(row.join(" ")) &&
            /status/i.test(row.join(" "))
        );

        if (headerIndex === -1) continue;

        foundManuscriptTable = true;
        const headers = rows[headerIndex].map(h => h.toLowerCase());

        const idIndex = headers.findIndex(h =>
            /manuscript\s*(id|number|#)/i.test(h)
        );
        const titleIndex = headers.findIndex(h => /title/i.test(h));
        const statusIndex = headers.findIndex(h => /status/i.test(h));

        for (const row of rows.slice(headerIndex + 1)) {
            const manuscript_id = (row[idIndex] || "").trim();
            const title = (row[titleIndex] || "").trim();
            const status = (row[statusIndex] || "").trim();

            if (manuscript_id && title && status) {
                records.push({ manuscript_id, title, status });
            }
        }
    }

    return {
        page_title: document.title,
        is_author_dashboard: /author dashboard/i.test(bodyText),
        found_manuscript_table: foundManuscriptTable,
        records
    };
}"""


def main():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)

        # Find the ScholarOne tab dynamically.
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

        if page is None:
            raise RuntimeError("ScholarOne tab not found.")

        print("ScholarOne tab found.")

        # Navigate to the Author Dashboard.
        clicked = page.evaluate("""
            () => {
                const link = [...document.querySelectorAll('a')]
                    .find(a =>
                        (a.innerText || '').trim() === 'Author'
                    );

                if (!link) return false;

                link.click();
                return true;
            }
        """)

        if not clicked:
            raise RuntimeError("Author navigation link not found.")

        print("Author navigation clicked.")
        page.wait_for_timeout(3000)

        # Extract manuscript information.
        data = page.evaluate(JS)

        if (
            not data.get("found_manuscript_table")
            and not data.get("is_author_dashboard")
        ):
            raise RuntimeError(
                "Could not verify the ScholarOne Author Dashboard. "
                "No results saved."
            )

        records = data.get("records", [])

        RESULTS_FILE.write_text(
            json.dumps(records, indent=2),
            encoding="utf-8"
        )

        print(f"Page: {data.get('page_title')}")
        print(f"Manuscripts found: {len(records)}")
        print(f"Saved to: {RESULTS_FILE}")
        print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
