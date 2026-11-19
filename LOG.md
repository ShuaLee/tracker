# Work Log

A running record of what has been done and **why**, so that a Claude Code session on
either machine can pick up without re-deriving context. [PLAN.md](PLAN.md) says what we
intend to build; this file says what has actually happened and what state the repo is in.

## How to use this file

**At the start of a session:** read *Current state* below, then the last two or three
entries. Check them against `git log` and the working tree — the log can lag reality if
someone forgot to write an entry.

**At the end of a session (or after anything worth remembering):** append an entry to the
bottom of *Entries*, update *Current state*, and commit `LOG.md` with the work it
describes. Entries are append-only — correct an earlier entry by writing a new one that
says what changed, never by rewriting history.

Record decisions and dead ends, not a diff. The commit already shows what changed; the log
exists for the reasoning that is not in the code: why an approach was rejected, what is
deliberately deferred, what is half-finished and what breaks if you touch it.

Entry format:

```
### YYYY-MM-DD — short title
**Machine:** <machine> · **Commit:** <sha or "uncommitted">

What happened, why, and anything the next session needs to know.
```

---

## Current state

*(Rewritten 2026-11-18 after the restart onto Plan v3.1. Entries before the
2026-11-18 "Restart" entry describe the old plan - its step names (B1, B2.5...) and
app names (`accounts`, `holdings`) no longer exist.)*

- **Read first:** `PRODUCT.md` (intent) and `PLAN.md` (**Plan v3.1** - steps 1-12). The
  old v2 plan was replaced wholesale on 2026-11-18.
- **Product:** individuals only (no advisors/clients/sharing), positions only (no
  transactions), one invisible portfolio per user, Free + paid plans.
- **Current step:** **Step 2 (asset types, accounts, holdings) - built, awaiting your
  confirmation** before step 3 (CSV import). Step 1 confirmed by the user 2026-11-18.
- **What exists:**
  - `users` app (rebuilt from scratch, replaces `accounts`): email-login `User`,
    `Profile` (display name, base currency, timezone), `Plan` + `Subscription`
    (Free seeded by migration, plans editable in admin, `users.entitlements.entitlements(user)`
    - nothing enforced until step 11), `SecurityEvent` audit trail. `/api/auth/` endpoints
    for register / verify / resend, login / logout / logout-all, me / options /
    security-events, password change / reset / confirm, email change, delete account.
    Protections per PLAN step 1: Argon2, password rules, per-IP + per-email throttles,
    axes lockout, single-use expiring tokens, secure cookies in prod, secrets in `.env`.
  - `portfolios` app (replaces `holdings`): `Portfolio` created at signup, base currency
    follows the profile, `portfolios.access.accessible_portfolios(user)` is the only access
    check. **No portfolio API** - PLAN 2.1 says the UI never mentions portfolios. Step 2
    added `Account` and `ExchangeRate` (manual FX pairs).
  - `assets` app (step 2): `AssetType` (8 standard, seeded; plus user-made), `AssetField`
    (text / number / date / choice), `Holding` (positions), `valuation.py` (pure
    functions: value, cost, gain, `totals()`, `value_by()`), admin with custom-field
    inputs and a read-only **Portfolio summaries** page. **Admin only, no API yet.**
  - `frontend/` test harness (unstyled, separate from step 10's real frontend): every
    auth flow + settings. Nothing for holdings (no API).
  - 122 tests; `check --deploy` clean against prod settings.
- **Dev DB is per-machine** and was **reset** on 2026-11-18 (app rename = fresh
  migrations). Any machine with an old database must delete `backend/db.sqlite3` and
  `migrate` from scratch, then `createsuperuser` and optionally `seed_users`.
- **Next action:** you enter your own holdings in admin (PLAN step 2's "done when") and
  confirm step 2; then **step 3 - CSV import** (PLAN 2.9: IBKR Open Positions + generic;
  pick an account → upload → review new / changed / missing → apply; matched holdings
  updated in place; each import kept as an `ImportBatch`). Built in admin.
  - **Blocked on input from you:** your two IBKR exports (TFSA, FHSA) - or at least
    their header row plus a couple of rows with fake numbers. IBKR's Open Positions
    layout depends on how the report is set up, so the parser should be built against
    the real file, not a guess.
  - **Proposed defaults (2026-11-19, not yet confirmed):** the file's price becomes
    `current_price` until live prices (step 9), with `price_updated_at` = import time;
    "missing" holdings default to **keep** (removal must be ticked); new holdings' asset
    type from IBKR's asset class (stocks/ETFs → `stocks`, bonds → `bonds`, crypto →
    `crypto`) or the generic file's `asset_type` column (blank → `stocks`); match on
    **symbol + currency** within the account, so a TSX and a US listing of the same
    ticker stay separate holdings.

### Machine / environment notes

| | |
|---|---|
| Repo path (`engineer` machine) | `C:\Users\engineer\Desktop\tracker` |
| Repo path (`Josh` machine) | `C:\Users\Josh\Desktop\tracker` |
| Python | 3.12 (`backend/.python-version`) |
| Venv | `backend/.venv`, **not committed** — a fresh machine must bootstrap it (see README.md) |
| Package manager | uv, installed *inside* the venv, pinned in the dev group so `uv sync` cannot remove it |
| VS Code | `.vscode/settings.json` is gitignored, so each machine needs its own: `"python.defaultInterpreterPath": "${workspaceFolder}/backend/.venv/Scripts/python.exe"` and `"python.analysis.extraPaths": ["${workspaceFolder}/backend"]`. Without them Pylance reports `Import "django.conf" could not be resolved` (wrong interpreter) and can't find `users` / `portfolios` (the workspace is `tracker/`, the Django root is `backend/`). Then *Python: Select Interpreter* → `backend\.venv`. |
| `.env` | gitignored, machine-local. This machine's `.env` has a real generated `SECRET_KEY`; a fresh checkout copies `backend/.env.example` and generates its own (see README.md) — **the two machines do not and should not share one `.env`**. |

The two machines use different paths and different usernames, so never hard-code an
absolute path into the project. Anything machine-specific belongs in `.env` or this table.

---

## Entries

### 2026-11-16 — Django project initialized, dependencies locked
**Machine:** other · **Commit:** `3c652a7`

Created the repo: a stock Django 5.2 project (`config`) under `backend/`, plus `PLAN.md`,
`README.md` and `.gitignore`. No apps yet — deliberately, because the custom user model
has to be the first migration.

Why these choices:

- **Django 5.2** — current LTS, supported to April 2028, so the stack does not need a
  framework upgrade mid-build.
- **uv with a committed `uv.lock`** — both machines resolve to byte-identical versions.
  uv is installed in the project venv rather than globally so the two machines do not
  drift on uv's own version; it is listed in the dev dependency group because `uv sync`
  uninstalls anything absent from the lock file, including uv itself.
- **Dependencies declared up front** for steps that have not been built yet
  (`django-axes`, `requests`, `drf-spectacular`). They are locked but unused — that is
  intentional, so adding a step later does not also mean re-resolving the lock file.
- **No `migrate` run** and no `db.sqlite3`, for the `AUTH_USER_MODEL` reason above.

### 2026-11-17 — Added this log
**Machine:** `engineer` (`C:\Users\engineer\Desktop\tracker`) · **Commit:** uncommitted

Started `LOG.md` because work is moving between two machines and `PLAN.md` only records
intent, not what has actually been done. Verified while writing it that the working tree
is clean, `backend/` holds only `config/`, and there is no database or `.env` here — so
the repo state matches the single commit above.

Noted that `PLAN.md` § line 19 still gives the old path `C:\Users\Josh\Desktop\portfolio-dashboard`.
Left the plan unedited rather than quietly changing it; the correct path per machine lives
in the table above.

### 2026-11-17 — Step B1 (`accounts`) built in full
**Machine:** `engineer` (`C:\Users\engineer\Desktop\tracker`) · **Commit:** `8b51bcd`

Built all four parts of PLAN.md §1.3 B1, not just models+admin — confirmed with the user
up front that "good to go from the start" meant the whole step, matching its own "done
when" bar. Plan was written to `C:\Users\engineer\.claude\plans\merry-jingling-wreath.md`
before any code, after reading the actual installed `django-axes==9.0.0` source (not
guessed) to get the lockout-parameter syntax and username-resolution right.

**What landed:**
- `config/settings.py` → `config/settings/{base,dev,prod}.py`. `dev` is the default now
  (manage.py/wsgi/asgi); a real deploy must set `DJANGO_SETTINGS_MODULE=config.settings.prod`
  explicitly. `backend/.env.example` documents every env var; this machine's real `.env`
  got a freshly generated `SECRET_KEY`, retiring the insecure one Django's scaffold shipped.
- `accounts`: custom `User`/`Profile`/`SecurityEvent`, every `/api/auth/` endpoint from
  the plan's table, django-axes lockout (account+IP combination), dual-dimension DRF
  throttling (per-IP and per-submitted-email), a `UserAdmin` with the Django-documented
  custom-user-model forms, colored verified-badge, timezone/currency dropdowns, and the
  five actions the plan asked for (deactivate/reactivate/mark-verified/send-reset/unlock).
- `backend/tests/test_dependency_rules.py`: a generic AST-based check that `accounts`
  (and every future app) only imports what PLAN.md §1.1's dependency graph allows.
- 53 tests, all passing; `manage.py check --deploy --settings=config.settings.prod` clean
  against a fully-populated env; a real superuser created on this machine's dev DB
  (`joshgrein2@gmail.com` / `ChangeMe123456!` — rotate this before it matters).

**Bugs the tests caught, worth remembering if this code gets touched again:**
- Plain-text email templates still autoescape by default in Django's template engine —
  `&` in a reset/verify link became `&amp;`, silently truncating the query string at
  `parse_qs` time. Every email `.txt` template is wrapped in `{% autoescape off %}`.
- `ChangePasswordView`/`PasswordResetConfirmView` call `validate_user_password()` directly
  in the view body, not inside a serializer's `validate()` — so Django's
  `core.exceptions.ValidationError` wasn't being caught (DRF only auto-converts that
  exception when it's raised *inside* serializer validation). Added
  `_password_strength_error()` in `views.py` to catch it explicitly.
- `ProfileInline` on `UserAdmin`'s **add** page demanded inline-formset management data
  that nothing was submitting, because `Profile` doesn't exist until the `post_save`
  signal creates it — standard fix is `get_inline_instances()` returning `[]` when
  `obj is None`.
- With only `SessionAuthentication` configured, DRF coerces unauthenticated responses
  from 401 to **403** (no `WWW-Authenticate` header to justify a 401) — see
  `rest_framework.views.APIView.handle_exception`. Don't assume 401 for "not logged in"
  anywhere in this codebase.

**Deliberately deferred:** see "Current state" above re: the default-Portfolio-on-signup
signal, which belongs in `holdings`, not here.

### 2026-11-17 — Minimal frontend scaffold, for testing `accounts` only
**Machine:** `engineer` (`C:\Users\engineer\Desktop\tracker`) · **Commit:** uncommitted

Added `frontend/` (Vite 8 + React 19, Node 22.17 - matches PLAN.md's stack). This is
**not** PLAN.md Part 2's real frontend - it's a bare, intentionally unstyled harness with
exactly two screens (login; settings+logout) so the `accounts` API can be exercised by
hand instead of only through `curl`/admin. `src/App.jsx` checks `/api/auth/me/` on load
and switches between `LoginScreen`/`SettingsScreen` accordingly.

Deliberately did **not** install `react-grid-layout`, `recharts`, `lucide-react`, or
bundle the Inter font yet - those belong to the widget-grid/Targets screens (PLAN.md
§2.3), which don't exist. Add them when those screens are actually built, not before.

`src/api.js` handles Django's session-cookie + CSRF-header auth: GET `/api/auth/csrf/`
once on load to set the `csrftoken` cookie, then every unsafe request reads that cookie
fresh via `document.cookie` and sends it as `X-CSRFToken`. Worth remembering if this
breaks: `django.contrib.auth.login()` **rotates the CSRF token** on success (anti-fixation) -
a client must re-read the cookie after login, not reuse the pre-login value. Verified the
full login → authenticated PATCH → logout → rejected sequence end-to-end with curl against
both dev servers running together, not just that the frontend compiles.

`npm install` flags a high-severity `picomatch` advisory (transitive, via Vite's dev-time
glob handling). Left it - no production exposure, and the suggested fix downgrades
Vite 8→6. Revisit if `npm audit` still flags it once Vite's own dependency updates.

Vite's dev server binds to `localhost` (IPv6 `::1` on this machine), not `127.0.0.1` -
use `http://localhost:5173`, which is also the exact origin backend/.env's
`CORS_ALLOWED_ORIGINS`/`CSRF_TRUSTED_ORIGINS`/`FRONTEND_URL` already expect.

### 2026-11-17 — Second machine bootstrapped; full B1 frontend; B10 added to plan
**Machine:** `Josh` (`C:\Users\Josh\Desktop\tracker`) · **Commit:** uncommitted

**Bootstrap.** Fresh checkout: created `backend/.venv` and `uv sync` per README, generated
this machine's own `backend/.env` from `.env.example`, ran `migrate`. The dev DB is not
shared between machines, so the superuser from the B1 entry did not exist here - recreated
`joshgrein2@gmail.com` (superuser, `ChangeMe123456!`) plus test users `alice`/`bob`/`carol`
(advisor)/`dave` (unverified)/`erin` (inactive) `@example.com`, all `TestPass123!`. Seeded
with a throwaway shell script, not a committed command - `seed_demo` (PLAN.md B1.5) is
still the right home once `holdings` exists.

**Gotchas hit, worth knowing:**
- `frontend/src/api.js` defaulted to `http://127.0.0.1:8000` while Vite serves
  `localhost:5173`. Those are different *sites*, so the `SameSite=Lax` session cookie was
  never sent on fetches and every authenticated call 403'd right after a 200 login. Default
  is now `http://localhost:8000` (and `.env.example`). The 2026-11-17 scaffold entry's curl
  test didn't catch this because curl ignores SameSite.
- Failed logins against a not-yet-existing account still count: axes locked the email
  (cleared with `manage.py axes_reset`), and the per-account DRF throttle (10/hour) kept
  answering 429. Throttle counts live in the default LocMemCache, i.e. inside the
  `runserver` process - restarting it clears them; nothing on disk does.

**Backend fix:** `accounts/emails.py` interpolated the email into verify/change links
unencoded, so `a+b@x.com` arrived as `a b@x.com` and verification failed. Links are now
built with `urlencode`; regression test `test_verify_link_survives_plus_address` (fails
without the fix). All accounts tests pass.

**Frontend:** the harness now has register, forgot-password, `/verify-email` and
`/reset-password` landing screens (matching the paths `emails.py` links to - no router
library, `App.jsx` reads `location.pathname`), and a settings page with profile,
resend-verification, change password, change email and deactivate. "Delete account" is
labelled as deactivation, because that's all the API does (PLAN.md: hard delete is an admin
action). Still intentionally unstyled.

**Plan:** added **B10 — Organizations** (PLAN.md §1.11, renumbering the later sections):
an org owner sees all the org's advisors and their org-tagged clients, read-only, built on
B9's `PortfolioAccess` rather than a hierarchy. It replaces B9's one-line `Practice` idea.
Also added a B2 note: route every access check through one `accessible_portfolios()` so
B10 is additive.

**User/profile layer finished** (same session, after confirming there is no v1 code and
the build goes outward from users/profiles). Gaps found by reading the code, now closed:
- `PATCH me/` accepted any timezone string (`"Not/AZone"` saved fine - only the admin form
  restricted it). `Profile.timezone` now has a model validator (`validation.validate_timezone`,
  migration `0002`), which `ProfileSerializer` picks up. There were **no tests for `me/` at
  all** - `test_me.py` added.
- `role` was self-assignable via `PATCH me/`. Made read-only (staff set it in admin). The
  user hadn't answered self-service vs admin-only when told to finish; chose the
  conservative default - reverse it in `ProfileSerializer.Meta.read_only_fields` if wanted.
- PLAN B1.3's "log out everywhere" existed only as `sessions.end_all_sessions()`; now
  `POST logout-all/` (optional `keep_current`). Plus `GET security-events/` (own last 50
  `SecurityEvent`s) and `GET options/` (currency/role/timezone choices; the frontend no
  longer hard-codes them). New event types `logout_all`, `reactivated`.
- Admin deactivate used `queryset.update()` - no audit row, sessions left alive until the
  next request. Now ends sessions and logs; reactivate logs; new "end all sessions" action.
  Admin-originated audit rows pass `request=None` so the staff member's IP isn't recorded
  against the target account.
- `manage.py seed_users` replaces the throwaway seeding script (dev only, idempotent).
- 78 tests pass; live HTTP smoke test (csrf → login → options → bad-tz 400 → role ignored →
  security-events → logout-all both modes) passed against a temporary `runserver`.

Dev throttle rates were **not** loosened: `test_throttling.py` asserts the real 5/min
rates and runs under dev settings, so a dev-only override would break it. README documents
the restart / `axes_reset` workarounds instead.

**What's next:** B2 - `holdings` from nothing (`Portfolio`, `PortfolioAccess`, default
portfolio on signup, one `accessible_portfolios()` check). The plan's build order then
needs a new step for `Account`/`AssetClass`/`Asset` before B3, which assumes they exist.

Committed as `0901037` on new branch `accounts-complete-and-holdings` (not `main` - the
harness rule is to branch before committing; merge/fast-forward when ready).

### 2026-11-17 — B2 first pass: `holdings` with Portfolio + PortfolioAccess
**Machine:** `Josh` (`C:\Users\Josh\Desktop\tracker`) · **Commit:** uncommitted (branch
`accounts-complete-and-holdings`)

Built `holdings` from nothing - only what a user *owns* and *who can use it*, nothing
inside a portfolio yet. Design decisions worth keeping:

- **One access module.** `holdings/access.py` (`accessible_portfolios(user, min_role)`,
  `role_for`, `has_role`, `READ`/`EDIT`/`OWN`) is the only code that reads access rows.
  `accessible_portfolios` annotates `my_role` via a **Subquery**, not
  `.annotate(F("access__role"))` - the latter's join can silently pick a different row
  once B9 adds non-owner rows. Inactive/anonymous users get `none()` here as well as at
  login, so a stale session can't see anything.
- **404 vs 403:** the viewset's queryset *is* `accessible_portfolios`, so no access at all
  is a 404 indistinguishable from a missing id (tested). `HasPortfolioRole` then gives 403
  only to users who can see the object but lack the role (viewer PATCH, manager DELETE).
- **Owner row integrity** is enforced by DB constraints (one row per user+portfolio; one
  *active* owner per portfolio - revoked owner rows don't count), and every creation path
  goes through `services.create_portfolio` / `add_owner_access` (API, signup signal,
  admin). Admin makes `owner` read-only after create and the access inline read-only;
  changing either directly would desync them - ownership transfer is a B9 service.
- **Last-portfolio rule:** an owner can't delete their only portfolio (400), so every
  user always has one to land in. Admin bypasses this (operator tool).
- **Signal order matters:** `holdings` is listed after `accounts` in `INSTALLED_APPS` so
  the Profile exists before the default portfolio reads its currency. Profile currency
  is CAD at signup anyway; the dependency is noted in settings.
- **Backfill migration** `holdings/0002` gave every pre-existing user a default portfolio
  (ran on this machine's dev DB: 6 users, 6 portfolios). The other machine gets the same
  on `migrate`.
- `Portfolio.base_currency` reuses `accounts.Profile.Currency` (allowed: holdings may
  import accounts). Move to `marketdata` once B3 owns currencies.
- Dropped v1's `summary_metrics` from `Portfolio` - it's a display preference for
  `layouts`, not portfolio data.

115 tests pass (37 new in `holdings/tests/`: models/constraints/backfill, access,
cross-user isolation + roles over the API, admin). Live HTTP smoke test against a
temporary `runserver` passed (list, create, rename, 404 on another user's portfolio,
400 on deleting the last one).

PLAN.md: B1.1's portfolio bullets annotated as built in B2; B2 got an "as built" note;
build order gained **B2.5** (`Account`/`AssetClass`/`AssetField`/`Asset`), which B3 needs.

**Ownership model decided (user, same session).** Questioned whether portfolios should
exist at all; settled on: an individual owns exactly one; an **advisor owns one per
client** (the client's book is the advisor's); the **client logs in as a viewer**. So
`Portfolio` stays (advisors need many; access needs something to attach to), and the
plan's old B9 "client claims the portfolio / ownership transfers" flow is dropped.
Accepted consequence, written into PLAN.md B2: client data belongs to the advisor.

- Code: `services.can_create_portfolio()` - only `role = advisor` may create beyond the
  first portfolio (an individual who owns none may create one). This leans on `role`
  being staff-set/read-only via the API (decided earlier today) - if `role` ever becomes
  self-service, this check needs another gate. 120 tests pass (new: creation rules,
  advisor-owns/client-views, client can't see the advisor's other clients).
- PLAN.md: B2 intro rewritten as the ownership model; B9 rewritten (advisor invites
  client as viewer; no transfer; invite signups must skip the default portfolio); B10
  moved the org tag to `Portfolio.organization` and made "advisor leaves" a portfolio
  transfer within the org.
- Open for B9, noted in the plan: a client who signs up via invitation currently would
  still get an empty "My portfolio" from the signup receiver.

**Then scoped down (user, same session):** advisor-owned client portfolios are a *future
idea*, not current scope - "client access would purely be for viewing" when it happens.
So for now **every user has exactly one portfolio**. Removed what was building ahead:
`can_create_portfolio`, `delete_portfolio`/`LastPortfolioError`, and the API's create and
delete - `/api/portfolios/` is now list / retrieve / PATCH. Kept the access-role table and
`HasPortfolioRole` (cheap; B9 stays additive) and their tests, which grant rows directly.
**No DB unique constraint on `Portfolio.owner`** on purpose: B9's advisors would need
many, and staff can still add one in admin. 116 tests pass. PLAN.md B2 now says "now:
one per user" and lists advisor/client as the future idea; B9 notes it brings back an
advisor-only create endpoint.

**Then settled for real (user answered three explicit questions, same session):**
1. Anyone who registers is an advisor (`Profile.role` default -> `advisor`; migration
   `accounts/0003` also switches existing profiles).
2. Clients are a `holdings.Client` record (name, email, phone, notes) with exactly one
   portfolio, owned by the advisor. Clients don't log in.
3. Advisors still get a personal portfolio at signup, but **locked** ("make it so they
   can not use it"). "This will be as far as we get with the advisor right now" - next,
   the app is completed for a single (client) portfolio.

Implementation notes for whoever touches this next:
- `Client` has **no `advisor` field** on purpose - it belongs to whoever owns its
  portfolio, so there's nothing to drift. List clients only via
  `access.accessible_clients()`.
- **Locking** is one filter in one place: `access.usable_portfolios()` =
  `accessible_portfolios()` minus `client IS NULL`. Every endpoint (and every B2.5 child
  endpoint) must scope through `usable_portfolios`, not `accessible_portfolios`.
- `Portfolio.client` is a nullable one-to-one with `CASCADE`: deleting a client deletes
  the portfolio (and later, all holdings in it). The API's client delete is owner-only.
- Holdings migrations were **regenerated** (never committed/shared): `0001` now includes
  `Client`. Done via `migrate holdings zero` on this machine's dev DB.
- `seed_users` roles changed (all advisors; carol is the demoted "individual" case);
  new `holdings` command `seed_clients` gives alice 2 clients and bob 1.
- Frontend harness: new Clients tab (list / add / edit client + portfolio name & currency
  / delete). 127 tests pass; live HTTP smoke test passed (create, rename portfolio,
  cross-advisor 404, individual 403, delete cascades portfolio).

### 2026-11-17 — Advisor layer removed: individual-only for now
**Machine:** `Josh` (`C:\Users\Josh\Desktop\tracker`) · **Commit:** uncommitted (branch
`accounts-complete-and-holdings`)

User: "just remove the advisor. we will build this out as just the individual for now."
Removed everything advisor-shaped; none of it had been committed, so migrations were
**regenerated** rather than reversed (dev DB rolled back with `migrate holdings zero` /
`migrate accounts 0002` first):

- `holdings.Client`, `Portfolio.client`, `/api/clients/`, `access.usable_portfolios` /
  `accessible_clients`, `services.create_client` / `can_create_clients`, the
  `seed_clients` command, `ClientAdmin` and the personal/client admin filter.
- **`Profile.role` removed entirely** (migration `accounts/0003_remove_profile_role`) -
  my call: with no advisors it distinguished nothing. It was part of the committed B1
  (`0901037`), hence a real migration rather than a regenerated one. Re-add it with
  the advisor work. `options/` no longer returns `roles`.
- Each user's single portfolio is simply *theirs* and usable (no "locked personal").
  `/api/portfolios/` = list / retrieve / PATCH. Kept the `PortfolioAccess` roles and
  `HasPortfolioRole` (sharing infrastructure, not advisor-specific).
- `seed_users` no longer sets roles (carol is now just another verified user, AUD).
- Frontend: Clients tab replaced by a Portfolio tab (view/rename/change currency).

Design notes for if advisors come back (were built and tested before removal): `Client`
record with **no `advisor` field** (belongs to whoever owns its portfolio, so nothing to
drift); `Portfolio.client` nullable one-to-one, CASCADE; advisor's signup portfolio
"locked" by a single filter in the access module so every endpoint inherits it; client
creation gated on staff-set `role`. PLAN.md B9 carries the summary.

115 tests pass; frontend lints and builds.

### 2026-11-17 — Tiers (structure only)
**Machine:** `Josh` (`C:\Users\Josh\Desktop\tracker`) · **Commit:** uncommitted (branch
`accounts-complete-and-holdings`)

User wants pricing tiers - "free, something, and a highest tier, maybe just 2 tiers to
start a free and paid. idk yet". Built only the structure, so the open decisions (how
many tiers, prices, what each unlocks) stay cheap:

- `accounts.Subscription` (one-to-one with User, `tier` = `free` | `paid`, timestamps),
  created by the same signal as Profile; migration `0004` backfills Free for existing
  users. A separate model rather than a Profile field so billing fields (provider ids,
  status, period end) land next to `tier` later without moving data.
- `accounts/tiers.py`: `TIER_LIMITS` (empty for both tiers - nothing to gate yet),
  `tier_for` / `limit` / `allows`. `limit()` raises `KeyError` on an unknown key on
  purpose. Rule written into PLAN §1.3a: features check limits, never tier names.
- Admin: Subscription inline on the user page, tier column + filter, "Set tier: Free /
  Paid" actions. `me/` returns `tier` read-only (test proves PATCH can't change it).
- Frontend Settings shows "Plan: Free/Paid".
- PLAN.md: new §1.3a (what's built, candidate gates per step, and a downgrade rule to
  decide before the first gate: never delete data, make over-limit items read-only);
  build order row **B1a**.

123 tests pass.

### 2026-11-17 — Session summary (`Josh` machine)
**Machine:** `Josh` (`C:\Users\Josh\Desktop\tracker`) · **Commit:** `0901037`, then the
commit that adds this entry (branch `accounts-complete-and-holdings`)

The entries above are long and include reversals; this is the short version, in order:

1. **Bootstrapped this machine** (venv, `.env`, migrate, superuser) and fixed the
   harness's `127.0.0.1` vs `localhost` cookie bug.
2. **Finished B1** - plus-address email links, timezone validation, `me/` tests,
   `logout-all/`, `security-events/`, `options/`, admin deactivate ending sessions,
   `seed_users`; full auth screens in the harness. Committed as `0901037`.
3. **Started B2 `holdings`** from nothing (there is no v1 code): `Portfolio`,
   `PortfolioAccess`, one access module, `/api/portfolios/`, signup-created portfolio.
4. **Ownership model went back and forth** - multiple portfolios per user → one per
   user → advisors owning one portfolio per client (with a `Client` model, built and
   tested) → **individuals only**. Final: one portfolio per user; the advisor design is
   kept as a future idea in PLAN.md B9 and in the "Advisor layer removed" entry above.
   `Profile.role` was removed with it.
5. **Added tiers** (structure only): `Subscription` Free/Paid + `tiers.py` limit table.
   Discussed and kept: limits in code (standard at 2-3 plans), tier on its own model
   rather than Profile (billing state vs user preferences).
6. **Plan updates:** B10 Organizations (future), §1.3a Tiers, B2.5 inserted before B3
   (B3 needs `Asset`), v1 sections marked design-only.

Because nothing after `0901037` had been committed or shared, the holdings migrations
were **regenerated** during step 4 rather than reversed. Any other machine that somehow
applied an intermediate holdings migration should `migrate holdings zero` before
pulling - in practice none did, since none of it left this machine.

### 2026-11-17 — `PortfolioAccess` removed
**Machine:** `Josh` (`C:\Users\Josh\Desktop\tracker`) · **Commit:** the commit that adds
this entry (branch `accounts-complete-and-holdings`, after `eb10d60`)

User asked what PortfolioAccess was for; with one portfolio per user and no sharing, it
only duplicated `Portfolio.owner` (every row was an owner row) while costing two DB
constraints, owner-row bookkeeping in every create path, an admin inline, a permission
class and role tests. User agreed to remove it.

- `holdings/access.accessible_portfolios(user)` is now just `Portfolio.objects.filter(owner=user)`
  (none for anonymous/inactive). **Keep routing every check through it** - that's what
  makes sharing (B9) a change in one function instead of a sweep of endpoints.
- Removed: `PortfolioAccess` model, `permissions.HasPortfolioRole`, `role_for` /
  `has_role` / `my_role`, `services.add_owner_access`, the access inline and access
  admin. `/api/portfolios/` serializer no longer returns `owner_email` / `my_role`.
- **Migrations regenerated again, even though `eb10d60` was committed:** that commit was
  never pushed, and this machine's dev DB was the only one that applied it (rolled back
  with `migrate holdings zero`). So `holdings/0001` now creates only `Portfolio`, and the
  `0002` backfill creates only portfolios. If any other DB ever applied `eb10d60`'s
  holdings migrations, roll holdings back to zero before migrating.
- PLAN.md B2 rewritten (owner-only scoping, sharing notes say B9 re-adds the table);
  B1.1/B1.4/B1.5/B9/build-order references updated. Frontend Portfolio tab no longer
  reads `my_role`.

109 tests pass; frontend lints and builds.

### 2026-11-18 — Restart onto Plan v3.1; user app rebuilt as `users`
**Machine:** `Josh` (`C:\Users\Josh\Desktop\tracker`) · **Commit:** the commit that adds
this entry (branch `accounts-complete-and-holdings`)

**New plan.** The user replaced `PLAN.md` with **Plan v3.1** (personal wealth app:
holdings of any kind, tags, nested targets, user-built sheets of widgets; positions
only; competing with Kubera / Snowball) and added `PRODUCT.md` (mission, users,
principles - "if the two disagree, PRODUCT.md is the intent"). Everything below this
entry follows v3.1; earlier entries refer to the old plan.

**Rebuilt the user app from scratch** (user: "completely rebuild the accounts app,
rename if necessary to have it be up to normal django convention"). Decisions, all
confirmed with the user except where noted:

- **`accounts` → `users`**, because v3.1 also has `portfolios.Account` (brokerage
  accounts); `accounts.User` beside `portfolios.Account` would confuse. PLAN.md §3
  updated to say `users`. **`holdings` → `portfolios`** to match the plan.
- **Dev DB reset** (approved): changing the user model's app label needs fresh
  migrations. Old `accounts` / `holdings` code and migrations deleted, not ported;
  `users/0001` + `0002_seed_free_plan`, `portfolios/0001`.
- **Extras beyond PLAN step 1 - user said "do whatever you think is best"; kept all
  four**, citing PRODUCT.md's "private by design" and "security as a feature": email
  verification, change email, **delete account (now a real delete** - user, profile,
  subscription, portfolio cascade; the audit row survives with the email), security log
  + log-out-everywhere. Self-service *deactivate* was dropped in favour of delete; staff
  can still deactivate/reactivate in admin.
- **Tiers now follow v3.1 2.11:** `Plan` model (slug, name, `entitlements` JSON,
  `is_default` - DB-constrained to one) + `Subscription` (user, plan, status, renews_at).
  Free is seeded by a data migration; Plus/Pro are added in admin when decided.
  `users.entitlements.entitlements(user)` is the one helper; an inactive (past due /
  canceled) subscription falls back to the default plan. This replaces the earlier
  code-table `tiers.py` approach - the plan asks for DB rows so plans can change in admin.
- **No portfolio API** and the harness's Portfolio tab is gone: PLAN 2.1 says the UI
  never mentions portfolios. The portfolio's `base_currency` follows the profile's via a
  `post_save` receiver in `portfolios` (users can't import portfolios). Revisit if a
  user can ever have two portfolios.
- `SecurityEvent` gained an `email` column so failed logins for unknown emails and events
  of deleted accounts still say who they were about.
- Django conventions: namespaced URLs (`app_name = "users"`, `reverse("users:login")`),
  `validators.py` (was `validation.py`), `verbose_name` on app configs, signals wired
  in `AppConfig.ready()`, a `raw` guard on post_save receivers.
- Dependency-rule test rewritten for v3.1's graph (`users ← portfolios ← assets ← tags ←
  targets ← sheets`; `history` / `imports` beside `assets`; `marketdata` imports nothing)
  plus a check that any new app is added to the rule.

**Verified:** 83 tests pass (written fresh, covering the old suite's cases plus plans,
entitlements, account deletion, email-change race, token expiry); `check --deploy`
clean; live HTTP smoke test (register → login → me → change currency → security events →
delete with wrong / right password → session gone, login refused, audit row kept);
frontend lints and builds. Dev DB re-seeded with `seed_users`; **no superuser yet** on
this machine - run `createsuperuser`.

Also: Pylance flagged `Import "django.conf" could not be resolved` - VS Code wasn't
using `backend\.venv` and didn't know `backend/` is the import root. Fixed with a local
(gitignored) `.vscode/settings.json`; the settings are in the environment table above
so the other machine can copy them.

### 2026-11-18 — Step 2: asset types, accounts, holdings
**Machine:** `Josh` (`C:\Users\Josh\Desktop\tracker`) · **Commit:** the commit that adds
this entry (branch `accounts-complete-and-holdings`) - committed at the user's request
**before** they confirmed step 2; confirmation (entering their own holdings) still pending.

User confirmed step 1 and asked for step 2. Built with the defaults proposed beforehand
(user didn't change them): **admin only, no API**; **`Instrument` and `yield_override`
wait for step 9**; **manual FX in a per-portfolio table**; custom field types text /
number / date / choice; account kinds brokerage / registered-retirement / bank / crypto /
physical / other.

- **`portfolios.Account`** (name unique per portfolio) and **`portfolios.ExchangeRate`**
  (`1 from = rate to`, explicit pair, inverse derived, DB checks: pair unique, currencies
  differ, rate > 0). Pairs rather than "rate to base" so a base-currency change needs no
  rate edits (tested).
- **`assets.AssetType`**: `portfolio` null = standard. 8 standard types seeded by
  migration with stable `key`s (for CSV import): all investment except Vehicles; Stocks,
  Bonds, Crypto marked `is_priced`. Real estate defaults to investment - override per
  holding for a home you live in. Unique names per portfolio, and separately among
  standard types (NULLs are distinct in a plain unique constraint).
- **`assets.AssetField`** has a `portfolio` FK the plan's table didn't list - otherwise a
  user's custom field on a *standard* type (e.g. Real estate → Address) would appear for
  every user. PLAN.md §3 updated. `key` is slugified from the name once and never changes
  (values in `Holding.custom_fields` are keyed by it); `normalize()` stores numbers as
  decimal strings and dates as ISO strings - no floats in JSON.
- **`assets.Holding`**: positions per PLAN 2.2. Blank currency → portfolio base on save.
  `price_updated_at` is set automatically whenever `current_price` changes (via
  `from_db` tracking; also handles `save(update_fields=...)`). DB check constraints keep
  quantity / avg cost / price non-negative. `asset_type` is **RESTRICT** (not PROTECT):
  a type in use can't be deleted on its own, but deleting a user/portfolio - custom types
  and holdings together - works (PROTECT would block that cascade; tested).
  `clean()` rejects another portfolio's type/account and validates custom fields against
  the holding's type (empty values dropped, unknown keys rejected).
- **`assets/valuation.py`** - plain functions, no DB except `portfolio_totals()`:
  value / cost / gain per holding; `Rates.convert` (same, direct, inverse, else None);
  `totals()` → net worth, investments, personal, cost basis, unrealized gain, plus
  **`unpriced`** and **`missing_rates`**: such holdings are left out and reported, never
  counted as zero or converted 1:1 (PRODUCT.md "numbers you can trust"). Cost basis
  counts holdings with an avg cost; gain only those with both price and cost.
  Full-precision Decimals; `money()` rounds only for display. `value_by()` groups by any
  key (used for breakdowns now, widgets later).
- **Admin**: holdings form shows the type's custom fields as real inputs once saved
  (`get_form` strips the dynamic `custom__` names because the admin builds the form
  class from fieldsets and would reject non-model fields); changing type drops old
  custom values. **Portfolio summaries** (`assets.PortfolioSummary`, a proxy of
  Portfolio, living in `assets` because `portfolios` may not import `assets`) shows
  totals, by-type and by-account breakdowns and what was left out. Portfolio admin has
  account and exchange-rate inlines.
- **`seed_holdings`** dev command: alice gets 3 accounts, USD→CAD 1.37 and 7 holdings
  (USD + CAD stocks, one without avg cost, gold, cash, a car, a "Watches" custom type
  with Brand/Reference/Condition). Hand-calculated totals, asserted in a test: net worth
  **115,871.00 CAD**, investments 74,371.00, personal 41,500.00, cost basis 73,499.00,
  gain −683.10. Seeded into this machine's dev DB.

122 tests pass (39 new); migrations clean; `check` clean.

User asked how asset types work (explained: standard vs user-made, what a type
controls, the rules above, admin-only for now, and types = *what it is* vs step 4's
tags = *how you classify it*). No design change came out of it.
