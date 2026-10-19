# Plan: Product Reviews

> Source PRD: `prd/product-reviews.md` (extends the core platform)

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning app**: a new `reviews` app with the URL namespace `reviews`, mounted at the site root like `wishlist`. It depends on `products` and `orders`, and neither depends back on it. This avoids the `products` ↔ `orders` circular import. No service module: logic lives on the `Review` model, its manager/queryset, and the `orders` queryset.
- **URLs** (all require sign-in; changes are POST-only, and the only GETs are edit and cancel):
  - `reviews:create` → `reviews/create/<int:pk>/`: takes a **product** pk, mirroring `wishlist:add`. It looks the product up across the whole catalog (no `available()` filter) and re-checks `can_review` on submit
  - `reviews:edit` (GET) → `reviews/<int:pk>/edit/`: takes a **review** pk and sends back that one card in edit mode
  - `reviews:cancel` (GET) → `reviews/<int:pk>/cancel/`: sends back that one card in display mode
  - `reviews:update` (POST) → `reviews/<int:pk>/update/`: saves the edit and sends back the whole section
  - `reviews:delete` (POST) → `reviews/<int:pk>/delete/`: deletes the review and sends back the whole section
  - Edit, cancel, update and delete look the review up through `Review.objects.editable_by(request.user)`. A review the user may not touch returns 404, the same as one that doesn't exist.
- **Models**:
  - `Review`: an author FK to the user and a product FK to `Product` (cascade on both), `rating` (small positive integer, 1–5 by validators, like `percent_off`), `comment` (required text, at most 2,000 characters by validation), `created_at` (`default=timezone.now`, not auto-now-add, so the seed can backdate), an updated timestamp, and an edited-by-staff flag. A unique constraint on the author–product pair.
  - `Order` gains its first custom queryset, which owns "delivered purchase": does a given user have a Delivered order containing a given product? There's no schema change.
  - `accounts.User` gains a display-name method: first name plus last initial ("Casey M."), falling back to "Verified customer". Usernames never appear on reviews.
- **Logic ownership** (names pinned by the PRD):
  - Review manager: `can_review(user, product)` (delivered purchase and no existing review) and `editable_by(user)` (everything for staff, only the user's own reviews for everyone else)
  - Review queryset: the rating summary, as one aggregate query for average and count
  - `Review` model: one edit method that takes the editor and the new values. An author's edit changes the rating and comment and clears the staff flag. A staff edit of someone else's review changes only the comment and sets the flag. Both refresh the updated timestamp.
  - Labels: "Edited" when updated ≠ created, and "Edited by staff" instead when the flag is set
- **Authorization**: the rule is "the author, or `is_staff`." There's one set of endpoints and partials, with no separate staff interface. Staff follow the same purchase rule to write a review. Eligibility is checked only at create time, so a later order-status change never affects an existing review. CSRF covers the HTMX POSTs through the token `base.html` already sends.
- **Frontend**: the reviews section (summary, then form/prompt/message, then list) is one partial, rendered the same way on first load and in every create, update and delete response. Edit and cancel swap one card only. Invalid submissions return 200 with inline errors and the input kept. Delete uses `hx-confirm="Delete this review?"`. `ProductDetailView` adds the reviews, summary, `can_review` and the viewer's own review to its context. Styling uses Tailwind and DaisyUI semantic classes only. The rating input is DaisyUI's radio star rating with nothing selected by default.
- **Forms**: one review form. It includes the rating and comment for authors and new reviews, and drops the rating field when staff edit someone else's review.
- **Admin**: `Review` is registered in the Django admin as a support fallback.
- **Tests**: pytest + pytest-django. Shared fixtures go in the project-level `conftest.py` as plain fixtures that don't depend on the seed. The seed tests call the seed directly.

---

## Phase 1: Read-only reviews section on the product page

**User stories**: 1, 2, 3, 4, 5, 6, 7, 8, 30, 38

### What to build

The thinnest complete path through every layer. Create the `reviews` app with the `Review` model, its migration, and the Django admin registration. Add the display-name method to `User`. Every product page, including unavailable ones, gets a reviews section partial below the product details. It shows the rating summary ("★ 4.3 out of 5 · 12 reviews" plus a note that all reviews come from verified buyers, or "No reviews yet") and the list of review cards, newest first. Each card shows the reviewer's display name, the stars, the date ("Oct 18, 2026"), the "Edited" or "Edited by staff" label when it applies, and the comment. Reviews are created through the admin or fixtures for now.

### Acceptance criteria

- [ ] The `reviews` app is installed, and a migration creates `Review` with the author–product unique constraint
- [ ] Deleting a user deletes their reviews, and deleting a product deletes its reviews
- [ ] Rating validation rejects values outside 1–5, and comment validation rejects a blank comment and one over 2,000 characters
- [ ] The review queryset returns the summary's average and count in one aggregate query
- [ ] `User` returns "First L." as its display name, and "Verified customer" when the names are blank
- [ ] The product page renders the section partial with the summary, the verified-buyers note, and newest-first cards. A product with no reviews shows "No reviews yet"
- [ ] Unavailable products show their reviews
- [ ] Cards show "Edited" when updated ≠ created, and "Edited by staff" when the flag is set. No username appears anywhere on a card
- [ ] `Review` is registered in the Django admin
- [ ] Tests cover: the unique constraint, rating and comment validation, the cascades, the summary and its empty state, the display name and its fallback, newest-first ordering, both labels, and reviews on an unavailable product

---

## Phase 2: Write a review

**User stories**: 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 24, 25, 27, 31, 37

### What to build

Add the delivered-purchase queryset method on `Order` and `can_review` on the review manager. `ProductDetailView` asks the manager for each piece the section needs. The section now shows, between the summary and the list:

- the review form for viewers who can review
- a sign-in link with `next` back to the product for visitors
- the "only customers who've received this product can review it" message for signed-in viewers without a Delivered purchase
- nothing for viewers who have already reviewed, whose own review is pinned at the top of the list

Submitting the form POSTs to `reviews:create` and swaps in the whole section, freshly rendered: the updated summary, no form, and the new review pinned. Invalid submissions re-render the form with inline errors and the input kept. A create from an ineligible viewer (a double-click, a stale tab, or an order no longer Delivered) sends back the section in its current state and never raises a server error from the unique constraint.

### Acceptance criteria

- [ ] The delivered-purchase check counts only Delivered orders belonging to that user. Placed, Shipped, Cancelled and other users' orders don't count
- [ ] `can_review` is true only with a delivered purchase and no existing review
- [ ] Each viewer state renders correctly on first load: visitor (a sign-in link whose `next` returns to the product), not received, eligible (the form), and already reviewed (no form, own review pinned)
- [ ] Staff without a delivered purchase see the not-received message, and staff with one see the form
- [ ] The rating radios start with none selected. A missing rating, blank or whitespace-only comment, or a comment over 2,000 characters returns 200 with inline errors and the input kept
- [ ] `reviews:create` requires sign-in, is POST-only, finds unavailable products, and re-checks `can_review` on submit
- [ ] A successful create sends back the whole section with the updated summary and the new review pinned at the top
- [ ] A second create for the same product (a double submit) leaves exactly one review and sends back the section, not a 500
- [ ] Tests cover: the delivered-purchase check, `can_review`, each viewer state, the sign-in requirement and POST-only, validation errors with input kept, create on an unavailable product, rejection for ineligible customers (including after the order leaves Delivered before the first review), the double-submit case, and the re-rendered section after create

---

## Phase 3: Authors edit and delete their own review

**User stories**: 17, 20, 21, 22, 23, 26, 28

### What to build

Add `editable_by` on the review manager and the author branch of the edit method on `Review`. The author's card gets Edit and Delete buttons:

- Edit GETs `reviews:edit` and swaps that one card into an edit form pre-filled with the rating and comment.
- Cancel GETs `reviews:cancel` and swaps the card back unchanged.
- Saving POSTs to `reviews:update` and sends back the whole section, with the "Edited" label and an updated summary. Invalid edits re-render with inline errors and the input kept.
- Delete POSTs to `reviews:delete` after an HTMX confirmation and sends back the whole section. If the author still has a delivered purchase, the form reappears.

A review stays editable and deletable by its author after the order leaves Delivered. Other customers get a 404 on every one of these endpoints.

### Acceptance criteria

- [ ] `editable_by` returns only the user's own reviews for non-staff users
- [ ] An author's edit changes the rating and comment, clears the staff flag, and refreshes the updated timestamp
- [ ] Edit and Cancel send back the single card in edit and display mode respectively. Cancel shows the review unchanged
- [ ] Update and Delete send back the whole section with a fresh summary. The Delete button uses `hx-confirm="Delete this review?"`
- [ ] Invalid updates return 200 with inline errors and the input kept
- [ ] After deleting, an author with a delivered purchase sees the form again and can post a new review
- [ ] An author can still edit and delete after their order's status changes away from Delivered
- [ ] Another customer gets a 404 from edit, cancel, update and delete, and the review is unchanged
- [ ] Tests cover: `editable_by` for customers, the author edit rule, each endpoint's sign-in requirement and method rule (GET for edit and cancel, POST for update and delete), the single-card and whole-section responses, inline errors with input kept, re-reviewing after a delete, editing and deleting after a status change, and the 404 for another customer

---

## Phase 4: Staff moderation in place

**User stories**: 7, 29, 32, 33, 34, 35, 36

### What to build

`editable_by` returns every review for staff, so staff see Edit and Delete on every card and use the same endpoints and partials. When staff edit someone else's review, the edit form has no rating field. The staff branch of the edit method changes only the comment and sets the edited-by-staff flag, so the card reads "Edited by staff," and the rating can't change even if one is posted. Staff can delete any review after the same confirmation. All of it updates the page in place, like the customer flow. A staff member editing their own review follows the author rules.

### Acceptance criteria

- [ ] `editable_by` returns all reviews for staff
- [ ] Staff see Edit and Delete on every review card, and customers see them only on their own
- [ ] Staff editing another user's review get a form without a rating field
- [ ] A staff edit changes only the comment, sets the staff flag, and refreshes the updated timestamp. A posted rating is ignored
- [ ] The card shows "Edited by staff" after a staff edit. A later author edit clears the flag, and the card shows "Edited"
- [ ] Staff can delete any review, and the section re-renders with a fresh summary
- [ ] Staff editing their own review may change the rating, and the flag stays clear
- [ ] Tests cover: `editable_by` for staff, the staff edit rule (including a submitted rating being ignored), the form without a rating, the label after a staff edit and after a later author edit, staff delete of another customer's review, and the staff viewer state on the product page

---

## Phase 5: Seeded demo reviews

**User stories**: 39, 40, 41, 42

### What to build

The `seed` command clears reviews in its reset step. The `customer` demo account gets a review of MindSync (Delivered), so the pinned review with Edit and Delete is on screen right after signing in. SyncRest and Dreamweaver (also Delivered) stay unreviewed, so the form is ready to try. Seraphine Mini (Shipped) and Veil (Placed) show the "only customers who've received this product" message. Background customers review only products from their own Delivered orders, with mixed ratings across several products and one review marked "Edited by staff." The seed's existing fixed random seed keeps all of this deterministic.

### Acceptance criteria

- [ ] The reset step clears reviews
- [ ] `customer` has a MindSync review, no reviews of SyncRest or Dreamweaver, and `can_review` is true for both of those
- [ ] `customer` sees the not-received message on Seraphine Mini and Veil
- [ ] Every seeded review is backed by a Delivered order of its author containing that product
- [ ] Several products have reviews from background customers with a mix of ratings, and exactly one seeded review is marked edited by staff
- [ ] The seed runs cleanly twice in a row with the same results
- [ ] Tests (calling the seed directly) cover: the customer's reviewed and unreviewed products, the Delivered backing of every seeded review, the staff-edited review, the rating mix, and running twice without duplicates
