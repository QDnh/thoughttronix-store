# PRD: The ThoughtTronix Store — Product Reviews

*Extends the core platform.*

---

## Problem Statement

A ThoughtTronix shopper deciding whether to buy a product has only the store's own description to go on. They can't see what other customers thought of it, so they can't tell whether a neural implant actually delivers on its tagline or whether a home assistant is worth the price.

Customers who *have* bought something have nowhere to say how it went. A good experience can't help sell the product to the next shopper, and a bad one can't warn them.

The store also has to trust its reviews. A review is only worth reading if it comes from someone who actually owned the product, if each customer gets one voice per product, and if nobody can quietly change what a customer said.

## Solution

**Product reviews**: customers who have received a product can leave one review of it, made up of a star rating and a written comment, and everyone can read the reviews on the product's page.

- **One review per customer per product.** A customer who has already reviewed a product sees their own review instead of a form.
- **Only verified buyers can review.** A customer can write a review only once the product is in one of their orders that staff have marked Delivered. Because every review comes from a verified buyer, the page says so once instead of badging each review.
- **A review is a 1–5 star rating and a written comment.** Both are required. The comment can be up to 2,000 characters.
- **Authors control their own reviews.** The customer who wrote a review can edit it (rating and comment) or delete it at any time, even if their order is later changed from Delivered.
- **Staff moderate in place.** Staff see Edit and Delete on every review on the product page. Staff can edit a review's comment, for example to remove profanity or personal details, but never its rating. A staff edit is labeled "Edited by staff" so readers know the text was moderated. An author's own edits are labeled "Edited."
- **Everything updates without a reload.** Creating, editing, and deleting a review all happen in place on the product page. The rating summary, the form, and the list stay in sync.
- **A rating summary** at the top of the reviews section shows the average rating and the number of reviews, or "No reviews yet."
- **Clear guidance when someone can't review.** Visitors are prompted to sign in. Signed-in customers who haven't received the product are told that only customers who've received it can review it.

## User Stories

**Shopper (anyone viewing a product page)**

1. As a shopper, I want to see the reviews for a product on its page, so that I can learn what other customers thought before buying.
2. As a shopper, I want to see a product's average star rating and its number of reviews at the top of the reviews section, so that I can judge it at a glance.
3. As a shopper, I want to see "No reviews yet" on a product nobody has reviewed, so that the section never looks broken.
4. As a shopper, I want to know that every review comes from a customer who received the product, so that I can trust what I'm reading.
5. As a shopper, I want the newest reviews first, so that I see the most current opinions.
6. As a shopper, I want each review to show the reviewer's first name and last initial, its star rating, its date, and its comment, so that each review reads as coming from a real person.
7. As a shopper, I want to see when a review has been edited, and whether staff edited it, so that I know whether the text is exactly what the customer first wrote.
8. As a shopper, I want to read reviews on products that are currently unavailable, so that I can still learn about them.

**Visitor (not signed in)**

9. As a visitor, I want a prompt to sign in where the review form would be, so that I know how to leave a review.
10. As a visitor, I want signing in from that prompt to bring me back to the same product, so that I don't have to find it again.

**Customer (signed in)**

11. As a customer who has received a product, I want a review form on its page, so that I can share my experience.
12. As a customer, I want to give a rating from 1 to 5 whole stars, so that I can sum up my opinion simply.
13. As a customer, I want the rating to start with no stars selected, so that I never submit a rating I didn't choose.
14. As a customer, I want to write a comment of up to 2,000 characters, so that I can explain my rating.
15. As a customer, I want a clear error when I forget the rating, leave the comment blank, or write too much, with my text kept, so that I can fix it without retyping.
16. As a customer, I want my review to appear as soon as I submit it, without a page reload, so that I don't lose my place.
17. As a customer, I want the rating summary to update when I post, edit, or delete my review, so that it always matches the reviews shown.
18. As a customer, I want to be able to leave only one review per product, so that each customer gets one voice per product.
19. As a customer, I want my own review pinned at the top of the list, so that I can find it and manage it easily.
20. As a customer, I want to edit my review's rating and comment in place, so that I can update my opinion.
21. As a customer, I want to cancel an edit and get my review back unchanged, so that I can back out safely.
22. As a customer, I want to delete my review, with a confirmation first, so that a stray click doesn't erase it.
23. As a customer, I want to write a new review after deleting my old one, as long as I've still received the product, so that deleting isn't permanent if I change my mind.
24. As a customer whose order hasn't been delivered yet, I want a message explaining that only customers who've received the product can review it, so that I understand why there's no form.
25. As a customer who has never ordered a product, I want the same message, so that I know what it takes to review it.
26. As a customer, I want to keep editing or deleting my review even if my order's status later changes, so that my review stays under my control.
27. As a customer, I want to review products I received even if they're now unavailable, so that I can still share my experience.
28. As a customer, I want no one but me and staff to be able to change or delete my review, so that my words stay mine.
29. As a customer, I want staff to be unable to change my rating, so that my score always reflects my opinion.
30. As a customer, I want my login username kept off my reviews, so that posting a review doesn't expose half of my sign-in details.
31. As a customer, I want a double-click on submit to create only one review, so that I never post duplicates.

**Employee and admin**

32. As an employee or admin, I want Edit and Delete on every review on the product page, so that I can moderate reviews where customers see them.
33. As an employee or admin, I want to edit a review's comment to remove inappropriate content, so that I can clean up a review without deleting it.
34. As an employee or admin, I want my edits labeled "Edited by staff," so that moderation is transparent to readers.
35. As an employee or admin, I want to delete any review, with a confirmation first, so that I can remove abusive or fraudulent reviews without accidents.
36. As an employee or admin, I want my moderation to update the page without a reload, just as it does for customers.
37. As an employee or admin, I want to review products I've received like any customer, but not products I haven't, so that being staff grants moderation, not a free review.
38. As an admin, I want to view and manage reviews in the Django admin, so that I have a fallback for support questions.

**Reviewer of the demo**

39. As someone exploring the demo, I want the seeded customer account to already have a review, so that I can see the pinned review with its Edit and Delete controls right after signing in.
40. As someone exploring the demo, I want the seeded customer to have delivered products they haven't reviewed yet, so that I can try writing a review.
41. As someone exploring the demo, I want products in shipped and placed orders to show the "only customers who've received this product" message, so that I can see that rule working.
42. As someone exploring the demo, I want other customers' reviews on several products, with a mix of ratings and one staff-edited review, so that the summary and labels are on screen without any setup.

## Implementation Decisions

**A new `reviews` app.** Reviews get their own app with the URL namespace `reviews`. They don't belong in `products`: checking purchases there would make `products` import from `orders`, which already imports from `products`, creating a circular dependency. They don't belong in `orders` either, which is about buying. The new app depends on both, and neither depends back on it. This follows the wishlist precedent.

**Model: `Review`.**

- Fields: the author (a foreign key to the user), the product (a foreign key to `Product`), a rating, a comment, a created timestamp, an updated timestamp, and an "edited by staff" flag.
- The rating is a small positive integer limited to 1–5 by validators, like the discount code's percent-off field.
- The comment is a text field, limited to 2,000 characters by validation. It's required, and since form fields strip whitespace by default, a comment made only of spaces is rejected.
- A unique constraint on the author–product pair enforces one review per customer per product in the database itself, like the cart's and wishlist's unique pairs. The form also checks it, so customers see a friendly message, but the database is the final guarantee against double-submits.
- Deleting a user deletes their reviews, and deleting a product deletes its reviews (cascade on both). Every user foreign key in the codebase already cascades, and keeping the author required keeps the ownership rule free of null cases.
- The created timestamp uses a default rather than auto-now-add, so the seed can backdate reviews, matching the convention on orders.

**What "purchased" means.** A customer has purchased a product when it's on a line of one of their orders with status Delivered. Placed, Shipped, and Cancelled orders don't count. Eligibility is checked only when a review is *created*. If staff later change the order's status, an existing review is unaffected, and its author can still edit and delete it. Staff change order statuses freely in the back office (any status at any time), and reviews shouldn't appear and disappear with those changes. If a cancelled purchase shouldn't keep its review, staff can delete it.

**Logic lives in models and managers.**

- The `orders` app owns "delivered purchase": a queryset method answers whether a given user has a Delivered order containing a given product. It's reusable later, for example for a "you bought this" badge.
- The review manager owns "may review": `can_review(user, product)` combines "has a delivered purchase" with "hasn't reviewed it yet." Views and the product page call it once.
- The review manager owns "may modify": `editable_by(user)` returns every review for staff and only the user's own reviews for everyone else.
- The `Review` model owns the edit rules in one method that takes the editor and the new values. An author's edit may change the rating and the comment and clears the staff flag. A staff edit of someone else's review may change only the comment and sets the staff flag. Either kind of edit refreshes the updated timestamp.
- The review queryset owns the rating summary: one aggregate query for the average and the count.
- No service module. The architecture keeps exactly two deliberate deep modules, and a two-condition check doesn't justify a third.

**Edit labels.** A review shows "Edited" when its updated timestamp differs from its created timestamp, and "Edited by staff" instead when the staff flag is set. Because an author's save clears the flag, the label always describes the text currently shown. An author can undo a moderation edit this way, and staff can moderate it again or delete the review.

**Staff are author-or-staff, not a separate interface.** There is one set of endpoints and partials. The permission rule is "the author, or `is_staff`." Staff who write their own reviews follow the same purchase rule as everyone else. Being staff grants moderation, not eligibility.

**Forms.** One review form. It includes both the rating and the comment when the editor is the review's author or is creating a new review. It drops the rating field when a staff member is editing someone else's review, so staff can never submit a rating change. The rating input is DaisyUI's radio-button star rating with no default selected, so choosing a rating is required.

**Endpoints.** Every endpoint requires sign-in. Changes are POST-only, and the only GETs are for showing the edit form and cancelling it.

- `reviews:create` takes a product pk, the same as the wishlist's add endpoint. It looks the product up across the whole catalog, not just available products, so customers can review products that have since become unavailable. It re-checks `can_review` on submit, so hiding the form is never the only protection.
- `reviews:edit` (GET) takes a review pk and sends back that single review card in edit mode.
- `reviews:cancel` (GET) takes a review pk and sends back that single review card in display mode.
- `reviews:update` (POST) takes a review pk and saves the edit.
- `reviews:delete` (POST) takes a review pk and deletes the review.
- Edit, cancel, update, and delete look the review up through `editable_by(request.user)`. A review the user may not touch returns a 404, exactly like one that doesn't exist, so nobody can probe which review ids exist.
- Cross-site forged requests are rejected by Django's CSRF protection. The base template already sends the CSRF token with every HTMX request.

**HTMX behavior.**

- Create, update, and delete each send back the whole reviews section: summary, then the form or the explanation, then the list. Everything is rendered together from fresh data, so the page can never be partly updated. This is the same approach as the wishlist's remove-from-list response.
- Edit and Cancel swap only the one review card between display and edit mode. Saving from edit mode then re-renders the whole section.
- Invalid submissions (no rating, blank comment, over 2,000 characters) re-render with the form, inline errors, and the customer's input kept. They return status 200, like the store's other HTMX forms.
- If a create arrives when the customer is no longer eligible (a second submit after a double-click, or a stale form after they reviewed in another tab), the response is the section showing their existing review or the explanation. A unique-constraint collision never becomes a server error.
- Delete buttons use HTMX's built-in confirmation ("Delete this review?"), which stays within the HTMX-only frontend rule.

**Product page.**

- The reviews section sits below the product details and is a partial, so the page's first load and every HTMX response render it the same way.
- `ProductDetailView` adds what the section needs to the template context: the product's reviews, the summary, whether the viewer can review, and the viewer's own review if any. It asks the review manager for each.
- Top to bottom: the summary ("★ 4.3 out of 5 · 12 reviews," a note that all reviews come from verified buyers, or "No reviews yet"); then the review form if the viewer can review, a sign-in link with a `next` back to the product for visitors, or the "only customers who've received this product can review it" message for signed-in customers who haven't received it (customers who've already reviewed see neither, just their pinned review); then the list.
- The list is newest first, with the viewer's own review pinned at the top. There's no pagination or sorting.
- Each review card shows the reviewer's display name, the stars, the date (for example "Oct 18, 2026"), the "Edited" or "Edited by staff" label when it applies, the comment, and Edit and Delete buttons when the viewer is its author or staff.
- Styling is Tailwind and DaisyUI semantic classes only, per the frontend conventions.

**Reviewer display name.** `accounts.User` gets a small display method: first name plus last initial (for example "Casey M."), falling back to "Verified customer" when the names are blank. Login usernames never appear on reviews.

**Django admin.** `Review` is registered so the admin has a fallback for support. Superusers, and staff given review permissions, can view and edit reviews there.

**Seed.** The `seed` command clears reviews in its reset step and creates:

- for the `customer` demo account: a review of MindSync (Delivered), so its pinned review is on screen at first sign-in. SyncRest and Dreamweaver (also Delivered) stay unreviewed, so the form is ready to try. Seraphine Mini (Shipped) and Veil (Placed) show the "only customers who've received this product" message without any extra setup.
- for the background customers: reviews only on products from their own Delivered orders, so the seed obeys the feature's purchase rule. Ratings are mixed, and one review is marked "Edited by staff." The seed's existing fixed random seed keeps this deterministic.

**Tests.** Shared fixtures go in the project-level `conftest.py`, as plain fixtures that don't depend on the seed. The seed's tests invoke the seed directly. Coverage should include:

- the delivered-purchase check: Delivered counts, and Placed, Shipped, Cancelled, and another user's orders don't
- `can_review`: true only with a delivered purchase and no existing review, and true again after the review is deleted
- the one-review-per-product database constraint
- rating validation (1–5 required) and comment validation (required, whitespace-only rejected, 2,000-character limit)
- the edit rules: an author edits the rating and comment and clears the staff flag, and a staff edit changes only the comment, sets the flag, and can't change the rating even if a rating is submitted
- the "Edited" and "Edited by staff" labels
- `editable_by`: staff see all reviews, and a customer sees only their own
- each endpoint's sign-in requirement and POST-only rule
- create is rejected for ineligible customers, including after a status change away from Delivered before the first review
- an existing review stays editable and deletable by its author after the order leaves Delivered
- one customer can't edit or delete another customer's review (a 404, with the review unchanged)
- staff can edit the comment of and delete any review
- each viewer state on the product page: visitor, not received, eligible, already reviewed, and staff
- the summary's average and count, and the empty state
- each HTMX response: the re-rendered section after create, update, and delete, the single card after edit and cancel, and inline errors with input kept
- the reviewer display name and its fallback
- the seeded reviews, including that every seeded review is backed by a Delivered order

## Out of Scope

- **A back-office Reviews tab** listing every review for moderation at scale. Staff moderate on product pages for now.
- **Stars on catalog cards**, or ratings anywhere other than the product page.
- **Pagination and customer-selectable sorting** of reviews.
- **Dashboard analytics** for reviews, such as "top rated" or "most reviewed" panels.
- **Helpful votes**, staff or seller replies, and images in reviews.
- **Email notifications** about new reviews or moderation.
- **Hiding reviews automatically** when an order leaves Delivered.
- **Keeping reviews after their author's account is deleted.**

## Further Notes

- **Future work.** Each out-of-scope item can be added without changing the data model. A back-office Reviews tab would reuse `editable_by` and the edit rules. Catalog stars and dashboard panels would reuse the summary aggregation (a dashboard panel belongs in the dashboard's query module, one of the codebase's two deep modules, so it would need docstrings, type hints, and tests).
- **Moderation can be undone by the author.** Because an author's save clears the staff flag, an author could restore text that staff removed. That's accepted on purpose so the label always describes the current text. Staff can moderate again or delete the review.
- **Django admin access** bypasses the comment-only rule for staff edits, as it bypasses other app rules. It's a fallback for support, not the moderation interface.
- This design came out of a grill-me design interview. Each decision was chosen from alternatives for honesty of the "verified purchase" promise, consistency with the existing cart and wishlist patterns, safety against repeated or stale requests, and keeping the scope tight to the stated requirements.
