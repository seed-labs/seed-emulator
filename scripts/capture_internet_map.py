#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture a screenshot and metadata for a live SEED Internet Map page.")
    parser.add_argument("--url", default="http://127.0.0.1:8080/", help="Page URL to open.")
    parser.add_argument(
        "--out-dir",
        default="/tmp/seed-page-evidence",
        help="Directory where screenshot and metadata will be written.",
    )
    parser.add_argument(
        "--wait-for",
        default="networkidle",
        choices=["load", "domcontentloaded", "networkidle"],
        help="Playwright wait_until mode for page.goto().",
    )
    parser.add_argument("--timeout-ms", type=int, default=30000, help="Page load timeout in milliseconds.")
    parser.add_argument("--full-page", action="store_true", help="Capture a full-page screenshot.")
    args = parser.parse_args()

    run_dir = Path(args.out_dir).expanduser().resolve() / _timestamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = run_dir / "page.png"
    metadata_path = run_dir / "page.json"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 960})
        response = page.goto(args.url, wait_until=args.wait_for, timeout=args.timeout_ms)
        page.screenshot(path=str(screenshot_path), full_page=bool(args.full_page))

        metadata = {
            "requested_url": args.url,
            "final_url": page.url,
            "title": page.title(),
            "status": response.status if response is not None else None,
            "ok": response.ok if response is not None else None,
            "wait_for": args.wait_for,
            "timeout_ms": args.timeout_ms,
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "screenshot": str(screenshot_path),
        }
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        browser.close()

    print(json.dumps({"run_dir": str(run_dir), "metadata": str(metadata_path), "screenshot": str(screenshot_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
