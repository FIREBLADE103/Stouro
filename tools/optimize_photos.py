#!/usr/bin/env python3
"""Convert original photos into app-ready WebP images for a Stouro city.

Usage:
    python tools/optimize_photos.py <city-slug> <source-folder> [--overwrite]

Example:
    python tools/optimize_photos.py canterbury assets/images/canterbury

Reads every supported image directly inside <source-folder> (not subfolders)
and writes a WebP copy to assets/images/<city-slug>/web/. Source images are
only ever read; they are never modified, moved or deleted. Existing outputs
are skipped unless --overwrite is given.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("error: Pillow is not installed for this Python interpreter.")

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIF_AVAILABLE = True
except ImportError:
    HEIF_AVAILABLE = False

REPO_ROOT = Path(__file__).resolve().parent.parent
IMAGES_ROOT = REPO_ROOT / "assets" / "images"

WEBP_QUALITY = 82
WEBP_METHOD = 6
MAX_DIMENSION = 2000

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}
HEIF_EXTENSIONS = {".heic", ".heif"}
if HEIF_AVAILABLE:
    SUPPORTED_EXTENSIONS |= HEIF_EXTENSIONS

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def output_name(source: Path) -> str:
    """Keep the source name, but trim it and turn runs of spaces into hyphens.

    'cathedral window 1  .HEIC' -> 'cathedral-window-1.webp'
    'IMG_2114.HEIC'             -> 'IMG_2114.webp'
    """
    stem = re.sub(r"\s+", "-", source.stem.strip())
    stem = re.sub(r"-{2,}", "-", stem).strip("-.")
    return (stem or "image") + ".webp"


def convert(source: Path, destination: Path) -> tuple[tuple[int, int], tuple[int, int]]:
    """Write an optimised WebP copy of source to destination.

    Returns (original_size, output_size). The file is written to a temporary
    name first so a failed conversion never leaves a partial output behind.
    """
    with Image.open(source) as img:
        original_size = img.size
        img = ImageOps.exif_transpose(img)  # bake in camera rotation
        has_alpha = img.mode in ("RGBA", "LA", "PA") or (
            img.mode == "P" and "transparency" in img.info
        )
        img = img.convert("RGBA" if has_alpha else "RGB")
        lanczos = getattr(Image, "Resampling", Image).LANCZOS  # Pillow < 9.1 fallback
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), lanczos)

        save_kwargs = {"format": "WEBP", "quality": WEBP_QUALITY, "method": WEBP_METHOD}
        icc_profile = img.info.get("icc_profile")
        if icc_profile:
            save_kwargs["icc_profile"] = icc_profile

        fd, tmp_name = tempfile.mkstemp(
            prefix=".tmp-", suffix=".webp", dir=destination.parent
        )
        os.close(fd)
        tmp_path = Path(tmp_name)
        try:
            img.save(tmp_path, **save_kwargs)
            os.replace(tmp_path, destination)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
        return original_size, img.size


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert original photos to app-ready WebP images "
        f"(quality {WEBP_QUALITY}, max {MAX_DIMENSION}px, method {WEBP_METHOD})."
    )
    parser.add_argument("city", help="city slug, e.g. rome or herne-bay")
    parser.add_argument("source", type=Path, help="folder containing original photos")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace existing WebP outputs (default: skip them)",
    )
    args = parser.parse_args()

    if not SLUG_PATTERN.match(args.city):
        parser.error(
            f"city slug {args.city!r} must be lowercase letters, digits and hyphens "
            "(e.g. 'herne-bay')"
        )

    source_dir = args.source.resolve()
    if not source_dir.is_dir():
        parser.error(f"source folder not found: {args.source}")

    dest_dir = IMAGES_ROOT / args.city / "web"
    if source_dir == dest_dir.resolve():
        parser.error("source folder must not be the web/ output folder")

    if not HEIF_AVAILABLE:
        print("warning: pillow-heif not available; .heic/.heif files will be skipped")

    files = sorted(p for p in source_dir.iterdir() if p.is_file())
    if not files:
        print(f"No files found in {source_dir}")
        return 0

    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"Source:      {source_dir}")
    print(f"Destination: {dest_dir}")
    print()

    counts = {"converted": 0, "skipped": 0, "unsupported": 0, "failed": 0}
    claimed: dict[str, Path] = {}

    for source in files:
        ext = source.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            reason = (
                "HEIC/HEIF needs pillow-heif" if ext in HEIF_EXTENSIONS else "not a supported image type"
            )
            print(f"UNSUPPORTED  {source.name}  ({reason})")
            counts["unsupported"] += 1
            continue

        name = output_name(source)
        key = name.lower()  # Windows/macOS filesystems are case-insensitive
        if key in claimed:
            print(f"SKIPPED      {source.name}  (output name {name} already used by {claimed[key].name})")
            counts["skipped"] += 1
            continue
        claimed[key] = source

        destination = dest_dir / name
        if destination.exists() and not args.overwrite:
            print(f"SKIPPED      {source.name} -> {name}  (already exists; use --overwrite to replace)")
            counts["skipped"] += 1
            continue

        try:
            (ow, oh), (nw, nh) = convert(source, destination)
        except Exception as exc:  # report and carry on with the rest
            print(f"FAILED       {source.name}  ({type(exc).__name__}: {exc})")
            counts["failed"] += 1
            continue

        size_kb = destination.stat().st_size / 1024
        print(f"CONVERTED    {source.name} -> {name}  {ow}x{oh} -> {nw}x{nh}, {size_kb:.0f} KB")
        counts["converted"] += 1

    print()
    print(
        "Summary: {converted} converted, {skipped} skipped, "
        "{unsupported} unsupported, {failed} failed".format(**counts)
    )
    if counts["converted"]:
        print("Next: run python tools/check_app_photos.py to check the results.")
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
