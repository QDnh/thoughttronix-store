# Plan: Customer Wishlist

> Source PRD: `prd/wishlist.md` (extends the core platform)

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning app**: a new `wishlist` app with the URL namespace `wishlist`, mounted at the site root like `orders`. It is not part of `orders` (buying) or `products` (the catalog and its back office). No service module: all the logic is on `Wishlist`.
- **URLs** (all require sign-in; all accept POST only, except `detail`). Every action endpoint takes a **product** pk, never a wishlist or wishlist-item id:
  - `wishlist:detail` → `wishlist/`: the Wishlist page
  - `wishlist:add` → `wishlist/add/<int:pk>/`: sends back the product-page button partial in its "saved" state
  - `wishlist:remove` → `wishlist/remove/<int:pk>/`: sends back the product-page button partial in its "not saved" state
  - `wishlist:remove_from_list` → `wishlist/items/<int:pk>/remove/`: sends back the Wishlist page's contents partial (the list, or the empty state)
  - Add and remove are separate endpoints, not a toggle, so repeated or stale requests are harmless. The two remove endpoints share a base view and differ only in the partial they send back, following the cart's line-action pattern.
- **Models** (mirroring `Cart` / `CartItem`):
  - `Wishlist`: one-to-one with the user (cascade on user delete), created lazily through a `for_user` class method. Owns `add` (no effect if already saved), `remove` (no effect if not saved), `contains`, and `lines` (items with products loaded for display).
  - `WishlistItem`: FK to `Wishlist` (related name `items`) and FK to `Product` (cascade on product delete), plus `added_at`. A unique constraint on the wishlist–product pair, ordered newest first.
- **Availability**: the add endpoint looks products up across the whole catalog, not through `available()`, so unavailable products can be saved. This deliberately differs from add-to-cart, and the view carries a comment saying why.
- **Authorization**: sign-in only, with no role checks. Customers, employees and the admin each get their own wishlist. The wishlist is always `Wishlist.for_user(request.user)`. Signed-out requests are redirected to login, and CSRF protection covers the HTMX POSTs through the token `base.html` already sends.
- **Frontend**: HTMX partials that swap themselves in place, the same approach as the add-to-cart button. `ProductDetailView` adds an `in_wishlist` flag to its context (no context processor). The navbar gains a "Wishlist" link for signed-in users, with no count badge.
- **Admin**: `Wishlist` is registered with an inline for its items, mirroring `CartAdmin`.
- **Tests**: pytest + pytest-django. Shared fixtures go in the project-level `conftest.py`, and the seed tests call the seed directly.

---

## Phase 1: Save and unsave from the product page

**User stories**: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 21, 22, 23

### What to build

The thinnest complete path through every layer. Create the `wishlist` app with the `Wishlist` and `WishlistItem` models, their migration, and the Django admin registration with an items inline. Every product page gets a wishlist button. Signed-in users see "Add to wishlist" or "In wishlist — remove", based on the `in_wishlist` flag. Clicking it POSTs to `wishlist:add` or `wishlist:remove`, and the button swaps itself without a page reload. Signed-out visitors see the button as a link to login with a `next` parameter back to the product. Unavailable products can be saved.

### Acceptance criteria

- [ ] The `wishlist` app is installed, and a migration creates `Wishlist` (one-to-one with the user) and `WishlistItem` (unique wishlist–product pair, `added_at`, newest first)
- [ ] Deleting a user deletes their wishlist, and deleting a product deletes its wishlist entries
- [ ] `Wishlist.for_user`, `add`, `remove`, `contains` and `lines` exist on the model. `add` and `remove` have no effect when repeated
- [ ] The product page shows the correct button state on first load for a signed-in user
- [ ] `wishlist:add` and `wishlist:remove` are POST-only, require sign-in, and send back the button partial in the "saved" and "not saved" states respectively
- [ ] The add view finds unavailable products (no `available()` filter) and has a comment explaining why. Remove works for any product
- [ ] Signed-out visitors see a login link whose `next` returns them to the product
- [ ] `Wishlist` appears in the Django admin with an inline listing its items
- [ ] Tests cover: one wishlist per user, the duplicate-item constraint, repeated add/remove having no effect, adding an unavailable product, button state on first load and after each action, the sign-in requirement and POST-only on both endpoints, and that customer A removing a product only on customer B's list leaves B's list unchanged

---

## Phase 2: The Wishlist page

**User stories**: 11, 12, 13, 14, 16 (empty state when the page loads)

### What to build

A "Wishlist" link in the signed-in navbar, alongside Orders and Addresses, leads to `wishlist:detail`. The page lists the user's saved products newest first. Each row shows the product image, name and price, and links to the product page. A user with no saved items sees a designed empty state on the page: a short message, a hint that products are saved from their product pages, and a "Browse the catalog" link. Nothing redirects. The list and empty state are built as one contents partial so the next phase can swap it.

### Acceptance criteria

- [ ] The signed-in navbar shows a "Wishlist" link with no count badge. Signed-out visitors don't see it
- [ ] `wishlist:detail` requires sign-in and shows only the signed-in user's items
- [ ] Rows show image, name and price, link to the product page, and are ordered newest first
- [ ] An empty wishlist shows the designed empty state with a "Browse the catalog" link, and doesn't redirect
- [ ] The list and empty state render from one contents partial
- [ ] Tests cover: the sign-in requirement, ordering, row content, the empty state, and that one user's items never appear on another user's page

---

## Phase 3: Tidy and buy from the Wishlist page

**User stories**: 15, 16, 17, 18, 19, 20, 21

### What to build

Each row on the Wishlist page gets an HTMX Remove button that POSTs to `wishlist:remove_from_list`. It shares the remove step with `wishlist:remove` through the base view, and sends back the contents partial. After the last removal, the page swaps to the empty state. Each row also carries the store's existing add-to-cart partial, which takes per-product cart quantities from the cart context processor. Adding to the cart leaves the item on the wishlist. Unavailable products, including ones that became unavailable after they were saved, stay on the list with an Unavailable badge and a disabled add-to-cart button.

### Acceptance criteria

- [ ] `wishlist:remove_from_list` is POST-only, requires sign-in, and sends back the contents partial
- [ ] Both remove endpoints share one base view for the remove step, and each always sends back its own kind of response
- [ ] Removing the last item sends back the empty state
- [ ] Each row includes the existing add-to-cart partial. Adding to the cart doesn't remove the wishlist item
- [ ] Unavailable products show an Unavailable badge, their add-to-cart button is disabled, and they stay on the list after becoming unavailable
- [ ] Tests cover: the list response and the empty-state response after the last removal, the sign-in requirement and POST-only, that customer A removing a product only on customer B's list leaves B's list unchanged, that the item stays after add-to-cart, and the Unavailable badge with its disabled button

---

## Phase 4: Seeded demo wishlist

**User stories**: 24, 25

### What to build

The `seed` command clears wishlists during its reset step, alongside carts, and gives the `customer` demo account a few wishlist items. At least one is an unavailable product, and at least one is also in the seeded cart. Someone exploring the demo can sign in as `customer` and see every wishlist case right away.

### Acceptance criteria

- [ ] The reset step clears wishlists alongside carts
- [ ] The `customer` account has a seeded wishlist with several items
- [ ] The seeded wishlist includes at least one unavailable product and at least one product that's also in the seeded cart
- [ ] The seed still runs cleanly twice in a row
- [ ] Tests (calling the seed directly) cover the seeded wishlist's contents and that running the seed twice doesn't duplicate it
