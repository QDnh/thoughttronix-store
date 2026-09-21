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
