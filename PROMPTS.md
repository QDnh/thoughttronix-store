# PROMPTS.md — AI Usage Log

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught

## 2026-10-04 — Product images: implementation from the handoff

### Prompts
1. @HANDOFF.md Implement this feature
2. Can you switch SoulSear image from Mark 1 to Tactical Core?
3. Okay. Next, we need to alter the product edit page. The choose file no
   file chosen does not look like a button.
4. It looks clear now.
5. I've already migrated, seeded the database, and committed.
6. Append a session log to PROMPTS.md at the repo root, under today's date,
   newest entry at the top. Record every prompt I gave you this session, in
   order, including any corrections. End the entry with a short summary:
   the outcome, any places where I deviated from a recommended answer or
   asked follow-up questions, and anything that went sideways.

### Summary
- **Outcome:** Implemented the product-images design from `HANDOFF.md`.
  Added `products/images.py` (one processing function that validates an
  upload, crops it to 4:5, resizes it to 800×1000, and saves it as WebP,
  with plain-language errors and a logged catch-all). `Product` gained
  `image` and `image_original` (migration `0004_product_image`), an
  `image_url` property with a placeholder fallback, and file cleanup that
  runs only after a save or delete commits. `ProductForm` takes the upload
  all-or-nothing and offers a remove checkbox with a preview. Fixed the
  missing `enctype="multipart/form-data"` on the product form. Added a
  shared `_product_image.html` partial (4:5 frame, lazy loading, `onerror`
  fallback) for the catalog and detail pages, and redrew the placeholder
  SVGs at 4:5. Configured `MEDIA_ROOT`/`MEDIA_URL`, served media in
  development, and gitignored `media/`. Moved 12 photos to
  `products/seed_images/<slug>.png`; the seed attaches them. Added 26 tests
  in `products/test_images.py` plus an autouse temp-`MEDIA_ROOT` fixture in
  `conftest.py`. The full suite passed (282 tests) and ruff was clean.
  Then the SoulSear photo was moved from Mark I to Tactical Core (with a
  test), and the file input was restyled as `file-input file-input-primary`.
  The user ran `migrate` and `seed` and committed the work themselves.
- **Deviations:** The user changed the provisional SoulSear mapping from
  Mark I to Tactical Core. The agent made several calls the handoff didn't
  settle, and reported them: the "Your image wasn't saved" message shows
  only when the chosen image itself was valid; the decompression-bomb
  message omits the MB figure; cleanup uses a `post_delete` signal so bulk
  deletes are covered; the image fields are hidden from the Django admin;
  EXIF rotation is applied before cropping. The `onerror` fallback is
  inline JavaScript, which conflicts with `docs/FRONTEND.md` ("no
  JavaScript beyond HTMX"); this was flagged but not resolved. The agent
  did not run `migrate`/`seed` (the seed is destructive) or append to
  PROMPTS.md unprompted, since this file's rules forbid that even though
  the handoff asked for it.
- **Sideways:** `HANDOFF.md` was not at the referenced path; it was found
  in `thoughttronix-store/`. Ruff flagged model method order (DJ012) and
  formatting after the first full run; both were fixed. The first CSS
  build skipped as "up to date" and lacked the new classes until forced
  with `--force`. Before that forced rebuild, the file input had no
  DaisyUI styles, so "Choose file" rendered as plain text — the cause of
  the user's third prompt. The default grey button was still faint on the
  night theme, so a primary color modifier was added. The change was not
  checked in a browser by the agent; the user confirmed it looked right.

## 2026-10-04 — Product images: design interview and implementation handoff

### Prompts
1. /grill-me We need to add a feature so real images of the products will be
   on the catalog. Currenty, we only have placeholders there. We have images
   that are located in the product-images folder. These images need to look
   consistent whenever they are displayed. The pages that display the images
   must still respond quickly. Two rules that must be followed: 1, products
   must display either its uploaded image or placeholder. 2, image files will
   be upload via the backoffice; should display an error (which must be in
   plain language) if the image cannot be used by the website; and the file
   must not be accepted and lost if there is an error.
2. Option A.
3. Probably A.
4. No, they have complex backgrounds. Option A seems best for consistency.
5. Option A. Seems best for consistency, and I like the option to add an
   option for a second size later.
6. Let's go with A.
7. Option A seems best. I don't think HEIC is a concern. We might also need a
   default error message.
8. Option A. B won't work because it needs to be plain text. C is an
   absolutely not.
9. I agree. Let's do Option A.
10. Option A.
11. Option A. I believe I need these images committed anyway.
12. (Correction — rejected a tool call that listed seed product names and
    made preview copies of four images) what is this step?
13. I was thinking the same thing. 1: Use the No Text versions. 2: I don't
    know, so assume it is Mark 1 for now. 3: I believe it is.
14. Option A.
15. Go with Option A.
16. I agree. Option A.
17. Option A. I think Option C is too complicated. Option B could be added
    later.
18. /handoff the next session implements the design we just agreed
19. Append a session log to PROMPTS.md at the repo root, under today's date,
    newest entry at the top. Record every prompt I gave you this session, in
    order, including any corrections. End the entry with a short summary: the
    outcome, any places where I deviated from a recommended answer or asked
    follow-up questions, and anything that went sideways.

### Summary
- **Outcome:** A 15-question design interview settled the product-images
  feature: process once at upload (center-crop to 4:5, 800×1000 WebP), keep
  the original alongside, JPEG/PNG/WebP up to 10 MB and at least 800×1000,
  plain-language errors plus a catch-all, all-or-nothing saves with a
  "choose the file again" note, a Remove checkbox, delete-after-commit file
  cleanup, slug-plus-random filenames, product name as alt text, an
  `onerror` placeholder fallback, display on catalog/detail/edit preview
  only, and seed-attached images. The design was written to `HANDOFF.md`
  for the implementing session; no code was changed and no PRD or plan file
  was written.
- **Deviations:** Every recommended option was accepted. The user added
  input beyond the options: asked for a default (catch-all) error message,
  which became Question 7; ruled out HEIC support; accepted 4:5 only
  "probably"; chose "No Text" image variants; and assigned the SoulSear
  image to Mark I provisionally because they were unsure. Thumbnails in the
  back-office list were deferred as a later follow-up.
- **Sideways:** Before Question 11 the agent ran a command to list product
  names and make preview copies of four ambiguous images without first
  saying what it was for; the user rejected it and asked "what is this
  step?". The agent explained and asked the user about the mappings
  directly instead. While exploring, the agent found an existing bug: the
  back-office product form lacks `enctype="multipart/form-data"`, so file
  uploads would be silently dropped; fixing it is part of the handoff.

## 2026-09-27 — Discount codes: design interview, checkout Apply flow, and a Discounts back-office tab

### Prompts
1. /grill-me A customer should be able to type in a discount code at
   checkout, and the order total should drop according to the discount.
   Typing in an expired code should display a message to the customer saying
   the discount code is expired, rather than a broken page. If a code
   expires, it should not change an orders that have already used it. The
   discount code system must be able to support both order-wide discounts
   and discounts limited to specific products.
2. Let's go with Option 1. I like that I have the option to add "amount off"
   code functionality later, if needed.
3. Option 2. I think the customer should see it before committing to the
   purchase. They might have multiple codes they want to compare before the
   purchase.
4. Let's go with Option 1.
5. Probably Option 1. I was given the example: 50% off Seraphine for a
   limited time.
6. Definitely Option 2.
7. The prompt I was given said "the plan is seasonal promotions." Which fits
   that best?
8. Yes, Option 2 with expires_at required.
9. I agree, Option 3 sounds better.
10. Option 1.
11. Option 1.
12. Option 1 sounds best. One of the prompts I got was: "Marketing will
    create and retire codes themselves, without filing a ticket with
    engineering."
13. I agree. I think we have the right logic with the prompt I was given.
    Option 3 would be most convenient.
14. This was left to my discretion. I agree, I think Option 1 would be best.
15. I think this looks good. Implement this feature.
16. *(Correction, after rejecting a combined command that would have run
    `ruff format` and then migrated and seeded a scratch database through a
    temporary settings file)* Explain the scratchpad edit.
17. Run the scratch database check
18. yes, run ruff format
19. Will the rule in staff form rather than the model's clean be an issue?
20. Okay, migrate.
21. Should I have "git add ." or "git add -A"?
22. I think there is a problem in the backoffice. I'm logged into admin and I
    am on /backoffice/discounts/4/edit/. The "Products" selection is not
    displayed correctly.
23. Okay, I see. The problem is that the options are listed horizontally.
    The text of each option is not able to be all on one line.
24. There we go. Much better. The products are listed vertically and can be
    read clearly.
25. Append a session log to PROMPTS.md at the repo root, under today's date,
    newest entry at the top. Record every prompt I gave you this session, in
    order, including any corrections. End the entry with a short summary:
    the outcome, any places where I deviated from a recommended answer or
    asked follow-up questions, and anything that went sideways.

### Summary
- **Outcome:** A 12-question design interview settled these decisions:
  - Codes are percentage-off only.
  - An HTMX Apply button previews the discount, and `place_order` checks
    the code again when the order is placed.
  - One code per order.
  - A code covers either the entire order or specific products, chosen by
    an explicit `applies_to` field.
  - Each code runs from a `starts_at` time to a required `expires_at` time.
  - Discounts are snapshotted per line, rounded half-up for each line and
    then summed.
  - A code that matches nothing in the cart is rejected with its own
    message.
  - Codes are managed in a back-office Discounts tab, with an "End now"
    button, and Delete only for codes no order has used.
  - No usage limits.

  What was built:
  - **Model and migration:** a `DiscountCode` model with a
    `for_checkout()` queryset method, the one place all four customer
    messages are written. Snapshot fields on `Order` and `OrderItem`.
    Migration `orders/0003_discount_codes.py` fills `subtotal` in from
    `total` on existing orders.
  - **Services:** `quote()` and a live `coupon_code` seam in
    `orders/services.py`.
  - **Forms:** `DiscountEntryForm` for checkout and `DiscountCodeForm` for
    staff.
  - **Pages and views:** the checkout summary partial with Apply, the
    discount shown on the order detail and confirmation pages, and the
    Discounts tab (list with a status filter and empty states, create/edit,
    End now, delete-if-unused).
  - **Seed and dashboard:** four demo codes in the seed, one in each state.
    `top_products` on the dashboard now subtracts line discounts.

  Verification:
  - The full suite passed, 256 tests, before the final format and CSS
    changes. After those changes only 79 product and discount tests were
    rerun.
  - `ruff check` and `ruff format --check` are clean, and
    `makemigrations --check` finds no missing migrations.
  - The seed ran twice with identical results on a scratch database, which
    was then deleted.
  - The local database was migrated but not reseeded.

  Nothing is committed.
- **Deviations:**
  - The user took the recommended answer on every question except Q6. The
    agent first recommended `expires_at` only. The user asked which option
    fits "seasonal promotions," and the agent changed its recommendation to
    a `starts_at` + `expires_at` window with `expires_at` required, which
    the user accepted.
  - Two parts of the approved design were changed during implementation,
    and only reported afterwards:
    - Code validation went into a separate `DiscountEntryForm` instead of a
      `clean_discount_code` on `CheckoutForm`, because the PRD and an
      existing test forbid `clean*` methods on `CheckoutForm`.
    - The "specific products need at least one product" rule went into the
      staff form instead of the model's `clean()`, because a many-to-many
      can't be read on an unsaved object.
  - The user asked follow-up questions about the scratchpad edit, whether
    the form-level rule is a risk, and `git add .` versus `git add -A`.
    The answer to the last one was neither: stage by path so the
    unrelated, modified `bash.exe.stackdump` stays out.
- **Sideways:**
  - The user rejected a single command that combined `ruff format` with
    migrating and seeding a scratch database, and asked for an explanation
    first. The steps were then run separately with the user's approval.
  - On the discount edit page, the Products multi-select laid its options
    out horizontally. DaisyUI's `.select` sets `display: inline-flex`. The
    bug was already in the shared `StyledModelForm` and also affected the
    product form's Tags field. It was fixed by adding `block` to the
    multi-select class in `products/forms.py`. The user caught it in the
    browser, because the tests only check the HTML.
  - Not raised during the session: the discount input is attached to the
    checkout form, so pressing Enter in it submits the whole checkout
    instead of pressing Apply. An invalid code still can't place an order,
    but Enter doesn't do what Apply does.

## 2026-09-20 — Add Product.is_featured with a "Featured" badge and tests

### Prompts
1. Add an is_featured field to Product. It should be a boolean field and
   defaults to not-featured.
2. *(Correction, after rejecting a combined "migrate + run the test suite"
   command)* migrate
3. *(After rejecting a `showmigrations` check)* Add a badge for is_featured.
   A featured product should show the "Featured" badge on both the catalog
   listing and the product detail page.
4. Write tests for the badge and add a fixture to conftest.py
5. *(After rejecting a full-suite `pytest` run)* Append a session log to
   PROMPTS.md at the repo root, under today's date, newest entry at the top.
   Record every prompt I gave you this session, in order, including any
   corrections. End the entry with a short summary: the outcome, any places
   where I deviated from a recommended answer or asked follow-up questions,
   and anything that went sideways.

### Summary
- **Outcome:** Added `is_featured = models.BooleanField(default=False)` to
  `Product` and generated `products/migrations/0003_product_is_featured.py`.
  Added a solid `badge-secondary` "Featured" badge to the product cards in
  `templates/products/catalog.html` and to the status badge row in
  `templates/products/detail.html`. On the detail page, that row became a
  flex row with a gap. Added a `featured_product` fixture to `conftest.py`
  and five tests to `products/tests.py`: the default is not featured, and
  the badge shows or stays hidden on both the catalog and detail pages. The
  five badge tests pass (`pytest -k featured`). The full suite was not run.
- **Deviations:** The agent tried to run `migrate` and the full test suite
  in one command. The user rejected it and asked for `migrate` on its own.
  The user also rejected the agent's follow-up `showmigrations` check and
  the full-suite test run. No clarifying questions were asked. The agent
  offered to add `is_featured` to the back-office product form and the seed
  data, and the user didn't take that up.
- **Sideways:** `migrate` reported "No migrations to apply" right after
  0003 was generated, which is unexpected for a new migration. It was not
  confirmed whether 0003 is applied to the local database. The field is not
  on the back-office form yet, so for now products can only be featured
  through the Django admin or the shell.
