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

## 2026-10-19 — Product Reviews: Phase 4 (staff moderation in place)

### Prompts
1. /implement @prd/product-reviews.md @plans/product-reviews.md Phase 4.
2. (Asked whether to run /tdd) Do you think it is needed here?
3. (Given a recommendation to skip it) No, run tdd but only on what you
   think we should run it for.
4. (Shown two TDD behaviors) Yes, approved, go ahead
5. (Shown the RED test for the staff edit rule) I believe so.
6. (Asked whether to write the second test as a regression guard) Yes
7. (Asked whether to continue with the rest of the phase) Yes, continue.
8. Looks like everything works. Continue
9. (Asked whether to append PROMPTS.md and whether to commit) Yes, append
   it; Yes, commit
10. (Asked for a commit title) Complete Product Reviews Phase 4

### Summary
- **Outcome:** Built Phase 4 of `plans/product-reviews.md`.
  `editable_by` now returns every review for staff. `Review.edit(editor,
  *, comment, rating=None)` branches on authorship: the author changes
  the rating and comment and clears the staff flag, while anyone else
  (only staff get past `editable_by`) changes only the comment, has any
  rating ignored, and sets the flag, so the card reads "Edited by staff".
  `ReviewForm` takes an `editor` and drops the rating field when staff
  edit someone else's review. The fields partial hides the stars in that
  case, and the card's edit mode reads "Moderate this review" with a note
  that the rating stays. Staff see Edit and Delete on every card. 11 new
  tests. 480 tests pass, and ruff is clean.
- **Deviations:** Asked whether TDD was needed, the agent recommended
  skipping it and writing the staff edit rule test first by hand. The
  user overrode this and asked for /tdd scoped to what the agent judged
  worthwhile. The agent picked two behaviors: the staff edit rule, which
  went RED on the rating assertion and then GREEN, and a staff member
  editing their own review. The agent flagged in advance that the second
  would pass immediately, and the user accepted it as a regression guard.
- **Sideways:** The second TDD cycle never went RED, because the first
  cycle's author-first check already covered it. The agent said so
  instead of forcing a failure. The first draft of the moderation heading
  used the author's display name, which read awkwardly with the
  "Verified customer" fallback. It was changed to "Moderate this review"
  before the tests ran.

## 2026-10-19 — Product Reviews: Phase 3 (authors edit and delete their own review)

### Prompts
1. /implement @prd/product-reviews.md @plans/product-reviews.md Phase 3.
2. (Asked whether to run /tdd) Do you think tdd for this step is necessary?
3. (Asked again, with a recommendation to skip) Skip TDD (Recommended)
4. what is the pk for mindsync?
5. Ah, I see it now. Thank you. Everything looks good. Continue.
6. (Asked whether to append PROMPTS.md and whether to commit) Yes, append
   it; Yes, commit
7. Complete Product Reviews Phase 3

### Summary
- **Outcome:** Built Phase 3 of `plans/product-reviews.md`. The review
  manager gains `editable_by(user)`, which returns only the user's own
  reviews (the staff branch waits for Phase 4). `Review.edit(editor, *,
  rating, comment)` saves the new values, clears the staff flag, and
  refreshes the updated timestamp, which makes the card read "Edited".
  Four new endpoints, all signed-in and looked up through `editable_by`
  (so another customer gets a 404): `reviews:edit` and `reviews:cancel`
  (GET) swap one card between edit and display mode, and `reviews:update`
  and `reviews:delete` (POST) re-render the whole section. An invalid
  update sends back just the card in edit mode, with errors and input
  kept, using an `HX-Retarget` header. The stars and comment box moved
  into a shared `_review_fields.html` partial used by both the create
  form and the card's edit mode, and edit forms get per-review field ids.
  The author's card shows Edit and Delete, with Delete behind
  `hx-confirm="Delete this review?"`. 25 new tests cover every acceptance
  criterion. 469 tests pass, and ruff is clean.
- **Deviations:** Instead of answering yes or no to running /tdd, the
  user asked whether TDD was necessary. The agent recommended skipping it,
  since the phase's logic is small and the rest follows Phase 2's
  patterns, and suggested Phase 4's staff edit rule as a better TDD
  candidate. The user accepted. During manual verification the user asked
  for MindSync's pk. The agent explained that the edit URL needs the
  review's pk, not the product's, and looked up both (product 586,
  review 8).
- **Sideways:** The first shell lookup of the pk failed because a
  one-line `-c` script with a list comprehension didn't run under
  `manage.py shell`. A multi-line script worked. Nothing went wrong in
  the implementation, and every test passed on the first run.

## 2026-10-19 — Product Reviews: Phase 2 (write a review)

### Prompts
1. /implement @prd/product-reviews.md @plans/product-reviews.md Phase 2.
2. (Asked whether to run /tdd) Yes, run /tdd
3. Approved, go ahead
4. Approved, go ahead
5. yes
6. yes
7. yes
8. yes
9. yes
10. Looks good. Continue.
11. (Asked whether to append PROMPTS.md and whether to commit) Yes, append
    it; Yes, commit
12. Complete Product Reviews Phase 2

### Summary
- **Outcome:** Built Phase 2 of `plans/product-reviews.md`. `Order` gains
  its first custom queryset, with `has_delivered(user, product)`. The
  review manager gains `can_review` (signed in, a delivered purchase, and
  no review yet) and `own_review`, and the queryset gains `pinned_for`
  (the viewer's own review first, then newest first). A `ReviewForm`
  (no default rating, whitespace-only comments rejected) posts to the new
  `reviews:create` endpoint. The endpoint requires sign-in, is POST-only,
  finds unavailable products, re-checks `can_review` on submit, and
  catches a unique-constraint race so it never returns a 500. A shared
  `section_context()` feeds both `ProductDetailView` and the create
  response, so the section renders the same way on first load and after
  HTMX swaps. Between the summary and the list it now shows the form, a
  sign-in link with `next` back to the product, or the "only customers
  who've received this product" message. Three behaviors were built
  test-first with /tdd, each approved at RED and GREEN: the
  delivered-purchase check, `can_review`, and the double submit. A new
  `order_with` fixture in `conftest.py` builds one-line orders. Regular
  tests cover the rest of the acceptance criteria. 443 tests pass, and
  ruff is clean.
- **Deviations:** None. Every recommendation was accepted as proposed,
  and no follow-up questions were asked.
- **Sideways:** At the GREEN step of the double-submit test, the agent
  noted that the re-check alone leaves a gap. Two simultaneous requests
  can both pass `can_review` before either saves. The fix wraps the save
  in `transaction.atomic()` and catches `IntegrityError`, tested by
  patching `can_review` to true while a review already exists. Six
  viewer-state tests first failed because they expected an HTML-escaped
  apostrophe in the not-received message. Literal template text isn't
  escaped, so the test constant was corrected. A local import slipped
  into `reviews/views.py` and was moved to the top before any test ran.
  One test run passed the tool's 2-minute limit and finished in the
  background.

## 2026-10-18 — Product Reviews: Phase 1 (read-only reviews section)

### Prompts
1. /implement @prd/product-reviews.md @plans/product-reviews.md Phase 1.
2. (Asked whether to run /tdd) Yes, run /tdd
3. yes, go ahead
4. Yes
5. I agree.
6. Yes
7. Yes
8. Yes
9. Yes
10. Continue
11. (Asked whether to append PROMPTS.md and whether to commit) Yes, append
    it; Yes, commit
12. Complete Product Reviews Phase 1

### Summary
- **Outcome:** Built Phase 1 of `plans/product-reviews.md`. A new `reviews`
  app holds the `Review` model (author and product cascade, a 1–5 rating,
  a comment capped at 2,000 characters, a backdatable `created_at`, an
  `updated_at` that starts equal to it, an edited-by-staff flag, and a
  unique author–product constraint), its migration, and its admin
  registration. `User.display_name()` returns "Casey M." or "Verified
  customer". `ProductDetailView` passes the reviews and the summary to a
  new section partial and a card partial on every product page,
  unavailable ones included. Three behaviors were built test-first with
  /tdd, each approved at RED and GREEN: the one-query rating summary,
  the display name, and the "Edited" / "Edited by staff" label. Regular
  tests cover the rest of the acceptance criteria. 416 tests pass, and
  ruff is clean.
- **Deviations:** None. The user approved the three TDD behaviors and
  every test as proposed. The agent offered to pin the one-name cases of
  the display name (first name only shows "Casey", last name only falls
  back to "Verified customer"), and the user didn't take it up, so those
  branches are implemented but untested.
- **Sideways:** The first full-suite run took more than the default
  two-minute timeout and finished in the background, so later runs used
  a longer timeout. A test first built its date with `timezone.datetime`
  and `timezone.UTC`, which only work through a re-export in
  `django.utils.timezone`. The agent switched to the `datetime` module
  before the final run, and `ruff format` then reformatted the test file.
  No test or assertion changed after its approval.

## 2026-10-18 — Product Reviews: implementation plan

### Prompts
1. /prd-to-plan @prd\product-reviews.md
2. Yes.
3. Append a session log to PROMPTS.md at the repo root, under today's date,
   newest entry at the top. Record every prompt I gave you this session, in
   order, including any corrections. End the entry with a short summary:
   the outcome, any places where I deviated from a recommended answer or
   asked follow-up questions, and anything that went sideways.

### Summary
- **Outcome:** Wrote `plans/product-reviews.md`. A new `reviews` app sits at
  the site root, with the URLs `reviews/create/<product pk>/` and
  `reviews/<review pk>/{edit,cancel,update,delete}/`. The plan has five
  vertical slices: (1) a read-only reviews section on the product page,
  (2) writing a review, covering the Delivered-purchase check,
  `can_review`, and every viewer state, (3) authors editing and deleting
  their own review, (4) staff moderation in place, and (5) seeded demo
  reviews. The outline was kept as first proposed.
- **Deviations:** None. The agent offered to split Phase 2 or to merge
  Phases 3 and 4, and the user took neither option and approved the
  breakdown as proposed.
- **Sideways:** The agent asked two questions at once ("Does the
  granularity feel right?" and "Should any phases be merged or split?"),
  so the one-word reply "Yes" could be read either way. The agent took it
  as approval of the unchanged outline and wrote the plan, then said so
  and offered to show a revised outline before changing the file if that
  was the wrong reading. No correction followed.

## 2026-10-18 — Product Reviews: design interview and PRD

### Prompts
1. /grill-me We need to create a feature that allows customers to leave
   product reviews. Requirements: customers must only be able to leave one
   review per product; reviews consist of a rating and written comment;
   customers must only be able to leave a review if they have actually
   purchased the product; the only customer who may be allowed to edit and
   delete the review is the customer who made it; staff must be able to
   edit and delete any review; creating, editing, or deleting a review must
   update smoothly without a reload.
2. (Q1, what counts as purchased) Option B
3. (Q2, what happens if eligibility is lost later) Option A
4. (Q3, rating scale) Option A
5. (Q4, comment rules) Option A
6. (Q5, which app) Option A
7. (Q6, where the purchase check lives) Option C
8. (Q7, behavior when a user or product is deleted) Option A
9. (Q8, where staff moderate) Option A
10. (Q9, what staff can edit) Option C
11. (Q10, edit labels over time) Option B
12. (Q11, what people who can't review see) Option A
13. (Q12, rating summary) Option B
14. (Q13, HTMX swap strategy) Option A
15. (Q14, delete confirmation) Option A
16. (Q15, how edit/delete find a review and reject outsiders) Option A
17. (Q16, list ordering and pagination) Option A
18. (Q17, how the reviewer is named) Option B
19. (Q18, seed data) Option A
20. (Q19, confirm the out-of-scope list) Option A
21. /to-prd

### Summary
- **Outcome:** A 19-question design interview, followed by
  `prd/product-reviews.md` (42 user stories). No code was written, and
  nothing was committed. Key decisions:
  - "Purchased" means the product is in one of the user's Delivered orders.
    It's checked only when a review is created. After that, the author can
    always edit or delete their review.
  - Reviews are a required 1–5 whole-star rating plus a required comment of
    at most 2,000 characters. A database unique constraint enforces one
    review per user per product.
  - A new `reviews` app. `orders` owns the delivered-purchase query, and the
    review manager owns `can_review` and `editable_by`. Both foreign keys
    cascade.
  - Staff moderate inline on the product page with the same controls. They
    can edit only the comment, never the rating. Staff edits show "Edited by
    staff," author edits show "Edited," and an author's later save clears the
    staff flag.
  - Create, update, and delete re-render the whole reviews section. Edit and
    Cancel swap a single card. Delete uses `hx-confirm`. A review the user
    may not touch returns a 404.
  - A summary (average and count) on the product page only. The list is
    newest first with the viewer's own review pinned, and has no
    pagination. Reviewers show as "First L.", falling back to "Verified
    customer."
  - The seed gives `customer` a MindSync review and leaves SyncRest and
    Dreamweaver unreviewed. Background reviews come only from Delivered
    orders, and one is staff-edited.
- **Deviations:** None. The user took the recommended option on all 19
  questions and asked no follow-up questions. The agent settled several
  details from the codebase without asking (the unique constraint, create
  taking a product pk, staff following the purchase rule, error handling
  and races, and test conventions) and listed them for the user to check.
- **Sideways:** Nothing went wrong. Two things were added during PRD
  writing rather than in the interview, and the agent pointed them out
  afterward: separate edit and cancel GET endpoints are named for the
  card swap, and a note says the Django admin doesn't enforce the
  comment-only rule for staff.

## 2026-10-18 — Wishlist: Phase 4, seeded demo wishlist

### Prompts
1. /implement @prd/wishlist.md @plans/wishlist.md implement phase 4
2. (Asked whether to run /tdd) Do you think tdd is needed for this? I'm
   leaning no.
3. Looks good.
4. (Asked about PROMPTS.md and committing) Yes, append; yes, commit.
5. (Asked for a commit title) Complete wishlist Phase 4

### Summary
- **Outcome:** Phase 4 is built and the full suite is green (385 passed);
  `ruff check` and `ruff format --check` are clean.
  - The seed's `_wipe()` now clears wishlists right after carts.
  - A new `CUSTOMER_WISHLIST` constant and `_create_customer_wishlist()`
    step give `customer` four saved products with staggered `added_at`
    dates: MindSync Duo, EchoPatch (unavailable), Seraphine (also in the
    seeded cart), and Pulse Halo, newest first.
  - New `test_seed_gives_customer_a_wishlist` checks the contents and
    order, the unavailable item, the cart overlap, and that only one
    wishlist is seeded. `test_seed_is_idempotent` now also compares
    wishlist and wishlist-item counts across two runs.
- **Deviations:** Instead of answering yes or no to /tdd, the user asked
  whether it was needed. The agent agreed it wasn't, since the phase is seed
  data with no behavior to drive out, and implemented directly with tests
  alongside.
- **Sideways:** Nothing. The user checked the phase in the browser and
  approved it on the first pass.

## 2026-10-18 — Wishlist: Phase 3, tidy and buy from the Wishlist page

### Prompts
1. /implement @prd/wishlist.md @plans/wishlist.md implement phase 3
2. (Asked whether to run /tdd) Yes, run /tdd.
3. yes, approve all three
4. yes, approve the test
5. yes, move on to behavior 2
6. yes, keep it and move on to behavior 3
7. yes, approve the test
8. yes, move on to the rest of phase 3
9. Continue
10. (Asked about PROMPTS.md and committing) Yes, append; yes, commit.
11. (Asked for a commit title) Add tdd skill, implement skill, and wishlist
    phases 1-3

### Summary
- **Outcome:** Phase 3 is built and the full suite is green (384 passed);
  `ruff check` and `ruff format --check` are clean.
  - `RemoveFromListView` subclasses the existing `WishlistRemoveView` and
    only overrides `respond`, rendering
    `wishlist/partials/_wishlist_contents.html`. It is routed as
    `wishlist:remove_from_list` at `wishlist/items/<int:pk>/remove/`.
  - Each wishlist row now has an Unavailable badge when it applies, the
    existing `orders/partials/_add_button.html` (quantities from the cart
    context processor, disabled for unavailable products), and an HTMX
    Remove button targeting `#wishlist-contents`.
  - TDD covered three behaviors: the remove response shows the remaining
    rows, removing the last item shows the empty state, and rows offer
    add-to-cart while marking unavailable products. Ordinary tests added:
    sign-in and POST-only on the new endpoint, the A/B privacy case for
    both remove URLs, the Remove button on each row, an item staying on
    the wishlist after add-to-cart, and a product that becomes unavailable
    staying on the list.
- **Deviations:** none — every recommendation was approved as offered.
  The commit title was the user's own and covers more than Phase 3: it
  also commits the new `implement` and `tdd` skills and the uncommitted
  wishlist Phases 1–2 work.
- **Sideways:**
  - Behavior 1's first run failed with `NoReverseMatch`, not an
    assertion; a route and a stub `respond` returning an empty response
    were added to reach a real RED.
  - Behavior 2 never went RED. Phase 2's contents partial already had the
    empty state, so it passed as soon as behavior 1 rendered the real
    partial. It was a poor TDD pick (its interface was already settled);
    the user chose to keep it as a regression test.

## 2026-10-11 — Account Security Center: Phase 6, forgot password set a new password

### Prompts
1. @prd/account-security-center.md @plans/account-security-center.md Do
   Phase 6.
2. Okay, how can I test these new features in the webpage?
3. Append a session log to PROMPTS.md at the repo root, under today's date,
   newest entry at the top. Record every prompt I gave you this session, in
   order, including any corrections. End the entry with a short summary:
   the outcome, any places where I deviated from a recommended answer or
   asked follow-up questions, and anything that went sideways.

### Summary
- **Outcome:** Phase 6 is built, which completes the Account Security
  Center plan.
  - `StyledSetPasswordForm` in `accounts/forms.py` is Django's stock
    `SetPasswordForm` with DaisyUI classes added. It asks for the new
    password twice, never the old one, and runs the project's password
    validators.
  - `ResetPasswordView` (`accounts:password_reset_confirm`) now uses that
    form. On success it:
    - calls `User.notify_password_changed()`,
    - adds a "Password reset — you can now sign in with your new
      password." success message,
    - redirects to `accounts:password_reset_complete`.

    `post_reset_login` stays off, so the user is not signed in.
  - The new `ResetPasswordCompleteView` subclasses
    `PasswordResetCompleteView` and serves `accounts:password_reset_complete`
    at `/accounts/password-reset/complete/`. Its `get` redirects to the
    login page. The success message is added by the confirm view, so
    opening this URL directly shows no message.
  - `templates/accounts/password_reset_confirm.html` replaces the Phase 5
    placeholder.
    - A valid link shows the form, naming the username, with errors beside
      each field.
    - Any other link shows "Link invalid or expired" and a "Request a new
      link" button.
  - 11 new tests are in `accounts/tests.py`. They cover:
    - the stock form being used, with no old-password field
    - the password being set, landing on the login page with the message,
      and the new password signing in
    - the user not being signed in after a reset
    - the notice, checked in the outbox
    - a weak password being rejected, with no change and no mail
    - opening the complete URL directly redirecting with no message
    - links rejected after one hour, after use, after a password change,
      after an email change, and when made up
  - The one-hour test fakes the clock by monkeypatching the private
    `PasswordResetTokenGenerator._now`, which avoids adding a time-freezing
    dependency.
  - The full suite passed (338 tests). `ruff check` and
    `ruff format --check` were clean. Nothing was committed.
- **Deviations:**
  - No recommendations were overridden and no clarifying questions were
    asked.
  - Phase 6 needed one design choice the plan didn't settle: where the
    success message comes from. The agent decided it without asking. The
    confirm view adds the message and the complete view only redirects, so
    the bare complete URL can't show a false "Password reset" message.
  - The user asked one follow-up question: how to test the feature in the
    browser. The agent gave steps for:
    - a full reset: request, copy the link from the dev-server terminal,
      set a password, land signed out on the login page with the message,
      see the notice email, and sign in with the new password
    - weak and mismatched passwords
    - links rejected after use, after a password change, after an email
      change, and when made up
    - opening the complete URL directly
  - It noted:
    - Testing earlier phases may have changed the `customer` account's
      details, and `seed` wipes the database.
    - Expiry can be checked by hand by setting `PASSWORD_RESET_TIMEOUT` to
      60 for a while.
- **Sideways:**
  - Nothing failed.
  - `uv` warned that the active `VIRTUAL_ENV` (the parent folder's
    `.venv`) doesn't match the project's `.venv` and was ignored. The
    warning was harmless.
  - The plan's acceptance-criteria checkboxes were left unticked, as in
    earlier phases.

## 2026-10-11 — Account Security Center: Phase 5, forgot password request and email

### Prompts
1. @prd/account-security-center.md @plans/account-security-center.md Do
   Phase 5.
2. Okay, how can I test these new features in the webpage?
3. Append a session log to PROMPTS.md at the repo root, under today's date,
   newest entry at the top. Record every prompt I gave you this session, in
   order, including any corrections. End the entry with a short summary:
   the outcome, any places where I deviated from a recommended answer or
   asked follow-up questions, and anything that went sideways.

### Summary
- **Outcome:** Phase 5 is built.
  - `PASSWORD_RESET_TIMEOUT = 3600` is set in `config/settings.py`.
    `DEFAULT_FROM_EMAIL` was already set in Phase 3.
  - `StyledPasswordResetForm` in `accounts/forms.py` is Django's stock
    `PasswordResetForm` with DaisyUI classes added. Django's form already
    ignores case when looking up the email, skips accounts with unusable
    passwords, and doesn't say whether an email matched.
  - Three views in `accounts/views.py` subclass Django's reset views:
    - `ForgotPasswordView` serves `accounts:password_reset` at
      `/accounts/password-reset/`.
    - `ForgotPasswordDoneView` serves `accounts:password_reset_done` at
      `/accounts/password-reset/sent/`.
    - `ResetPasswordView` serves `accounts:password_reset_confirm` at
      `/accounts/password-reset/<uidb64>/<token>/`.
  - The confirm page is a placeholder. Django checks the link, but the
    page says setting a new password "isn't available yet". The plan
    leaves that page to Phase 6, so the route exists only so the email's
    link can be built.
  - New templates:
    - the request page
    - the "Check your email" page, which shows the same message whether
      or not the email matched
    - the placeholder confirm page
    - the reset email's subject and body templates in
      `templates/accounts/email/`. The body includes "Your username is:
      …", the link, and a note that it expires after one hour.
  - The login page has a "Forgot password?" link above the Sign in button.
  - 9 new tests are in `accounts/tests.py`. They cover:
    - the login page link
    - the request page using the stock form
    - the timeout setting
    - the email's subject, sender and username, checked in the outbox
    - the emailed link opening the confirm page as a valid link
    - the lookup ignoring capitalization
    - an unknown email getting the same redirect and no mail
    - an account with an unusable password getting no mail
    - the confirmation page not saying whether the email matched
  - The full suite passed (327 tests), and `ruff check` was clean.
    Nothing was committed.
- **Deviations:**
  - No recommendations were overridden and no clarifying questions were
    asked.
  - The user asked one follow-up question: how to test the feature in the
    browser. The agent gave steps:
    - the login page link
    - a known email, with the email checked in the dev-server terminal
    - the same email in different capitalization
    - an unknown email
    - a background customer with an unusable password (`mwren`)
    - opening the emailed link, which reaches the placeholder page
  - It noted:
    - Phase 3 and 4 testing may have changed the `customer` account's
      email or password.
    - `seed` wipes the database.
    - Django redirects the link to a token-free `set-password` URL.
  - At the end of Phase 5, the agent offered to commit and to write this
    log. The user asked for the log only.
- **Sideways:**
  - `ruff format --check` flagged `accounts/urls.py` after the first
    test run. The agent ran `ruff format` on that file, and the rest of
    the project was already formatted.
  - Every `uv run` printed the same warning as earlier sessions: the
    active `VIRTUAL_ENV` (the parent folder's `.venv`) doesn't match the
    project's `.venv`. uv ignored it and used the project's own
    environment.
  - `bash.exe.stackdump` showed up as modified in `git status`. It's a
    leftover from the shell, not part of this change, and it was also in
    the Phase 4 commit.
  - The agent didn't test the feature in a browser. Only the test suite
    checked it.

## 2026-10-11 — Account Security Center: Phase 4, change password with a notice

### Prompts
1. @prd/account-security-center.md @plans/account-security-center.md Do
   Phase 4.
2. Okay, how can I test these new features in the webpage?
3. Append a session log to PROMPTS.md at the repo root, under today's date,
   newest entry at the top. Record every prompt I gave you this session, in
   order, including any corrections. End the entry with a short summary:
   the outcome, any places where I deviated from a recommended answer or
   asked follow-up questions, and anything that went sideways.

### Summary
- **Outcome:** Phase 4 is built.
  - `User.notify_password_changed()` in `accounts/models.py` emails the
    account's own address. `set_password` is not overridden, so signup,
    `createsuperuser`, the seed and the tests send no notice. The
    email-sending code from `change_email()` moved into a shared
    `_send_notice()` helper, so both notices use the same path. The notice's
    subject and body templates are in `templates/accounts/email/`.
  - `StyledPasswordChangeForm` in `accounts/forms.py` is Django's stock
    `PasswordChangeForm` with DaisyUI classes added in its constructor. The
    old-password check and the password validators are all Django's.
  - `ChangePasswordView` in `accounts/views.py` subclasses
    `PasswordChangeView` and serves `accounts:password_change` at
    `/accounts/security/password/`. It keeps Django's session handling:
    the current session stays signed in and other sessions are signed out.
    On success it sends the notice and returns to the hub with "Password
    updated." It adds `LoginRequiredMixin` for consistency, although
    Django's view already requires sign-in.
  - `templates/accounts/change_password.html` is new. It shows the
    password rules under the field, the same way the signup page does. The
    hub's "Change password" button, a disabled placeholder until now, is a
    link.
  - 10 new tests are in `accounts/tests.py`. They cover sign-in being
    required, the hub link, a successful change, this session staying
    signed in while a second client is signed out, an outbox check for the
    notice, rejections for a wrong old password, mismatched passwords and a
    weak password, and no mail from signup or `create_user`. The seed test
    in `products/tests.py` now also checks that seeding sends no mail.
  - The full suite passed (318 tests), and `ruff check` and `ruff format`
    were clean. Nothing was committed.
- **Deviations:**
  - No recommendations were overridden and no clarifying questions were
    asked.
  - The user asked one follow-up question: how to test the feature in the
    browser. The agent gave steps using the seeded `customer` account,
    checking the notice in the dev-server terminal, a private window to
    show other sessions being signed out, the three rejection cases, the
    sign-in redirect, and the other two roles. It warned that `seed` wipes
    the database and that changed passwords persist until they're changed
    back or the database is reseeded.
  - At the end of Phase 4, the agent offered to commit and to write this
    log. The user asked for the log only.
- **Sideways:**
  - Nothing failed. Every `uv run` printed the same warning as earlier
    sessions: the active `VIRTUAL_ENV` (the parent folder's `.venv`)
    doesn't match the project's `.venv`. uv ignored it and used the
    project's own environment.
  - The agent didn't test the feature in a browser. Only the test suite
    checked it.

## 2026-10-11 — Account Security Center: Phase 3, change email with a notice to the old address

### Prompts
1. @prd/account-security-center.md @plans/account-security-center.md Do
   Phase 3.
2. Okay, how can I test these new features in the webpage?
3. Append a session log to PROMPTS.md at the repo root, under today's date,
   newest entry at the top. Record every prompt I gave you this session, in
   order, including any corrections. End the entry with a short summary:
   the outcome, any places where I deviated from a recommended answer or
   asked follow-up questions, and anything that went sideways.

### Summary
- **Outcome:** Phase 3 is built.
  - `User.change_email(new_email)` in `accounts/models.py` saves the new
    address and emails a notice to the old one only. The notice shows the
    new address masked (`c***@example.com`) through a new `mask_email()`
    helper, and tells the owner to contact support if the change wasn't
    theirs. Its subject and body templates are in
    `templates/accounts/email/`.
  - `ChangeEmailForm` in `accounts/forms.py` takes a new email and the
    current password. It lowercases the email and rejects a wrong
    password, an email another account uses (in any capitalization), and
    the user's own current email. It's a plain `Form` that takes the user,
    not a `ModelForm`. A `ModelForm` would set the user's email during
    validation, before `change_email()` could read the old address.
  - `ChangeEmailView` (`LoginRequiredMixin` + `FormView`) serves
    `accounts:change_email` at `/accounts/security/email/`. It's backed by
    `templates/accounts/change_email.html`, and on success it returns to
    the hub with "Email updated."
  - The hub's "Change email" button is now a link. "Change password" stays
    a disabled placeholder until Phase 4.
  - `DEFAULT_FROM_EMAIL` is now
    `ThoughtTronix <no-reply@thoughttronix.example>`.
  - 10 new tests are in `accounts/tests.py`. They cover sign-in being
    required, a successful change saved lowercased, each rejection, the
    typed email kept after an error, and an outbox check: one notice, to
    the old address, from the store sender, with only the masked new
    address in it.
  - The full suite passed (308 tests), and `ruff check` and `ruff format`
    were clean. Nothing was committed.
- **Deviations:**
  - No recommendations were overridden and no clarifying questions were
    asked.
  - The user asked one follow-up question: how to test the feature in the
    browser. The agent gave steps using the seeded `customer` account,
    checking the notice in the dev-server terminal, the three rejection
    cases, and the sign-in redirect. It warned that `seed` wipes the
    database.
  - At the end of Phase 3, the agent offered to commit and to write this
    log. The user asked for the log only.
- **Sideways:**
  - Nothing failed. Every `uv run` printed a warning that the active
    `VIRTUAL_ENV` (the parent folder's `.venv`) doesn't match the project's
    `.venv`. uv ignored it and used the project's own environment.
  - The agent didn't test the feature in a browser. Only the test suite
    checked it.

## 2026-10-11 — Account Security Center: Phase 2, Security Center hub and navbar link

### Prompts
1. @prd/account-security-center.md @plans/account-security-center.md Do
   Phase 2.
2. Okay, how can I test these new features in the webpage?
3. Append a session log to PROMPTS.md at the repo root, under today's date,
   newest entry at the top. Record every prompt I gave you this session, in
   order, including any corrections. End the entry with a short summary:
   the outcome, any places where I deviated from a recommended answer or
   asked follow-up questions, and anything that went sideways.

### Summary
- **Outcome:** Phase 2 is built.
  - `SecurityView` (`LoginRequiredMixin` + `TemplateView`) serves
    `accounts:security` at `/accounts/security/`, with no role checks.
  - `templates/accounts/security.html` is a DaisyUI card showing the
    username and email, with "Change email" and "Change password" buttons.
  - `templates/base.html` has a "Security" link right after "Addresses",
    for signed-in users only.
  - 6 new tests are in `accounts/tests.py`:
    - the navbar link shows for signed-in users and is hidden from visitors
    - anonymous visitors are redirected to the login page
    - the hub shows the username, email and both buttons, run as a
      customer, an employee and the admin (pytest-django's `admin_user`)
  - The full suite passed (299 tests), and `ruff check` and
    `ruff format --check` were clean. Nothing was committed.
- **Deviations:**
  - The plan leaves the buttons' destinations to later phases without
    saying how they should look until then. The agent made them disabled
    `<button>`s with a template comment, so nothing links to a URL that
    doesn't exist yet. It flagged this choice, and the user didn't respond
    to it. Phases 3 and 4 should turn them into links.
  - The user asked a follow-up question about testing the hub by hand. The
    agent gave the seed's demo credentials (`customer`/`customer123`,
    `employee`/`employee123`, `admin`/`admin123`) and a checklist: the
    navbar link, the hub's contents, the same page for every role, the
    login redirect with `?next=`, and the link hidden from visitors. It also
    noted that `seed` is destructive.
- **Sideways:**
  - Nothing failed. The manual checks were not run during the session, and
    nobody has looked at the navbar's layout at narrow widths in a browser.
    The tests only check the HTML.

## 2026-10-11 — Account Security Center: Phase 1, every account has a unique email

### Prompts
1. @prd/account-security-center.md @plans/account-security-center.md Do
   Phase 1.
2. Okay, how can I test these new features in the webpage?
3. During manual test 4, when I entered the admin@example.com email, the
   terminal freezes.
4. What would you recommend?
5. Add the note and leave createsuperuser as it is. I'm not sure if
   altering it will cause problems later, so I think it is best to leave
   it.
6. Okay, verify Phase 1 again to ensure it has been completed.
7. Append a session log to PROMPTS.md at the repo root, under today's date,
   newest entry at the top. Record every prompt I gave you this session, in
   order, including any corrections. End the entry with a short summary:
   the outcome, any places where I deviated from a recommended answer or
   asked follow-up questions, and anything that went sideways.

### Summary
- **Outcome:** Phase 1 is complete, and all eight acceptance criteria were
  checked one by one.
  - `User.email` is required and unique. It has an
    `"That email is already in use."` message and a database check
    constraint against blanks. `User.save()` lowercases the email, and
    `REQUIRED_FIELDS = ["email"]`. The migration is
    `accounts/migrations/0003_user_email_required_unique.py`.
  - A `UniqueEmailMixin` in `accounts/forms.py` lowercases the email and
    checks it against other accounts. It is used by the signup form, which
    now asks for email, and by new admin add-user and edit-user forms. The
    admin's "Add user" page includes email.
  - Emails were added to the conftest user fixtures and to the two inline
    users in `orders/tests.py`. 13 new tests are in `accounts/tests.py`.
  - The final run had 293 tests passing, ruff clean,
    `makemigrations --check` clean and `manage.py check` clean.
  - Nothing was committed. The local `db.sqlite3` grading snapshot was
    migrated (see Sideways).
- **Deviations:**
  - The agent applied the case-insensitive duplicate check to the admin's
    edit-user form as well, which the plan doesn't ask for. Without it, a
    different-case duplicate would crash the page with an `IntegrityError`.
  - The user asked follow-up questions about testing the features by hand,
    about the frozen terminal, and for a recommendation.
  - The user followed the agent's recommendation: leave `createsuperuser`
    as it is and record the gap in the PRD, rather than override the command
    and move `accounts` above `django.contrib.auth` in `INSTALLED_APPS`. The
    note is in the PRD's Further Notes.
- **Sideways:**
  - On the first full run, the new admin add-user test failed (200 instead
    of a 302). The post was missing the address inline's management-form
    fields. The test was fixed, and the code didn't need to change.
  - The manual testing steps were wrong about `createsuperuser`. They said
    it would reject `admin@example.com` as already in use. Django's command
    only runs `field.clean()` on the email, so it catches a blank but not a
    duplicate. The duplicate goes on to the password prompt and then fails
    with an `IntegrityError`, and no account is created. The user's
    "frozen" terminal was most likely that password prompt: `getpass` never
    echoes, and in Git Bash (mintty) it receives no keystrokes at all. The
    agent suggested PowerShell or `winpty` instead. This was caught by the
    user in manual testing and confirmed in Django's source.
  - The agent did not migrate the tracked `db.sqlite3`, but a later
    `showmigrations` showed 0003 already applied, most likely from the
    user's run of the manual testing steps. While this entry was being
    written, `git status` showed `db.sqlite3` modified and all 30 tracked
    product images under `media/products/` deleted. Running `seed`
    rebuilds the images under new file names, so the committed grading
    snapshot no longer matches the working tree. They can be restored with
    `git checkout db.sqlite3 media/`, which would also undo the migration.

## 2026-10-11 — Account Security Center: PRD to phased plan

### Prompts
1. /prd-to-plan @prd/account-security-center.md
2. I think it is fine. Keep 5 and 6 separate. I think 2 and 3 should be kept
   separate.
3. Append a session log to PROMPTS.md at the repo root, under today's date,
   newest entry at the top. Record every prompt I gave you this session, in
   order, including any corrections. End the entry with a short summary:
   the outcome, any places where I deviated from a recommended answer or
   asked follow-up questions, and anything that went sideways.

### Summary
- **Outcome:** `plans/account-security-center.md` was written using the
  prd-to-plan skill's template. It has a header of shared decisions:
  - Everything lives in the `accounts` app, with no service module and no
    signals.
  - There are seven named URLs under `accounts:`.
  - Email is required, unique and lowercased in `User.save()`.
  - The Security Center pages require sign-in, with no role checks.
  - Mail goes to the console only, and reset links last one hour.

  The six phases each cut through every layer:
  1. Every account has a unique email.
  2. The Security Center page and its navbar link.
  3. Change email, with a notice to the old address.
  4. Change password, with a notice.
  5. Forgot password: request and email.
  6. Forgot password: set a new password.

  Each phase has acceptance criteria and lists the PRD stories it covers.
  Together the phases cover stories 1–26. No code was written.
- **Deviations:** None. The first proposed breakdown was approved without
  changes. Claude raised two open questions. On whether to merge phases 5
  and 6, Claude made no recommendation, and the user chose to keep them
  separate. On whether to fold phase 2 into phase 3, Claude recommended
  keeping them separate, and the user agreed.
- **Sideways:** Nothing significant. Phase 5 has to define the
  `accounts:password_reset_confirm` route early so the reset email's link
  can be built. The plan records this, and the confirm page itself is
  finished in phase 6. The new plan uses the skill's template, so its format
  differs from `plans/core-platform.md`. The IDE connection failed to
  connect at session start, which had no effect on the work.

## 2026-10-11 — Account Security Center: design interview and PRD

### Prompts
1. /grill-me We need to create an Account Security Center feature that
   expands the current account security features. Customers must be able to
   do the following: provide an Email address during creating an account,
   change their password, and reset a forgotten password via email.
2. Option A.
3. Option A.
4. I agree. For this projects scope, Option A.
5. Option A.
6. Option C. It is a security hub, so I think changing email should also be
   a feature there.
7. Option A. I think changing password should also require the previous
   password; unless going through forgot password.
8. Option A. Yes to the password-change notice.
9. I like Option B.
10. Go with Option A.
11. Option A.
12. Option A. I don't think this project will ever require real emails to be
    sent.
13. Option A makes the most sense.
14. Option A sounds simpler.
15. Option A.
16. Option A.
17. Option A.
18. I agree. Option A.
19. /to-prd
20. Append a session log to PROMPTS.md at the repo root, under today's date,
    newest entry at the top. Record every prompt I gave you this session, in
    order, including any corrections. End the entry with a short summary:
    the outcome, any places where I deviated from a recommended answer or
    asked follow-up questions, and anything that went sideways.

### Summary
- **Outcome:** A 17-question design interview settled the Account Security
  Center:
  - Email is required on the `User` model, so it applies everywhere
    (signup, admin "Add user", `createsuperuser`). It is unique, enforced by
    the database, and lowercased in `User.save()`.
  - No email verification; login stays username-only, and the reset email
    includes the username.
  - A hub page at `/accounts/security/` (sign-in required, staff included,
    no role checks) shows the username and email and links to separate
    change-email and change-password pages.
  - Changing email requires the current password and notifies the old
    address. Changing or resetting the password requires the old password
    (change only) and notifies the account's email. The notices are sent by
    explicit `User` methods, not signals and not a `set_password` override.
  - Forgot password uses Django's four built-in reset views. Links expire
    after one hour, the page shows the same message whether or not the email
    exists, and a successful reset goes to the login page without signing
    the user in.
  - Email stays on the console backend, with a `DEFAULT_FROM_EMAIL` added.
    No rate limiting.

  The PRD was written to `prd/account-security-center.md` with 26 user
  stories. It notes that it supersedes core-platform user story 6 ("no
  email"). No code was changed and nothing was committed.
- **Deviations:**
  - Q5: the user chose C (the hub also lets you change your email) over the
    recommended A, reasoning that a security hub should include it. This
    added Q6 (password required to change email) and Q7 (notifying the old
    address).
  - Q11: the user chose A (console email only) over the recommended B
    (configurable through `.env`), saying the project will never need real
    email.
  - Q6: the user also asked that changing the password require the old
    password, except through forgot password. Django's stock forms already
    work that way, so it was recorded as a requirement, not a new question.
  - Q7: the user accepted the agent's suggestion of a password-change
    notice as well.
  - The agent decided some things without asking and told the user each
    time: reset also sends the password-change notice, a
    `DEFAULT_FROM_EMAIL` is set, and the URL names and template locations
    follow existing conventions. The PRD also adds a rule rejecting an
    unchanged email on the change-email page, which was never discussed.
- **Sideways:**
  - Q13 exists because the agent found a conflict between earlier answers:
    with emails unique (Q2) but optional on the model, a second account
    created through the admin or `createsuperuser` without an email would
    crash on the duplicate `""`. The user chose to make email required on
    the model.
  - In Q14 the agent said lowercasing in `User.clean()` plus the user
    manager would cover "every path." Reading the seed command showed that
    was wrong: `seed` builds users with `User(...).save()`, which skips both.
    The agent corrected it before Q17 and moved lowercasing to
    `User.save()`; the decision itself (store lowercase) didn't change.
  - The seed command's background customers have unusable passwords, so
    Django's reset form skips them. This was recorded in the PRD as
    expected behavior, not fixed.
  - The PRD has not been reviewed by the user yet.

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
