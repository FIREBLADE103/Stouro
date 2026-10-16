# City images

Each city in the app's `places` object (index.html) has its own folder:

```
assets/images/<city>/        original photos (.png, .HEIC, ...), never loaded by the app
assets/images/<city>/web/    optimised WebP copies the app loads
```

- `<city>` is the `places` key in lowercase with spaces as hyphens
  (`Rome` -> `rome`, `Herne Bay` -> `herne-bay`).
- `curatedPhoto(...)` paths are relative to this folder and must point to a
  `.webp` file inside `web/`, e.g.
  `'canterbury/web/canterbury-river-stour-westgate-towers.webp'`.
- There is no shared or central image folder.

## Adding a new city

When you add a city to `places`, also create `assets/images/<city>/web/`.
Git does not track empty folders, so add an empty `.gitkeep` file inside it
until the first optimised image goes in.

```sh
mkdir -p assets/images/<city>/web && touch assets/images/<city>/web/.gitkeep
```

Current cities: `barcelona`, `canterbury`, `herne-bay`, `london`, `rome`.

## Preserving originals

Original photos must be preserved. Keep them in `assets/images/<city>/` and
never edit, overwrite, rename or delete them. Neither tool below modifies
originals: the optimiser only reads them, and the checker is read-only.

## Optimising photos

```sh
python tools/optimize_photos.py <city> <source-folder> [--overwrite]
# e.g. python tools/optimize_photos.py canterbury assets/images/canterbury
```

- Converts each supported image (JPEG, PNG, HEIC/HEIF, WebP, TIFF, BMP)
  directly inside the source folder (not subfolders) to WebP: quality 82,
  method 6, longest side at most 2000 px, aspect ratio kept, camera rotation
  applied.
- Output goes to `assets/images/<city>/web/`, keeping the source name with
  spaces turned into hyphens (`cathedral window.HEIC` -> `cathedral-window.webp`).
- Existing outputs are skipped unless `--overwrite` is passed.
- Uses the local Pillow and pillow-heif packages; no internet needed.

## Checking app images

```sh
python tools/check_app_photos.py            # all cities
python tools/check_app_photos.py rome       # one or more cities
```

Read-only: it never deletes, renames or modifies any image. Exits with code 1
if there is any failure, otherwise 0 (warnings alone do not fail the check).

**Size thresholds.** WebP files over **500 KiB** (512,000 bytes) produce a
warning: they are allowed, but review them for further optimisation, as
nothing is recompressed automatically. Files over **1 MiB** (1,048,576 bytes)
are a hard failure and must be re-exported smaller before they ship.

- **Fail:**
  - `index.html` references an image that does not exist.
  - `index.html` references a non-WebP image under `assets/images/`.
  - A `.webp` file in a `web/` folder is not a genuine, readable WebP image.
  - A WebP image's width or height is over 2000 px.
  - A WebP image is over 1 MiB.
- **Warn:**
  - A WebP image is over 500 KiB.
  - A legacy non-WebP file (e.g. an old `.jpg`) sits in a `web/` folder but
    is not referenced by `index.html`. It is left in place; remove or replace
    it by hand when convenient. (`.gitkeep` is ignored.)
  - `index.html` references an app image outside a `web/` folder.
