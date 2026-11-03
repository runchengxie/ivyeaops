"""Verify reliability fixes using the real App harness and an isolated browser."""
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    base = "http://127.0.0.1:5201"
    results = {}
    with sync_playwright() as playwright:
        edge = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe"
        browser = playwright.chromium.launch(headless=True, executable_path=str(edge))
        for scenario in ("transient", "recover", "network", "denied"):
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"{base}/?r=/dashboard&authcase={scenario}")
            if scenario in ("recover", "network"):
                notice = page.get_by_text("暂时连不上服务器", exact=True)
                notice.wait_for(timeout=25000)
                assert page.url.split("?")[0].endswith("/dashboard")
                assert notice.evaluate("e => getComputedStyle(e).fontSize") == "16px"
                if scenario == "network":
                    assert not errors, errors
                    context.close()
                    results[scenario] = "offline, no login navigation"
                    continue
                page.evaluate("window.__harnessAuthRecovered = true")
            if scenario == "denied":
                page.wait_for_url("**/login", timeout=10000)
            else:
                page.get_by_text("Demo product", exact=False).first.wait_for(timeout=30000)
                assert page.url.split("?")[0].endswith("/dashboard")
                if scenario == "recover":
                    assert page.get_by_text("暂时连不上服务器", exact=True).count() == 0
                with page.expect_download() as download:
                    page.evaluate('''async () => {
                        const source = performance.getEntriesByType('resource').map(r => r.name).find(u => u.includes('/src/api/client.ts'));
                        const prefix = source.slice(0, source.indexOf('/api/client.ts'));
                        const { saveText } = await import(prefix + '/lib/saveBlob.ts');
                        saveText('synthetic report', 'report.md');
                    }''')
                assert download.value.suggested_filename == "report.md"
                assert Path(download.value.path()).read_text() == "synthetic report"
            assert not errors, errors
            results[scenario] = "passed"
            context.close()
        browser.close()
    print(json.dumps(results))


if __name__ == "__main__":
    main()
