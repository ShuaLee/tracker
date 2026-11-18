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

*(Rewritten 2026-11-17 at the end of the `Josh`-machine session; the entries below
record how it got here.)*

- **Plan version:** v2 (backend first). Django admin is the working interface. PLAN.md's
  real Part 2 frontend (grid layout, charts, Targets screen) is not started. `frontend/`
  is a separate, deliberately unstyled **test harness** for exercising the API by hand -
  don't confuse the two.
- **There is no v1 code.** PLAN.md §1.12 / §2.1 describe a v1 `holdings` / `layouts` /
  React app as design only - none of it was ever built. Everything is built outward from
  users/profiles.
- **Product shape: individuals only.** Every user has exactly **one portfolio**, created
  at signup. No advisors, clients or `Profile.role` - explored and removed this session;
  advisors and organizations are future ideas (PLAN.md B9 / B10).
- **Branch:** all of this session's work is on `accounts-complete-and-holdings` (not yet
  merged into `main` or pushed). Merge/fast-forward `main` when ready.
- **Done:**
  - **B1 `accounts`** - complete: custom `User`/`Profile`/`SecurityEvent`, every
    `/api/auth/` endpoint (incl. `logout-all/`, `security-events/`, `options/`),
    timezone validation, axes lockout, DRF throttling, admin with session-ending
    deactivate, `seed_users`.
  - **B1a tiers** (PLAN.md §1.3a) - structure only: `accounts.Subscription` (`free` |
    `paid`, staff-set), limits table in `accounts/tiers.py` - **nothing gated yet**.
  - **B2 `holdings`** - `Portfolio` + `PortfolioAccess` (owner/manager/viewer, only owner
    rows exist), one access module (`holdings/access.py`), `/api/portfolios/`
    (list / retrieve / PATCH), signup creates the portfolio.
  - **Harness** covers every auth flow, settings, security activity, plan display, and
    a Portfolio tab (rename / currency).
  - 123 tests pass (accounts, holdings, dependency rule); `check --deploy` clean against
    prod settings.
- **Still deferred from B1.5:** `seed_demo --user` (needs assets) and duplicating
  starter template pages into a new portfolio (needs `layouts`).
- **Dev DB is per-machine** (not committed). After pulling, a machine runs `uv sync`,
  `migrate` (which backfills each existing user's portfolio and Free subscription), and
  optionally `seed_users`. Superuser on each machine: `joshgrein2@gmail.com` - change
  the documented dev password before it matters.
- **Next action:** **B2.5** - `Account`, `AssetClass`, `AssetField`, `Asset` inside the
  user's portfolio, every endpoint scoped through `holdings/access.accessible_portfolios`.
  First tier decision likely lands here (asset cap on Free?) - and the downgrade rule
  in PLAN §1.3a must be settled before any gate ships.

### Machine / environment notes

| | |
|---|---|
| Repo path (`engineer` machine) | `C:\Users\engineer\Desktop\tracker` |
| Repo path (`Josh` machine) | `C:\Users\Josh\Desktop\tracker` |
| Repo path in PLAN.md | `C:\Users\Josh\Desktop\portfolio-dashboard` — stale, do not treat as authoritative |
| Python | 3.12 (`backend/.python-version`) |
| Venv | `backend/.venv`, **not committed** — a fresh machine must bootstrap it (see README.md) |
| Package manager | uv, installed *inside* the venv, pinned in the dev group so `uv sync` cannot remove it |
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
