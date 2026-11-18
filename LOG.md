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

- **Plan version:** v2 (backend first). Django admin is the working interface; PLAN.md's
  real Part 2 frontend (grid layout, charts, the Targets screen) is still frozen and not
  started. A separate, minimal `frontend/` now exists purely to exercise the `accounts`
  API by hand - see the 2026-11-17 "frontend scaffold" entry. Don't confuse the two.
- **Current step:** B1 (`accounts`: custom user model, auth endpoints, protections,
  user admin) — **done**, committed as `8b51bcd`. See the 2026-11-17 entry below.
- **What exists:** `config/settings/` split into `base.py`/`dev.py`/`prod.py`; a full
  `accounts` app (custom `User`/`Profile`/`SecurityEvent` models, every `/api/auth/`
  endpoint from PLAN.md §1.3, django-axes lockout, DRF throttling, a polished admin);
  53 passing tests plus a project-wide import-dependency-rule test. `manage.py migrate`
  has been run against the dev SQLite DB and a superuser exists there
  (`joshgrein2@gmail.com` — change that password before relying on it for anything real).
  **The dev DB is per-machine** (not committed): the `Josh` machine has its own, seeded
  2026-11-17 — see that day's "second machine" entry.
- **Frontend harness** now covers every B1 flow (register, verify, login, forgot/reset,
  change password/email, deactivate, log out everywhere, security activity), which
  satisfies PLAN.md §2.2's B1 row.
- **User/profile layer is complete** as of 2026-11-17 (see that day's last entry). The
  only B1.5 items still open need `holdings`: default portfolio + owner access row on
  signup, and `seed_demo --user`.
- **Explicitly deferred (not forgotten):** B1.1's "sign-up creates a default Portfolio +
  owner PortfolioAccess row" is NOT implemented. `holdings` doesn't exist yet, and
  PLAN.md §1.1 says `accounts` must import nothing else in the project — building that
  signal inside `accounts` would violate that rule. It belongs in `holdings` (a receiver
  on `User` via `get_user_model()`) once step B2 adds that app.
- **Next action:** step B2 — `holdings` app: `Portfolio`, `PortfolioAccess` roles/scoping,
  and the deferred default-portfolio-on-signup receiver described above. The frontend
  scaffold (below) was a side excursion for manual testing, not part of the backend
  build order - it doesn't block or get blocked by B2.
  **There is no v1 code.** PLAN.md §1.12/§2.1 described `holdings`/`layouts`/a full React
  app as "existing" - confirmed with the user 2026-11-17 that none of it was ever built;
  both sections are now marked as design only. Everything is built outward from
  users/profiles, so B2 creates `holdings` from nothing.

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
