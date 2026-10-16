#!/usr/bin/env python3
"""Quality gate for Stouro app images. Read-only: never modifies any file.

Usage:
    python tools/check_app_photos.py [city ...]

Checks every file in assets/images/<city>/web/ (all cities by default) and
every image reference in index.html.

FAIL (exit code 1):
  - index.html references an image that does not exist
  - index.html references a non-WebP image under assets/images/
  - a .webp file in a web/ folder that is not a genuine, fully decodable WebP
  - a WebP image wider or taller than 2000 px
  - a WebP image larger than 1 MiB
WARN (exit code 0):
  - a WebP image larger than 500 KiB (review for further optimisation)
  - a WebP image in a web/ folder that index.html does not reference
  - a legacy non-WebP file in a web/ folder that index.html does not reference
    (.gitkeep is ignored)
  - index.html references an app image outside a web/ folder
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

try:
    from PIL import Image
except ImportError:
    sys.exit("error: Pillow is not installed for this Python interpreter.")

REPO_ROOT = Path(__file__).resolve().parent.parent
IMAGES_ROOT = REPO_ROOT / "assets" / "images"
INDEX_HTML = REPO_ROOT / "index.html"

MAX_DIMENSION = 2000
FAIL_BYTES = 1024 * 1024  # 1 MiB
WARN_BYTES = 500 * 1024  # 500 KiB
IGNORED_FILES = {".gitkeep"}

IMAGE_EXTENSIONS = r"webp|jpe?g|png|gif|avif|heic|heif|tiff?|bmp"
# Quoted strings in index.html that end in an image extension.
REFERENCE_PATTERN = re.compile(
    r"""['"`]([^'"`\n<>]+?\.(?:%s))['"`]""" % IMAGE_EXTENSIONS, re.IGNORECASE
)


class Report:
    def __init__(self):
        self.fails: list[str] = []
        self.warns: list[str] = []

    def fail(self, message: str):
        self.fails.append(message)
        print(f"  FAIL  {message}")

    def warn(self, message: str):
        self.warns.append(message)
        print(f"  WARN  {message}")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def path_key(path: Path) -> str:
    """Comparable form of a path (resolved, case-folded on Windows)."""
    return os.path.normcase(str(path.resolve()))


def check_web_folder(web_dir: Path, referenced: set[str] | None, report: Report) -> int:
    """Check every file in one web/ folder. Returns the number of WebP images checked.

    `referenced` is None when index.html is missing; unused-WebP warnings are then skipped.
    """
    checked = 0
    for path in sorted(p for p in web_dir.iterdir() if p.is_file()):
        name = rel(path)
        if path.name in IGNORED_FILES:
            continue
        if path.suffix.lower() != ".webp":
            if referenced is not None and path_key(path) in referenced:
                # The index.html reference check reports this as a failure.
                continue
            report.warn(f"{name}: legacy non-WebP file, not referenced by index.html")
            continue

        checked += 1
        if referenced is not None and path_key(path) not in referenced:
            report.warn(f"{name}: unused WebP, not referenced by index.html")
        size = path.stat().st_size
        try:
            with Image.open(path) as img:
                fmt = img.format
                width, height = img.size
                img.load()  # fully decode to catch truncated/corrupt data
        except Exception as exc:
            report.fail(f"{name}: unreadable image ({type(exc).__name__}: {exc})")
            continue

        if fmt != "WEBP":
            report.fail(f"{name}: has a .webp extension but is actually {fmt}")
            continue
        if max(width, height) > MAX_DIMENSION:
            report.fail(f"{name}: {width}x{height} exceeds {MAX_DIMENSION}px")
        if size > FAIL_BYTES:
            report.fail(f"{name}: {size / 1024:.0f} KiB exceeds 1 MiB")
        elif size > WARN_BYTES:
            report.warn(f"{name}: {size / 1024:.0f} KiB is over 500 KiB; review for further optimisation")
    return checked


def resolve_reference(ref: str) -> Path | None:
    """Map an index.html image string to a file path, or None if it is remote."""
    if re.match(r"^(?:[a-z][a-z0-9+.-]*:|//)", ref, re.IGNORECASE):
        return None  # http(s):, data:, protocol-relative, etc.
    clean = unquote(ref.split("?", 1)[0].split("#", 1)[0])
    clean = clean.lstrip("/")
    while clean.startswith("./"):
        clean = clean[2:]
    if clean.startswith("assets/"):
        return REPO_ROOT / clean
    # curatedPhoto(...) paths are relative to assets/images/, e.g. 'rome/web/x.webp'.
    first = clean.split("/", 1)[0]
    if "/" in clean and (IMAGES_ROOT / first).is_dir():
        return IMAGES_ROOT / clean
    return REPO_ROOT / clean


def collect_references() -> list[tuple[int, str, Path]] | None:
    """Return (line, ref, path) for each local image in index.html, or None if it is missing."""
    if not INDEX_HTML.is_file():
        return None
    text = INDEX_HTML.read_text(encoding="utf-8", errors="replace")
    references = []
    seen = set()
    for match in REFERENCE_PATTERN.finditer(text):
        ref = match.group(1)
        if ref in seen:
            continue
        seen.add(ref)
        path = resolve_reference(ref)
        if path is None:
            continue
        line = text.count("\n", 0, match.start()) + 1
        references.append((line, ref, path))
    return references


def check_index_references(references: list[tuple[int, str, Path]] | None,
                           cities: set[str] | None, report: Report) -> int:
    if references is None:
        report.warn("index.html not found; skipped reference checks")
        return 0
    checked = 0
    for line, ref, path in references:
        try:
            parts = path.resolve().relative_to(IMAGES_ROOT.resolve()).parts
        except ValueError:
            parts = None
        if cities is not None and (not parts or parts[0] not in cities):
            continue

        checked += 1
        label = f"index.html:{line} '{ref}'"
        if not path.is_file():
            report.fail(f"{label}: file not found ({rel(path)})")
        if parts is not None:
            if path.suffix.lower() != ".webp":
                report.fail(f"{label}: app images must be .webp")
            if len(parts) < 3 or parts[1] != "web":
                report.warn(f"{label}: app image is not inside a web/ folder")
    return checked


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Stouro app images (read-only).")
    parser.add_argument("cities", nargs="*", help="city slugs to check (default: all)")
    args = parser.parse_args()

    if not IMAGES_ROOT.is_dir():
        sys.exit(f"error: {rel(IMAGES_ROOT)} not found")

    all_cities = sorted(p.name for p in IMAGES_ROOT.iterdir() if p.is_dir())
    if args.cities:
        unknown = [c for c in args.cities if c not in all_cities]
        if unknown:
            parser.error(f"unknown city folder(s): {', '.join(unknown)}")
    cities = args.cities or all_cities

    report = Report()
    references = collect_references()
    referenced = (None if references is None
                  else {path_key(path) for _, _, path in references})

    images_checked = 0
    for city in cities:
        web_dir = IMAGES_ROOT / city / "web"
        print(f"{city}/web")
        if not web_dir.is_dir():
            report.warn(f"{rel(web_dir)}: folder missing")
            continue
        images_checked += check_web_folder(web_dir, referenced, report)

    print("index.html references")
    refs_checked = check_index_references(
        references, set(args.cities) if args.cities else None, report
    )

    print()
    print(f"Checked {images_checked} WebP image(s) in {len(cities)} city folder(s) "
          f"and {refs_checked} index.html reference(s).")
    if report.fails:
        print(f"RESULT: FAIL ({len(report.fails)} failure(s), {len(report.warns)} warning(s))")
        return 1
    if report.warns:
        print(f"RESULT: PASS WITH WARNINGS ({len(report.warns)} warning(s))")
        return 0
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
