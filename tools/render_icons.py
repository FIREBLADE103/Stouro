#!/usr/bin/env python3
"""Render the GUIDO app icons in assets/icons/ from the master SVGs in assets/branding/guido/.

Usage:
    python tools/render_icons.py [--browser PATH]

Uses a local Chromium-based browser (Microsoft Edge or Google Chrome) in
headless mode, so no Python packages are needed. Writes to assets/icons/:
  - icon-192.png, icon-512.png and apple-touch-icon.png (180) from guido-icon.svg
  - icon-maskable-512.png from guido-icon-maskable.svg
and checks that every PNG has the expected pixel size.
"""

from __future__ import annotations

import argparse
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
BRANDING = ASSETS / "branding" / "guido"
ICONS = ASSETS / "icons"
OUTPUTS = [
    ("guido-icon.svg", "icon-192.png", 192),
    ("guido-icon.svg", "icon-512.png", 512),
    ("guido-icon.svg", "apple-touch-icon.png", 180),
    ("guido-icon-maskable.svg", "icon-maskable-512.png", 512),
]
BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]


def find_browser(explicit: str | None) -> str:
    if explicit:
        return explicit
    for candidate in BROWSERS:
        if Path(candidate).exists():
            return candidate
    for name in ("msedge", "google-chrome", "chromium", "chrome"):
        found = shutil.which(name)
        if found:
            return found
    sys.exit("No Edge or Chrome found; pass --browser PATH")


def png_size(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path.name} is not a PNG")
    return struct.unpack(">II", header[16:24])


def render(browser: str, svg: Path, png: Path, size: int, work: Path) -> None:
    page = work / f"{png.stem}.html"
    page.write_text(
        "<!doctype html><html><body style=\"margin:0;overflow:hidden\">"
        f"<img src=\"{svg.as_uri()}\" width=\"{size}\" height=\"{size}\" style=\"display:block\">"
        "</body></html>",
        encoding="utf-8",
    )
    subprocess.run(
        [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--force-device-scale-factor=1", f"--window-size={size},{size}",
         f"--user-data-dir={work / 'profile'}", f"--screenshot={png}", page.as_uri()],
        check=True, capture_output=True, timeout=60,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--browser", help="path to Edge or Chrome")
    args = parser.parse_args()
    browser = find_browser(args.browser)
    failed = False
    with tempfile.TemporaryDirectory() as tmp:
        for svg_name, png_name, size in OUTPUTS:
            png = ICONS / png_name
            render(browser, BRANDING / svg_name, png, size, Path(tmp))
            actual = png_size(png)
            ok = actual == (size, size)
            failed |= not ok
            print(f"{'OK  ' if ok else 'FAIL'} {png_name} {actual[0]}x{actual[1]} (expected {size}x{size})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
