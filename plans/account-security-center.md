# Plan: Account Security Center

> Source PRD: `prd/account-security-center.md` (extends the core platform; supersedes core-platform user story 6, "no email")

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning app**: `accounts`. The feature touches only `User`, so it gets no service module and no signals. Logic lives on the model, and the views that trigger a notice call it in their own code.
- **URLs** (all in the `accounts` namespace, sign-in required unless noted):
  - `accounts:security`: the Security Center hub
  - `accounts:change_email`: the change-email form
  - `accounts:password_change`: the change-password form (subclasses `PasswordChangeView`)
  - `accounts:password_reset`, `accounts:password_reset_done`, `accounts:password_reset_confirm`, `accounts:password_reset_complete`: public, subclassing Django's four reset views and pointed at `accounts` templates and namespaced URLs (the same way the sign-in view subclasses `LoginView`)
- **Models**: no new models. `User.email` becomes required and unique (a database constraint, applied by a migration with no data migration needed). It is lowercased in `User.save()` so a plain unique constraint gives case-insensitive uniqueness, and it is added to `REQUIRED_FIELDS`. `User.change_email(new_email)` saves the new address and notifies the old one. A separate `User` method sends the password-changed notice. `set_password` is **not** overridden.
- **Authorization**: signed in only, with no role checks. Customers, employees and the admin all share the same Security Center.
- **Forms**: Django's stock `PasswordChangeForm`, `SetPasswordForm` and `PasswordResetForm` where the PRD names them, plus the extended signup form, a new change-email form and an extended admin user-creation form. All of them carry DaisyUI input classes set in their constructors.
- **Email**: console backend only, hardcoded. Each email has a subject template and a body template. `DEFAULT_FROM_EMAIL` is a store address. `PASSWORD_RESET_TIMEOUT` is 3600.
- **Templates**: extend the base template, use DaisyUI semantic classes only, and use no HTMX. They are plain GET/POST pages like the address book.
- **Tests**: pytest + pytest-django with plain fixtures in the project-level conftest. Sent mail is checked through Django's in-memory outbox.

---

## Phase 1: Every account has a unique email

**User stories**: 1, 2, 3, 25, 26

### What to build

Make email part of every account. The user model requires a unique, lowercased email. Signup asks for one and explains when it is already taken. The admin's "Add user" form requires one, and `createsuperuser` prompts for one and refuses a blank. Existing test fixtures and the seed command are brought in line with the new constraint.

### Acceptance criteria

- [ ] A migration makes `User.email` non-blank and unique, enforced by a database constraint
- [ ] `User.save()` lowercases the email on every creation path
- [ ] `email` is in `REQUIRED_FIELDS`, and `createsuperuser` will not accept a blank email
- [ ] Signup requires an email. A duplicate, including one with different capitalization, shows a field error instead of an integrity error
- [ ] The admin's "Add user" form includes and requires email
- [ ] Conftest user fixtures supply emails, and the full suite passes
- [ ] The seed command still runs cleanly, twice in a row, against the new constraint
- [ ] Tests cover: email required at signup, uniqueness across capitalization, and lowercasing on save

---

## Phase 2: Security Center hub and navbar link

**User stories**: 14, 15

### What to build

A signed-in page at `accounts:security` shows the account's username and current email, with "Change email" and "Change password" buttons. A "Security" link sits beside "Addresses" in the navbar for signed-in users. The buttons' destinations arrive in later phases.

### Acceptance criteria

- [ ] `accounts:security` shows the signed-in user's username and email
- [ ] Anonymous visitors are redirected to sign in
- [ ] The navbar shows a "Security" link beside "Addresses" for signed-in users only
- [ ] The hub works the same for a customer, an employee and the admin
- [ ] Tests cover: sign-in required, and username and email rendered

---

## Phase 3: Change email, with a notice to the old address

**User stories**: 16, 17, 18, 19, 23, 24

### What to build

From the hub, an account holder opens `accounts:change_email` and enters a new email and their current password. On success, `User.change_email()` saves the new address and emails a notice to the old one. The notice names the new address in masked form (for example `c***@example.com`) and advises contacting support if the change wasn't the owner's. The user returns to the hub with a success message. This is the first phase that sends mail, so it also sets `DEFAULT_FROM_EMAIL`.

### Acceptance criteria

- [ ] The form requires the current password and rejects a wrong one
- [ ] The new email is lowercased and must not belong to another account
- [ ] An unchanged email is rejected
- [ ] Errors appear beside their fields, and the user's input is kept
- [ ] On success, the email is updated and the user lands on the hub with a success message
- [ ] A notice with the masked new address goes to the *old* address, and nothing goes to the new one
- [ ] `DEFAULT_FROM_EMAIL` is set to the store address
- [ ] Tests cover: sign-in required, wrong password rejected, duplicate rejected, and an outbox check for the old-address notice

---

## Phase 4: Change password, with a notice

**User stories**: 20, 21, 22 (change), 23, 24

### What to build

From the hub, an account holder opens `accounts:password_change` and enters their old password and a new one twice. Django's default session handling applies: this session stays signed in and other sessions are invalidated. On success, the view calls the `User` password-changed notifier, which emails the account's address, and the user returns to the hub with a success message.

### Acceptance criteria

- [ ] The view subclasses `PasswordChangeView` and uses the stock `PasswordChangeForm` with the project's password validators
- [ ] A wrong old password, mismatched new passwords and weak passwords are each rejected with field errors
- [ ] After a change, the current session stays signed in and other sessions are signed out
- [ ] On success, the user lands on the hub with a success message
- [ ] A password-changed notice goes to the account's email
- [ ] `set_password` is not overridden, so signup, seeding and `createsuperuser` send no notice
- [ ] Tests cover: sign-in required, the change succeeds, a wrong old password is rejected, and an outbox check for the notice

---

## Phase 5: Forgot password, request and email

**User stories**: 4, 5, 6, 7

### What to build

The login page gets a "Forgot password?" link to `accounts:password_reset`. A visitor enters an email and lands on `accounts:password_reset_done`, which shows the same confirmation whether or not the email matched an account. A matching account with a usable password is emailed a reset link that also reminds the visitor of their username. `PASSWORD_RESET_TIMEOUT` is set to one hour. The `accounts:password_reset_confirm` route exists so the email's link can be built. The page behind it is completed in Phase 6.

### Acceptance criteria

- [ ] The login page links to "Forgot password?"
- [ ] The request uses the stock `PasswordResetForm`, so email lookup ignores case
- [ ] Known and unknown emails get the same response and the same redirect
- [ ] The reset email contains a working `accounts:password_reset_confirm` link and the account's username
- [ ] Accounts with unusable passwords, such as the seed's background customers, receive nothing
- [ ] `PASSWORD_RESET_TIMEOUT` is 3600
- [ ] Tests cover: an outbox check for the link and username, an unknown email getting the same response and no mail, and a lookup with different capitalization

---

## Phase 6: Forgot password, set a new password

**User stories**: 8, 9, 10, 11, 12, 13, 22 (reset)

### What to build

The emailed link opens `accounts:password_reset_confirm`, where the visitor sets a new password twice without giving their old one, using the project's password validators. On success, the view calls the password-changed notifier and does **not** sign the user in. `accounts:password_reset_complete` lands them on the login page with a success message. An invalid, expired, used or superseded link shows a clear message and a way to request a new one.

### Acceptance criteria

- [ ] The confirm page uses the stock `SetPasswordForm` and enforces the password validators
- [ ] A successful reset does not sign the user in, and `post_reset_login` stays off
- [ ] The visitor lands on the login page with a success message and can sign in with the new password
- [ ] A successful reset sends the password-changed notice to the account's email
- [ ] A link is rejected, with a clear "invalid or expired" message, after one hour, after it has been used, after a password change and after an email change
- [ ] Tests cover: a reset sets the password, the notice is in the outbox, there's no auto-login, and links are rejected after expiry, after use and after a password change
