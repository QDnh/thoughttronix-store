# PRD: The ThoughtTronix Store — Account Security Center

*Extends the core platform. Supersedes core-platform user story 6 ("no email").*

---

## Problem Statement

A ThoughtTronix customer's account is held together by a username and a password, and nothing else. Signup deliberately asks for no email, so the store has no way to reach a customer about their own account.

That leaves customers stuck in three ways:

- **A forgotten password is a dead account.** There is no "Forgot password?" link and no address to send a reset link to. The customer's order history and saved addresses are stranded.
- **A password can't be changed.** A customer who suspects their password is known to someone else has no way to replace it.
- **There's no place to manage account security.** Signed-in customers can manage their addresses, but nothing else about their account. If someone else changed their details, they would never find out.

Employees and the admin are in the same position: their accounts are ordinary user accounts with the same gaps, and they are the more valuable target.

## Solution

An **Account Security Center**: a signed-in page where any account holder sees their username and email, and from which they can change their email or password. It comes with a **forgot-password flow** that emails a short-lived reset link.

- **Email becomes part of every account.** Signup asks for an email, which must be unique across the store. Every account, however created, has one.
- **The Security Center** is reached from a "Security" link in the navbar. It shows the account's username and email, with buttons to change each of email and password. Each change happens on its own page and returns to the hub with a success message.
- **Changes are protected and announced.** Changing email or password requires the current password. Each change sends a notice: to the *old* address when the email changes, and to the account's email when the password changes or is reset.
- **Forgot password** is linked from the login page. The customer enters their email and receives a link, valid for one hour, to set a new password. The emailed message also reminds them of their username. After resetting, they sign in with the new password.

Email is delivered to the development console only. No real mail leaves the application.

## User Stories

**Visitor (not signed in)**

1. As a visitor, I want to give my email address when I sign up, so that I can recover my account if I forget my password.
2. As a visitor, I want signup to tell me when my email is already in use, so that I understand why my account wasn't created and can sign in or reset instead.
3. As a visitor, I want my email to be treated the same regardless of capitalization, so that `Casey@Example.com` and `casey@example.com` are recognized as one address.
4. As a visitor, I want a "Forgot password?" link on the login page, so that I can start recovering my account from the place I discovered the problem.
5. As a visitor, I want to request a password reset by entering my email, so that a reset link is sent to an inbox I control.
6. As a visitor, I want the reset page to show the same confirmation whether or not my email matches an account, so that strangers can't use it to discover who shops at ThoughtTronix.
7. As a visitor, I want the reset email to include my username, so that I can recover my username as well as my password.
8. As a visitor, I want to set a new password from the emailed link without being asked for my old one, so that I can recover an account whose password I've forgotten.
9. As a visitor, I want my new password checked by the same password rules as signup, so that a reset can't leave me with a weak password.
10. As a visitor, I want to be sent to the login page with a success message after resetting, so that I know the reset worked and practice my new password right away.
11. As a visitor, I want a reset link to stop working after one hour, so that an old email sitting in my inbox can't be used to take over my account.
12. As a visitor, I want a reset link to stop working once it has been used, or once my password or email has changed, so that a leaked link is useless.
13. As a visitor, I want a clear message when a reset link is invalid or expired, so that I know to request a new one.

**Account holder (signed in — customer, employee, or admin)**

14. As an account holder, I want a "Security" link in the navbar, so that I can find my account's security settings from any page.
15. As an account holder, I want a Security Center page showing my username and current email, so that I can confirm the details my account recovery depends on.
16. As an account holder, I want to change my email from the Security Center, so that my account follows me when I change email providers.
17. As an account holder, I want changing my email to require my current password, so that someone using my unattended signed-in session can't redirect my account recovery to themselves.
18. As an account holder, I want the email change to be rejected if the new address belongs to another account, so that every email still maps to exactly one account.
19. As an account holder, I want a notice sent to my *old* address when my email changes, so that I find out immediately if someone else changed it.
20. As an account holder, I want to change my password from the Security Center by entering my old password and my new one twice, so that only I can change it and typos don't lock me out.
21. As an account holder, I want to stay signed in on this device after changing my password while my other sessions are signed out, so that a change made because of a suspected leak actually removes the intruder.
22. As an account holder, I want a notice sent to my email whenever my password is changed or reset, so that I find out if someone else did it.
23. As an account holder, I want to return to the Security Center with a success message after saving a change, so that I know the change took effect.
24. As an account holder, I want form errors shown beside their fields with my input preserved, so that I can fix a mistake without starting over.

**Admin**

25. As the admin, I want the Django admin's "Add user" form to require an email, so that accounts I create can use password reset like everyone else's.
26. As the admin, I want `createsuperuser` to insist on an email, so that no account, including mine, is left without a way to recover.

## Implementation Decisions

**User model (`accounts`)**

- `User.email` becomes required (no blanks) and unique, enforced by a database constraint. A migration applies the change; seeded emails are already unique, lowercase, and non-empty, so no data migration is needed.
- Emails are normalized to lowercase in `User.save()`, so every creation path is covered: signup, admin, `createsuperuser`, the seed command, and the change-email flow. A plain unique constraint is then sufficient for case-insensitive uniqueness.
- `email` is added to the user model's `REQUIRED_FIELDS`, so `createsuperuser` prompts for it and refuses a blank.
- A `User.change_email(new_email)` method saves the new address and emails a notice to the previous one.
- A `User` method that notifies the account's email of a password change. It is called explicitly by the change-password and reset-confirm flows. `set_password` is **not** overridden, because Django calls it during signup, `createsuperuser`, seeding, and tests, and those must not send notices.
- This follows the project convention that logic lives in models; the feature touches only `User`, so it gets no service module. Signals are not used, so the views that trigger a notice show it in their own code.

**Forms (`accounts`)**

- The signup form adds a required email field. Its "already in use" check compares the lowercased value and shows a field error, so customers see a friendly message rather than a database integrity error.
- A new change-email form takes a new email and the current password. It validates the password against the signed-in user, lowercases and checks uniqueness of the new email (excluding the user's own account), and rejects an unchanged email.
- Change password uses Django's stock `PasswordChangeForm` (old password + new password twice). Reset confirm uses Django's stock `SetPasswordForm` (new password twice, no old password). Both inherit the project's existing password validators.
- The reset request uses Django's stock `PasswordResetForm`. It looks emails up case-insensitively, always reports success, and skips accounts with unusable passwords.
- All forms get DaisyUI input classes in their constructors, the same as the existing account forms.
- The admin's user-creation form is extended to include and require email.

**Views and URLs (`accounts` namespace)**

- `accounts:security` is the hub page, sign-in required, showing username and email with "Change email" and "Change password" buttons.
- `accounts:change_email` is a form page, sign-in required. It calls `User.change_email()` on success and redirects to the hub with a success message.
- `accounts:password_change` subclasses Django's `PasswordChangeView`, sign-in required. On success it calls the password-change notifier and redirects to the hub with a success message. Django's default session handling is kept: the current session stays valid and other sessions are invalidated.
- `accounts:password_reset`, `accounts:password_reset_done`, `accounts:password_reset_confirm`, and `accounts:password_reset_complete` subclass Django's four built-in reset views, pointed at the `accounts` templates and namespaced URLs (the same way the existing sign-in view subclasses `LoginView`).
- The reset-confirm view calls the password-change notifier on success and does **not** sign the user in (`post_reset_login` stays off). The completion step lands the user on the login page with a success message.
- Access is "signed in" only, with no role checks: customers, employees, and the admin all use the same Security Center.

**Templates and navigation**

- All new pages extend the project base template and use DaisyUI semantic classes only, following the frontend conventions. No HTMX: these are plain GET/POST pages, the same pattern as the address book.
- The navbar gets a "Security" link beside "Addresses" for signed-in users.
- The login page gets a "Forgot password?" link.
- New email templates (subject and body) cover the reset message, which includes the username, plus the email-changed notice and the password-changed notice.
- The email-changed notice names the new address in masked form (for example `c***@example.com`) and advises contacting support if the change wasn't the owner's.

**Settings**

- `PASSWORD_RESET_TIMEOUT` is set to one hour (3600 seconds).
- `DEFAULT_FROM_EMAIL` is set to a store address (for example `ThoughtTronix <no-reply@thoughttronix.example>`) instead of Django's `webmaster@localhost`.
- The email backend stays hardcoded to the console backend.

**Testing**

- Tests use pytest + pytest-django with plain fixtures in the project-level conftest, per the testing conventions. Fixtures that create users must now supply an email.
- Sent mail is checked through Django's in-memory outbox (pytest-django swaps the backend automatically): the reset email's link and username, the old-address notice on email change, and the password-change notice on change and on reset.
- Coverage includes: email required and unique at signup (including different capitalization); lowercasing on save; a wrong current password rejecting the email change; reset links rejected after expiry, after use, and after a password change; an unknown email getting the same response as a known one; sign-in being required for the Security Center pages; and the seed command still running cleanly against the new constraints.

## Out of Scope

- **Email verification.** Addresses are trusted as typed, with no confirmation link and no "verified" state.
- **Login by email.** Sign-in stays username-only; the reset email covers username recovery.
- **Rate limiting** on reset requests, either per account or per IP. With console-only delivery there's no inbox to flood.
- **Real email delivery.** No SMTP configuration, no environment variables for mail, no third-party email provider.
- **A notice to the *new* address** on email change.
- **Asking existing accounts to add an email.** Every existing account comes from the seed command and already has one.
- **Two-factor authentication, session/device lists, login history, and account deletion.**
- **Auto-login after password reset** (and after signup, which remains as it is).

## Further Notes

- **Known enumeration gap.** The reset page doesn't reveal whether an email is registered, but signup does ("that email is already in use"), because emails are unique. This is a deliberate trade-off. Closing it would require email verification, which is out of scope.
- **Background customers can't reset.** The seed command's background customers have unusable passwords, and Django's reset form skips those accounts, so "Forgot password?" sends them nothing. This is expected: they exist to populate the dashboard and are never signed in to.
- **Email change invalidates pending reset links.** Django's reset token includes the user's email, so changing email (like changing password) voids any outstanding reset link.
- **Testing the flow by hand.** With the console backend, the reset link appears in the terminal running the dev server and is copied into the browser from there.
