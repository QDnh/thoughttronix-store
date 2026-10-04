# Handoff — Product images

**Next session's job:** implement the product-images design below. It was
agreed with the user in a `/grill-me` session (2026-10-04). No PRD or plan
file exists for it yet — this document is the only written record of the
design, so treat it as the spec.

## Starting state

- Branch `main`. Uncommitted: `pyproject.toml` / `uv.lock` add
  `pillow>=12.3.0` (needed — keep it), and an untracked `product-images/`
  folder holding the 13 source PNGs (~1.6–2.4 MB each, mostly ~1122×1402).
- Nothing has been implemented yet.
- Read before starting (per `CLAUDE.md`): `docs/ARCHITECTURE.md`,
  `docs/FRONTEND.md`, `docs/TESTING.md`. Earlier design history:
  `prd/core-platform.md`, `plans/core-platform.md`.

## Goal and the user's two hard rules

Replace category placeholders with real product images on the catalog,
keeping images visually consistent and pages fast.

1. Every product displays either its uploaded image or its placeholder —
   never a broken image.
2. Images are uploaded in the back office. An unusable file shows a
   **plain-language** error, and a file is never silently accepted-and-lost.

## Agreed design

### Model and storage
- `Product` gains two optional fields: `image` (processed, the only one
  served) and `image_original` (the exact upload, kept so sizes/crops can be
  regenerated later without re-uploading).
- Add `MEDIA_ROOT` / `MEDIA_URL` to `config/settings.py`; serve media in dev
  via `config/urls.py`. Add `media/` to `.gitignore`. There is no production
  deployment config in the project, so dev serving is enough.
- Filenames: `products/<slug>-<short random>.webp` and
  `products/originals/<slug>-<short random>.<ext>` — a new name on every
  upload (cache-safe, compatible with delete-after-commit).

### Processing (once, at upload)
- Center-crop to **4:5** (`ImageOps.fit`), resize to **800×1000**, save as
  **WebP**. One size only; a second size may be added later from the
  originals. Keep the 4:5 / 800×1000 values as single constants (user said
  "probably" 4:5 — it should be easy to change).
- Put processing in one reusable function (e.g. `products/images.py`) shared
  by the back-office form and the `seed` command.

### Validation (all messages plain language, shown on the image field)
- Formats: JPEG, PNG, WebP. SVG always rejected. HEIC not supported (user
  said not a concern).
- Max 10 MB. Min 800×1000 pixels.
- Example wording agreed:
  - "This file isn't an image we can read. Please upload a JPEG, PNG, or WebP picture."
  - "This image is too large (14.2 MB). Please upload one smaller than 10 MB."
  - "This image is too small (640 × 480 pixels). Please upload one at least 800 × 1000 pixels so it looks sharp on the site."
- Decompression bomb → the "too large" message.
- Any other unexpected processing error → catch-all
  "We couldn't process this image. Please try saving it again as a JPEG or
  PNG, or try a different picture." and log the real exception. Never show
  technical text; never let it 500.

### Error handling / "not accepted and lost"
- All-or-nothing: any form error saves nothing; the product's current image
  stays; text fields re-fill; if a file had been chosen, show
  "Your image wasn't saved. Please choose the file again." (browsers cannot
  re-fill file inputs).
- **Existing bug to fix:** `templates/products/manage_product_form.html`
  lacks `enctype="multipart/form-data"`, so files are silently dropped. Fix
  it and cover it with a test.

### Replace / remove / delete
- Use Django's `ClearableFileInput`, checkbox relabelled
  "Remove image (show the placeholder instead)", plus a preview of the
  current image on the edit form. Clear + new file together → Django's
  standard conflict error.
- Old processed + original files are deleted only after a successful save,
  via `transaction.on_commit` — on replace, remove, and product delete.

### Display
- `Product.image_url` property: uploaded image URL, else
  `static(category.placeholder_image)`.
- One shared template partial (used by `templates/products/catalog.html`
  and `templates/products/detail.html`, which currently each have a raw
  `<img src="{% static product.category.placeholder_image %}">`): 4:5 frame
  (`aspect-ratio` + `object-fit: cover`), `loading="lazy"`,
  `alt="{{ product.name }}"`, and an `onerror` swap to the placeholder when
  the file is missing.
- Redraw the six placeholder SVGs in `assets/images/placeholders/`
  (currently 400×300) at 4:5.
- Scope: catalog/category grid, detail page, edit-form preview only.

### Seed
- Move images to `products/seed_images/<product-slug>.png` and commit them.
  `products/management/commands/seed.py` attaches them through the same
  processing function, and clears old media files when it wipes the catalog.
- File → product mapping (use the "No Text" variant where two exist):

  | Source file | Product |
  |---|---|
  | Calm Collar GPT Man.png | Calm Collar |
  | CrowdCalm Array No Text.png | CrowdCalm Array |
  | DreamWeaver Matrix GPT 3.png | DreamWeaver |
  | Hush GPT No Text.png | Hush |
  | MindSync Duo.png | MindSync Duo |
  | MindSync GPT 2.png | MindSync |
  | MoodSet GPT No Text.png | MoodSet |
  | RecallPro.png | RecallPro |
  | Seraphine GPT Text.png | Seraphine |
  | SoulSear No Text.png | SoulSear Mark I (provisional — user unsure) |
  | SyncRest GPT No Text.png | SyncRest |
  | Veil GPT Text.png | Veil |

  `SyncRest GPT Text.png` is unused. Confirm slugs against `seed.py`.

### Tests
- Follow `docs/TESTING.md`. Point `MEDIA_ROOT` at a temp dir in tests so
  nothing is written to the real `media/`. Cover each validation message,
  all-or-nothing behaviour, enctype, remove checkbox, on-commit cleanup,
  `image_url` fallback, and seed attachment.

## Explicitly out of scope (possible follow-ups)
Back-office list thumbnails; a second image size; real alt-text field;
images in cart/checkout/order history; confirming the SoulSear product.

## Working with this user
- They are a beginner; explain steps plainly. They interrupted an
  unexplained preview command last session — say what a command does before
  running anything non-obvious.
- Append an entry to `PROMPTS.md` (never rewrite history).
- Commit only when asked.

## Suggested skills
- `run` — launch the dev server to see images on the catalog and test an upload.
- `code-review` — review the diff before committing.
- `simplify` — tidy the change after it works.
- `grill-me` — only if a new design question comes up that this doc doesn't settle.
