import json
import shutil
import subprocess
from pathlib import Path

from paths import RESULTS_FILE, APP_DIR

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
            /manuscript\s*(id|number|#)/i.test(h));
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

    return JSON.stringify({
        page_title: document.title,
        is_author_dashboard: /author dashboard/i.test(bodyText),
        found_manuscript_table: foundManuscriptTable,
        records
    });
}"""

def main():
    openclaw = shutil.which("openclaw")

    if not openclaw:
        raise RuntimeError(
            "OpenClaw was not found. Install OpenClaw and make sure "
            "its executable is available in PATH."
        )

    result = subprocess.run(
        [openclaw, "browser", "evaluate", "--fn", JS],
        capture_output=True,
        text=True,
        cwd=str(APP_DIR.parent)
    )

    if result.returncode != 0:
        raise RuntimeError(f"Browser error: {result.stderr}")

    try:
        response = json.loads(result.stdout.strip())
        data = json.loads(response) if isinstance(response, str) else response
    except (json.JSONDecodeError, TypeError) as e:
        raise RuntimeError(
            f"Could not parse browser response: {result.stdout}"
        ) from e

    if not data.get("found_manuscript_table") and not data.get("is_author_dashboard"):
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
