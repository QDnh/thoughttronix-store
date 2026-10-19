# PRD: The ThoughtTronix Store — Customer Wishlist

*Extends the core platform.*

---

## Problem Statement

A ThoughtTronix customer who finds a product they like but aren't ready to buy has nowhere to keep it. Their only options are:

- **Put it in the cart.** But the cart is for buying. Using it as a "maybe later" list clutters checkout, and the customer has to work around those items every time they actually want to buy something.
- **Remember it.** The catalog is large enough that customers lose track of products they meant to come back to, and they have to search for them again.
- **Give up on unavailable products.** If a product is marked unavailable, it can't go in the cart at all, so there's no way to note "I want this when it's back."

## Solution

A **wishlist**: one personal list per signed-in customer, for products they want to save for later.

- **Save from the product page.** Every product page has a wishlist button. Clicking it adds the product to the customer's wishlist, or removes it if it's already there, and the page doesn't reload. The button always shows the current state: "Add to wishlist" when the product isn't saved, "In wishlist — remove" when it is.
- **Any product can be saved**, including ones marked unavailable. Saving something isn't buying it.
- **A Wishlist page**, reached from a "Wishlist" link in the navbar, lists everything the customer has saved, newest first. Each entry shows the product's image, name, and price and links to its product page. Each entry has a Remove button that takes it off the list without a page reload, and the store's usual add-to-cart button so the customer can buy straight from the list. Unavailable products are marked as such, and their add-to-cart button is disabled.
- **Adding to the cart doesn't remove an item from the wishlist.** The two lists are independent.
- **An empty wishlist** gets a designed empty state: the customer stays on the Wishlist page and sees a short message, a hint that products are saved from their product pages, and a "Browse the catalog" link they can choose to follow. Nothing redirects automatically.

Visitors who aren't signed in see the wishlist button on product pages as a prompt to sign in. After signing in, they come back to the product they were viewing.

## User Stories

**Visitor (not signed in)**

1. As a visitor, I want to see a wishlist option on a product page, so that I know the store offers one.
2. As a visitor, I want clicking that option to take me to sign in and then bring me back to the same product, so that I can save it without hunting for it again.

**Customer (signed in)**

3. As a customer, I want exactly one wishlist tied to my account, so that everything I've saved is always in one place.
4. As a customer, I want to add a product to my wishlist from its product page, so that I can save it while I'm looking at it.
5. As a customer, I want adding to my wishlist to happen without the page reloading, so that I don't lose my place.
6. As a customer, I want the wishlist button to change right away to show the product is saved, so that I know my click worked.
7. As a customer, I want to remove a product from my wishlist using the same button on its product page, so that I can change my mind where I made the decision.
8. As a customer, I want the button to show the correct state whenever I open a product page, so that I can tell at a glance whether I've already saved it.
9. As a customer, I want saving a product twice to have no extra effect, so that a double-click never creates duplicate entries.
10. As a customer, I want to save products that are currently unavailable, so that I can keep track of things I want once they're back.
11. As a customer, I want a "Wishlist" link in the navbar, so that I can reach my wishlist from any page.
12. As a customer, I want my wishlist page to show each product's image, name, and price, so that I can review what I've saved without opening each one.
13. As a customer, I want each wishlist entry to link to its product page, so that I can read the full details.
14. As a customer, I want my most recently saved products at the top, so that what I just added is easy to find.
15. As a customer, I want to remove an item directly from my wishlist page without a reload, so that I can tidy my list quickly.
16. As a customer, I want to see a friendly empty state when I remove my last item, so that the page never looks broken.
17. As a customer, I want to add a wishlist item to my cart from the wishlist page, so that I can buy it without going back to the product page.
18. As a customer, I want an item to stay on my wishlist after I add it to my cart, so that removing it from the cart later doesn't make me lose track of it.
19. As a customer, I want unavailable items on my wishlist clearly marked, with their add-to-cart button disabled, so that I understand why I can't buy them yet.
20. As a customer, I want products that become unavailable after I saved them to stay on my wishlist, so that my list doesn't quietly lose things.
21. As a customer, I want no one else to be able to see or change my wishlist, so that what I've saved stays private.

**Employee and admin**

22. As an employee or admin, I want my own wishlist like any customer, so that saving products works the same for every account.
23. As an admin, I want to inspect a customer's wishlist in the Django admin, so that I can help with support questions.

**Reviewer of the demo**

24. As someone exploring the demo, I want the seeded customer account to already have a wishlist, so that I can see the feature working right after signing in.
25. As someone exploring the demo, I want the seeded wishlist to include an unavailable product and a product that's also in the seeded cart, so that I can see those cases without setting them up.

## Implementation Decisions

**A new `wishlist` app.** The wishlist gets its own app with the URL namespace `wishlist`. It doesn't belong in `orders` (which is about buying) or `products` (which is the catalog and its back office).

**Models: mirror the cart.**

- `Wishlist` has a one-to-one relationship with the user, so the database itself enforces one wishlist per account. Like `Cart`, it's created the first time it's needed through a `for_user` class method rather than at signup.
- `WishlistItem` links a wishlist to a product and records `added_at`. A unique constraint on the wishlist–product pair blocks duplicates at the database level. Items are ordered newest first.
- Deleting a user deletes their wishlist. Deleting a product deletes its wishlist entries.
- Following the "logic lives in models" convention, `Wishlist` owns its behavior: add (has no effect if the product is already saved), remove (has no effect if it isn't), contains, and a lines method that loads products for display.

**Unavailable products can be wishlisted.** The add endpoint looks products up across the whole catalog, not through `available()`. This deliberately differs from add-to-cart, which returns a 404 for unavailable products to protect checkout, and the view should carry a comment explaining why. Remove works for any product on the customer's own list.

**Endpoints.** Every endpoint requires sign-in and accepts only POST, except the list page.

- `wishlist:detail` is the wishlist page.
- `wishlist:add` takes a product pk and sends back the product-page button partial in its "saved" state.
- `wishlist:remove` takes a product pk and sends back the product-page button partial in its "not saved" state.
- `wishlist:remove_from_list` takes a product pk and sends back the wishlist page's contents partial (the list, or the empty state after the last removal).
- Add and remove are separate endpoints rather than a single toggle. That makes repeat or stale requests harmless (adding twice still means saved, removing twice still means not saved), and it matches how the cart's add and remove work.
- The two remove endpoints share a base view for the "remove this product from my wishlist" step and differ only in the partial they send back, following the cart's line-action pattern. Each URL always sends back the same kind of response.

**Ownership and privacy.**

- No endpoint takes a wishlist or wishlist-item id. Every endpoint identifies the *product*, and the wishlist is always the signed-in user's own (`for_user(request.user)`). So there's no request a user can make that points at someone else's wishlist.
- Signed-out requests are redirected to login by the sign-in requirement.
- Cross-site forged requests are rejected by Django's CSRF protection. The base template already sends the CSRF token with every HTMX request.

**Product page.**

- The button is an HTMX partial that swaps itself in place, the same approach as the add-to-cart button.
- On first load, `ProductDetailView` adds an `in_wishlist` flag to the template context by asking the `Wishlist` model. There's no context processor, because only this page needs the flag.
- For signed-out visitors, the button is a plain link to login with a `next` parameter back to the product, the same as add-to-cart.

**Wishlist page.**

- Each row shows the product image, name, price, a link to the product page, an Unavailable badge when it applies, the existing add-to-cart partial, and an HTMX Remove button.
- The add-to-cart partial gets its per-product cart quantities from the existing cart context processor and already handles unavailable products.
- The page has a designed empty state.

**Navigation.** A "Wishlist" link joins the signed-in navbar alongside Orders and Addresses, with no count badge.

**Roles.** Wishlists only require sign-in. Customers, employees, and the admin all get one, the same as the cart.

**Django admin.** `Wishlist` is registered with an inline for its items, mirroring `CartAdmin`.

**Seed.** The `seed` command gives the `customer` demo account a few wishlist items: at least one unavailable product, and at least one product that's also in the seeded cart. Wishlists are cleared during the reset step, alongside carts.

**Tests.** Shared fixtures go in the project-level `conftest.py`, and the seed's tests invoke the seed directly. Coverage should include:

- the one-wishlist-per-user rule, and that duplicate items are prevented
- that add and remove have no extra effect when repeated
- that unavailable products can be added
- the button state on first load and after each action
- both remove responses, including the empty state after the last removal
- the sign-in requirement on every endpoint
- that one customer cannot affect another customer's wishlist (customer A removing a product that's only on customer B's list leaves B's list unchanged)
- the seeded wishlist

## Out of Scope

- **Back-office wishlist analytics**, such as a "most wishlisted" dashboard panel. This is recorded as future work (see Further Notes).
- **Wishlist buttons on catalog cards.** The button lives on the product page only.
- **A navbar wishlist count badge.**
- **"Move to cart"**, meaning adding to the cart also removes the item from the wishlist. The two lists stay independent.
- **Multiple or named wishlists, and sharing a wishlist** with other people.
- **Notifications** when a wishlisted product comes back in stock or changes price.
- **Wishlists for signed-out visitors** (for example, held in the session).

## Further Notes

- **Future work, a "most wishlisted" dashboard panel.** Wishlist data could show staff which products customers want, especially "most wishlisted but unavailable" as a restocking signal. This would be a new aggregation in the dashboard's query module (one of the codebase's two deep modules, so it would need docstrings, type hints, and tests). The data model supports it as-is, so no migration would be needed.
- **Django admin access.** Superusers, and staff given wishlist permissions, can view and edit any wishlist through the Django admin. That's consistent with how carts work. If staff should only view wishlists, the admin can be made read-only later.
- This design came out of a grill-me design interview. Each decision above was chosen from alternatives on grounds of consistency with the existing cart patterns, safety against repeated or stale requests, and keeping the scope tight to the four stated requirements.
