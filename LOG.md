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

- **Plan version:** v2 (backend first). Django admin is the working interface; the React
  frontend is frozen and not yet in this repo.
- **Current step:** B1 (`accounts`: custom user model, auth endpoints, protections,
  user admin) — **built and tested, not yet committed**. See the 2026-11-17 entry below.
- **What exists:** `config/settings/` split into `base.py`/`dev.py`/`prod.py`; a full
  `accounts` app (custom `User`/`Profile`/`SecurityEvent` models, every `/api/auth/`
  endpoint from PLAN.md §1.3, django-axes lockout, DRF throttling, a polished admin);
  53 passing tests plus a project-wide import-dependency-rule test. `manage.py migrate`
  has been run against the dev SQLite DB and a superuser exists there
  (`joshgrein2@gmail.com` — change that password before relying on it for anything real).
- **Explicitly deferred (not forgotten):** B1.1's "sign-up creates a default Portfolio +
  owner PortfolioAccess row" is NOT implemented. `holdings` doesn't exist yet, and
  PLAN.md §1.1 says `accounts` must import nothing else in the project — building that
  signal inside `accounts` would violate that rule. It belongs in `holdings` (a receiver
  on `User` via `get_user_model()`) once step B2 adds that app.
- **Next action:** step B2 — `holdings` app: `Portfolio`, `PortfolioAccess` roles/scoping,
  and the deferred default-portfolio-on-signup receiver described above.

### Machine / environment notes

| | |
|---|---|
| Repo path (this machine) | `C:\Users\engineer\Desktop\tracker` |
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
**Machine:** `engineer` (`C:\Users\engineer\Desktop\tracker`) · **Commit:** uncommitted

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
