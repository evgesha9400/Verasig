# Password Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A visitor who forgot their password gets a reset link by email, sets a new password, and logs in with it, on `https://verasig.io`. CI proves the whole journey with a local mail catcher. Nothing in the app pretends to reset a password any more.

**Diagnosis (facts from the repo and the live site, 2026-10-31):**

- The login page's "Forgot password?" is an anchor with no `href` and no handler (`LoginView.jsx:75`). The live bundle has the same text and nothing behind it.
- No public forgot or reset route exists. `POST /api/auth/password/forgot` and `/api/auth/forgot-password` answer 404 on the live site.
- The only reset route, `POST /user/password/reset-request` (`user_routes.py:114`), requires a logged-in user and only writes a log line. Settings says "Email delivery is not available yet" and shows a hard-coded "Last changed Feb 12, 2026".
- `mailer.py` sends nothing: both functions only log. No mail settings, no mail dependency, no mail secret on the mac-server.
- `verasig.io` DNS forbids sending: SPF `v=spf1 -all`, a null MX, and DMARC `p=reject; adkim=s; aspf=s`.
- The mac-server already runs another service (`winnow-post`) with a `resend_api_key` secret, so Resend is the platform precedent.

**Architecture:** One SMTP code path for every environment, with Python's standard library (`smtplib`, `email.message.EmailMessage`; no new dependency). Production relays through Resend's SMTP endpoint with a Resend API key as the password. CI and local dev send to a Mailpit container, and the Playwright spec reads the message back through Mailpit's HTTP API. The reset token is a signed JWT (purpose `password-reset`, 60 minutes) that also carries a fingerprint of the current password hash, so it is single-use without a new table. Both reset routes are public and never reveal whether an email is registered.

**Tech Stack:** FastAPI (`BackgroundTasks`), PyJWT, bcrypt, `smtplib`, Resend SMTP relay, Mailpit (`axllent/mailpit`), React Router, Playwright, mac-server `serverctl`, Cloudflare DNS.

**Parent spec:** `docs/superpowers/specs/2026-10-29-launch-architecture-design.md` (section 2 lists "The mailer only logs" as current state).

## Decisions

| Decision | Status | Reason |
|---|---|---|
| SMTP everywhere, Resend relay in production | RECOMMENDED | One code path; Mailpit tests the exact bytes production sends; no new Python dependency. The platform already holds a Resend key for another service. |
| Stateless JWT reset token with a password-hash fingerprint | RECOMMENDED | Same token helper family as `email-change`; single-use without a migration. |
| Reset link lands on `/reset-password?token=…`, success returns the user to `/login` | RECOMMENDED | No auto-login from an email link; the user proves the new password once. |
| Remove the fake authenticated reset route and the fake "Last changed" date | REQUIRED | Autophagy: one concept, one home. |
| Email-change confirmation stays log-only | DECIDED (out of scope) | It has no landing page in the web app; it gets its own plan. Do not start sending that email in this change. |

## Global Constraints

- Branch off `develop` (`feat/password-reset`); conventional commits; no attribution lines. Open the PR when the gate passes; merge with a `Merge: … (#N)` commit; release with a PR from `develop` to `main`.
- mac-server repo (`~/projects/97-support/mac-server`, `evgesha9400/mac-server`): PR only, rebase merge (the repo refuses squash); never edit `~/server-admin` on the host; secrets go in with `ssh mac-server '~/server-admin/scripts/serverctl secret set verasig production <name>' < file`. Never print a secret value, and `rm -P` any scratch file that held one.
- Stripe is untouched. Never use `stripe` CLI contexts for this project (see memory `stripe-sandbox-and-cli-caveat`).
- Tokens never appear in logs (`tests/accounts/test_mailer.py` pins this; extend it).
- Live-site specs are read-only: they may open `/forgot-password` but never submit it.
- Test artifacts and scratch output go in the session scratchpad, never the repo.
- Cloudflare DNS and Resend are external: use the `api-usage` skill for both. If no API access exists on this machine, write the exact records to the PR description and ask the user to add them; do not guess.

## Review Focus

1. `POST /auth/password/forgot` returns 202 with the same body and no measurable extra work whether or not the email exists. Pinned in Task 3.
2. A reset token stops working after one successful reset, after the password changes by any other path, and after 60 minutes. Pinned in Task 2 and Task 3.
3. The email body carries the link exactly once, built from `VERASIG_SITE_URL`, and the token never reaches a log line. Pinned in Task 1 and Task 3.
4. Mail failure does not leak: when SMTP is down the forgot route still returns 202, logs an error without the token, and the CI spec is the only place that asserts delivery. Pinned in Task 3.
5. DMARC alignment: the message is DKIM-signed by Resend for `verasig.io`, so `adkim=s` passes even though the SPF envelope domain is Resend's `send.` subdomain. Pinned in Task 8.

---

### Task 1: Mail transport settings and the SMTP mailer

**Files:**
- Modify: `apps/backend/src/verasig/config.py`
- Rewrite: `apps/backend/src/verasig/features/accounts/mailer.py`
- Modify: `apps/backend/src/verasig/entrypoints/api.py` (app state, like `exchange_verifier` at line 69)
- Modify: `apps/backend/.env.example`, `apps/backend/scripts/start-site.sh`
- Test: `apps/backend/tests/accounts/test_mailer.py`, `apps/backend/tests/foundation/test_config.py`

**Interfaces:**
- Settings: `smtp_host: str = ""`, `smtp_port: int = 1025`, `smtp_user: str = ""`, `smtp_password: str = ""`, `smtp_tls: str = "none"` (`none` | `starttls` | `ssl`), `mail_from: str = "Verasig <no-reply@verasig.io>"`. Add `mail_spec() -> MailConfig | None`: `None` when `smtp_host` is blank and env is local; raises `SettingsError` when blank outside local (same style as `stripe_secret_key_spec`).
- `mailer.py`: a `Mailer` protocol with `send(message: EmailMessage) -> None`; `SmtpMailer(config)` using `smtplib.SMTP_SSL` for `ssl`, `SMTP` + `starttls()` for `starttls`, plain `SMTP` for `none`; `LogMailer` that logs recipient and subject only. `build_password_reset_email(to: str, reset_url: str) -> EmailMessage` with a plain-text part and a minimal HTML part, subject `Reset your Verasig password`, a 60-minute expiry line, and an "ignore this if you did not ask" line.
- `app.state.mailer` is created once in `create_app` from `settings.mail_spec()`; tests replace it with a fake that records messages.
- `start-site.sh`: add `VERASIG_SMTP_PASSWORD` to the `*_FILE` loop.
- Delete `send_password_reset_requested`. Keep `send_email_confirm` log-only (Decisions table).

- [ ] **Step 1: Write the failing tests**: `mail_spec` returns `None` locally with a blank host, raises outside local; `build_password_reset_email` contains the URL exactly once in each part and the right subject; `SmtpMailer` picks `SMTP_SSL` for `ssl` (monkeypatch `smtplib`); `LogMailer` never logs the URL.
- [ ] **Step 2: Run** `cd apps/backend && uv run pytest tests/accounts/test_mailer.py tests/foundation/test_config.py -v`: expect FAIL.
- [ ] **Step 3: Implement** the settings, the mailer, the app-state wiring, the `.env.example` block (local default: `VERASIG_SMTP_HOST=localhost`, `VERASIG_SMTP_PORT=1025`, `VERASIG_SMTP_TLS=none`, `VERASIG_MAIL_FROM=Verasig <no-reply@verasig.io>`), and the start script line.
- [ ] **Step 4: Run** `make backend-test backend-lint backend-format-check`: expect PASS.
- [ ] **Step 5: Commit** `feat(backend): add smtp mailer and mail settings`

---

### Task 2: Reset token

**Files:**
- Modify: `apps/backend/src/verasig/features/accounts/tokens.py`
- Test: `apps/backend/tests/accounts/test_tokens.py` (create if missing; follow the existing tests' style)

**Interfaces:**
- `issue_password_reset_token(user_id: UUID, password_hash: str, secret: str, ttl: timedelta) -> str`: claims `sub`, `fp = sha256(password_hash.encode()).hexdigest()[:16]`, purpose `password-reset`.
- `read_password_reset_token(token: str, secret: str) -> tuple[UUID, str]` returns `(user_id, fp)`; raises `TokenInvalidError` on expiry, wrong purpose, or bad signature.
- `password_fingerprint(password_hash: str) -> str` shared by issue and the reset route.

- [ ] **Step 1: Write the failing tests**: round trip; wrong purpose (an access token) rejected; expired rejected; fingerprint changes when the hash changes.
- [ ] **Step 2: Run** the test file: expect FAIL.
- [ ] **Step 3: Implement** with the existing `_issue` and `_read` helpers.
- [ ] **Step 4: Run** `make backend-test backend-lint backend-format-check`: expect PASS.
- [ ] **Step 5: Commit** `feat(backend): add single-use password reset token`

---

### Task 3: Public forgot and reset routes

**Files:**
- Modify: `apps/backend/src/verasig/features/accounts/auth_routes.py`, `auth_schemas.py`, `workflow.py`, `repository.py`
- Modify: `apps/backend/src/verasig/features/accounts/user_routes.py` (delete `request_password_reset`)
- Test: `apps/backend/tests/api/test_auth.py` (or the file that holds login tests), `apps/backend/tests/api/test_user.py`

**Interfaces:**
- `POST /auth/password/forgot` body `{email}` → 202, empty body, always. When the normalized email matches an account: issue the token with `access_token_ttl`-style settings but a fixed `timedelta(minutes=60)`, build the URL `f"{settings.site_url_spec()}/reset-password?token={token}"`, and hand `mailer.send(message)` to `BackgroundTasks`. Wrap the send in try/except that logs `password reset email failed` with the recipient only.
- `POST /auth/password/reset` body `{token, password}` → 204. Read the token; load the user; compare `fp` with `password_fingerprint(user.password_hash)`; on any mismatch raise `ApiError(400, "AUTH_INVALID_TOKEN", "Invalid or expired link")`. Reuse `RegisterIn`'s password constraints for the new password. Persist through a new `repository.set_password_hash(session, user_id, password_hash)` and `workflow.reset_password(...)`.
- Delete `POST /user/password/reset-request` and its test `test_password_reset_request_is_accepted`; add a test that it now returns 404 (the file already has this pattern for the fake subscription routes).

- [ ] **Step 1: Write the failing tests** with the fake mailer from Task 1: known email → 202 and one message whose text contains `/reset-password?token=`; unknown email → 202 and no message; reset with the mailed token → 204 and login with the new password succeeds while the old fails; the same token a second time → 400; a token minted before an unrelated password change → 400; an expired token → 400; a mailer that raises → still 202; the old `/user/password/reset-request` → 404.
- [ ] **Step 2: Run** the test files: expect FAIL.
- [ ] **Step 3: Implement** the routes, schemas, workflow and repository functions. Email lookup uses the existing `normalize_email` and `find_by_email`.
- [ ] **Step 4: Run** `make backend-test backend-lint backend-format-check`: expect PASS.
- [ ] **Step 5: Commit** `feat(auth): add public password forgot and reset routes`

---

### Task 4: Web app pages and the login link

**Files:**
- Modify: `apps/frontend/web/src/app/paths.js` (add `forgotPassword: '/forgot-password'`, `resetPassword: '/reset-password'`)
- Modify: `apps/frontend/web/src/app/AppRouter.jsx` (two public routes, same `checkingSession` / `authenticated` guards as `/login`)
- Modify: `apps/frontend/web/src/shared/api/authApi.js` (`forgotPassword(email)`, `resetPassword(token, password)`), `userApi.js` (delete `requestPasswordReset`)
- Modify: `apps/frontend/web/src/features/auth/LoginView.jsx` (`onForgotPassword` prop; the link becomes a real action; show a success banner when routed back after a reset)
- Create: `apps/frontend/web/src/features/auth/ForgotPasswordView.jsx`, `ResetPasswordView.jsx` (reuse `BrandPanel`, `auth.css`, the `Input`/`Button`/`Banner`/`TextLink` design-system components as in `RegisterView.jsx`)
- Modify: `apps/frontend/web/src/features/settings/SettingsView.jsx` (the Password card calls `forgotPassword(user.email)`; copy says a link was emailed; delete the "Email delivery is not available yet" strings and the hard-coded "Last changed" date)
- Test: `LoginView.test.jsx`, `ForgotPasswordView.test.jsx`, `ResetPasswordView.test.jsx`, `authApi.test.js`, `userApi.test.js`, `SettingsView.test.jsx`

**Interfaces:**
- `ForgotPasswordView({ onSubmit, onLogin })`: one email field; after submit it always shows "If an account exists for that address, a reset link is on its way" and a link back to log in. Errors other than network failure are not shown (the API never returns them).
- `ResetPasswordView({ token, onSubmit, onLogin })`: new password and confirm fields; mismatch is a client-side error; a missing token or a 400 from the API shows "This link is invalid or has expired" with a link to request a new one; success calls `onDone()` which navigates to `/login?reset=1`, and `LoginView` shows a verified banner when that query is present.

- [ ] **Step 1: Write the failing tests** for each view (render, submit calls the prop with the typed values, error and success states) and for the two API functions (path and body).
- [ ] **Step 2: Run** `make frontend-test`: expect FAIL.
- [ ] **Step 3: Implement** the pages, routes, API functions, and the Settings change. Keep the auth pages' current look; no new CSS beyond what `auth.css` already offers.
- [ ] **Step 4: Run** `make check`: expect PASS.
- [ ] **Step 5: Commit** `feat(web): add forgot and reset password pages`

---

### Task 5: Mailpit for local dev and CI, and the E2E spec

**Files:**
- Modify: `docker-compose.yml` (service `mailpit` from `axllent/mailpit` pinned by digest, SMTP `1025`, HTTP `8025`, in the default services so `make dev` has it, and in the `site` profile; `site` gets `VERASIG_SMTP_HOST: mailpit`, `VERASIG_SMTP_PORT: "1025"`, `VERASIG_SMTP_TLS: none`, `depends_on: mailpit`)
- Modify: `.github/workflows/ci.yml` (`docker compose --profile site up -d --wait site`, which now pulls `mailpit`; env `E2E_MAIL_API_URL: http://localhost:8025`)
- Modify: `apps/frontend/web/e2e/.env.example` (document `E2E_MAIL_API_URL`), `CLAUDE.md` (one paragraph under the Playwright section, like the checkout note)
- Create: `apps/frontend/web/e2e/password-reset.spec.js`, `apps/frontend/web/e2e/mailpit.js` (fetch helpers over Mailpit's HTTP API: list messages for a recipient, read one, delete all)
- Modify: `apps/frontend/web/e2e/landing.spec.js` or a new `@smoke` test that only opens `/forgot-password` and asserts the form renders

**Spec (no `@smoke` tag, `test.use({ storageState: { cookies: [], origins: [] } })`, skips locally when `E2E_MAIL_API_URL` is unset and `CI` is unset):**
1. Register a throwaway user through `POST $E2E_API_URL/auth/register` (as `auth.setup.js` does).
2. Open `/login`, click "Forgot password?", land on `/forgot-password`, submit the email, see the confirmation text.
3. Poll Mailpit until a message to that address arrives; read the text body; extract the first `https?://…/reset-password?token=…` URL; replace its origin with `E2E_BASE_URL`.
4. Open it, set a new password, land on `/login` with the success banner.
5. Log in with the new password → `/app`. Open the same link again → the invalid-link state.
6. A second test: an unknown email still shows the same confirmation and Mailpit receives nothing.

- [ ] **Step 1: Write the spec and helpers.**
- [ ] **Step 2: Run locally** `docker compose --profile site up -d --wait site` then from `apps/frontend/web`: `CI=1 E2E_REGISTER=1 E2E_BASE_URL=http://localhost:8080 E2E_API_URL=http://localhost:8080/api E2E_MAIL_API_URL=http://localhost:8025 npm run e2e -- password-reset`: expect PASS. Tear down with `docker compose --profile site down`.
- [ ] **Step 3: Run the whole suite** the same way: expect PASS (checkout spec needs `VERASIG_STRIPE_WEBHOOK_SECRET` as `ci.yml` sets it).
- [ ] **Step 4: Lint** `ci.yml` with `docker run --rm -v "$PWD":/repo -w /repo rhysd/actionlint:latest`.
- [ ] **Step 5: Commit** `test(e2e): add password reset journey through mailpit`

---

### Task 6: Pull request to develop

- [ ] **Step 1: Run** `make check` once more from a clean tree; push `feat/password-reset`; open the PR to `develop` with a description that lists the new settings, the removed route, and the external steps (Tasks 7 and 8).
- [ ] **Step 2: Wait for CI** (check and e2e). Fix anything red on the branch.
- [ ] **Step 3: Merge** with `gh pr merge --merge --subject "Merge: password reset by email (#N)" --delete-branch`.

---

### Task 7: Resend and DNS (external, before the release)

**Owner:** the session through the `api-usage` skill where API access exists; otherwise the user.

- [ ] **Step 1: Resend domain.** Add `verasig.io` to the Resend account (region `eu-west-1`). Read the records Resend returns; do not copy them from this plan.
- [ ] **Step 2: Cloudflare DNS.** Add exactly the records Resend lists (expected shape: one DKIM TXT at `resend._domainkey`, one TXT and one MX on Resend's `send` subdomain). Leave the root `v=spf1 -all`, the null MX and the DMARC record as they are: Resend signs with DKIM on `verasig.io`, which satisfies `adkim=s`. Verify in Resend until the domain shows verified.
- [ ] **Step 3: Resend API key** named `verasig-production`, sending access only, restricted to `verasig.io`. Write it to a scratchpad file, install it as the mac-server secret in Task 8, then `rm -P` the file. Never paste it in chat or a commit.
- [ ] **Step 4: Prove the relay** with one message from the scratchpad through `smtp.resend.com:465` (user `resend`) to the user's own address, using the same `build_password_reset_email` body with a dummy URL. Confirm delivery through the Resend API (`GET /emails/{id}` shows `delivered`), not by assumption.

---

### Task 8: mac-server configuration PR and release

**Files (mac-server repo):**
- Modify: `service-catalog.json` (add `smtp_password`, mode `640`, group `staff` to `verasig` required_secrets)
- Modify: `services/verasig/compose.yml` (`VERASIG_SMTP_PASSWORD_FILE: /run/secrets/smtp_password`, the secret in both lists)
- Modify: `services/verasig/config/production.env.example` (`VERASIG_SMTP_HOST=smtp.resend.com`, `VERASIG_SMTP_PORT=465`, `VERASIG_SMTP_TLS=ssl`, `VERASIG_SMTP_USER=resend`, `VERASIG_MAIL_FROM=Verasig <no-reply@verasig.io>`)
- Modify: `services/verasig/README.md`, `CHANGES.md`

- [ ] **Step 1: Install the secret** `ssh mac-server '~/server-admin/scripts/serverctl secret set verasig production smtp_password' < <scratch file>` and the five config values with `serverctl config set verasig production`.
- [ ] **Step 2: Open the mac-server PR**, wait for its check, rebase-merge it, and confirm the `apply` workflow run succeeds.
- [ ] **Step 3: Release.** PR `develop` → `main`, `Merge: release password reset by email (#N)`. Watch the Deploy run (its label carries the `develop` SHA; pick the newest run after the merge): build_and_push, deploy and smoke must succeed.
- [ ] **Step 4: Verify on the live site** with the user's own account email only: `POST https://verasig.io/api/auth/password/forgot` → 202; confirm delivery through the Resend API; ask the user to open the link and set a new password, or do it with them. Then `POST /api/auth/password/reset` with a garbage token → 400 and `POST /api/user/password/reset-request` → 404.
- [ ] **Step 5: Report** PR numbers, merge SHAs, Deploy run id, Resend message id and the live probes.

## Out of scope, named follow-ups

- Email-change confirmation page (`/confirm-email?token=…`) so `send_email_confirm` can go through the same mailer.
- Request throttling on the public auth routes (none exists anywhere in the API today; Cloudflare sits in front).
- Revoking existing login tokens after a reset (access tokens are stateless, 7-day TTL, no revocation list).
