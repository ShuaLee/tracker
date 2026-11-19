# Personal Wealth App

Read [PRODUCT.md](PRODUCT.md) (what and why) and [PLAN.md](PLAN.md) (how and in what
order) first. [LOG.md](LOG.md) records what has been done. Backend first: Django + DRF in
`backend/`.

## Apps (`backend/`)

| App | Holds |
|---|---|
| `users` | `User` (email login), `Profile`, `Plan` / `Subscription` (tiers), `SecurityEvent`; the `/api/auth/` endpoints |
| `portfolios` | `Portfolio` - one per user, created at signup, never shown in the UI |

`backend/tests/test_dependency_rules.py` enforces which app may import which (PLAN.md 3).

## Setup (Windows, Python 3.12)

uv is installed inside the project venv rather than globally, so a fresh checkout
needs it bootstrapped with pip once:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install uv
.venv\Scripts\uv sync
copy .env.example .env
# then edit .env - at minimum, generate a DJANGO_SECRET_KEY:
.venv\Scripts\python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py createsuperuser
.venv\Scripts\python manage.py seed_users   # optional demo users, see below
.venv\Scripts\python manage.py check
```

`backend/.env` and `backend/db.sqlite3` are gitignored - every checkout needs its own,
so the superuser and demo users have to be created on each machine.

### Demo users

`manage.py seed_users` creates (or resets) one account per interesting state, all with
password `TestPass123!` (override with `--password`). Refuses to run unless `DEBUG` is on.

Each user gets a profile, a portfolio and the Free plan automatically.

| Email | State |
|---|---|
| `alice@example.com` | verified (CAD) |
| `bob@example.com` | verified (USD) |
| `carol@example.com` | verified (AUD, Sydney) |
| `dave@example.com` | email **not verified** |
| `erin@example.com` | **inactive** - login always fails |

### Locked out while testing?

- Five bad logins lock that email + IP (django-axes): `manage.py axes_reset`.
- `429 Request was throttled`: DRF rate limits (5/min per IP, 10/hour per email) live
  in the in-memory cache, so restarting `runserver` clears them.

## Frontend (test harness)

`frontend/` is a deliberately unstyled React app for exercising the auth API by hand.

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173 - use localhost, not 127.0.0.1
```

Emails print in the `runserver` terminal in dev; paste their links into the browser.

## Settings

`config/settings/` is a package, not a single file:

- `base.py` - everything shared; reads secrets/config from `backend/.env` via
  `django-environ` (see `.env.example` for every variable it reads).
- `dev.py` - local development. This is the **default** (`manage.py`, `wsgi.py` and
  `asgi.py` all fall back to `config.settings.dev` if `DJANGO_SETTINGS_MODULE` isn't set).
- `prod.py` - a real deployment must set `DJANGO_SETTINGS_MODULE=config.settings.prod`
  explicitly; nothing defaults to it.

```powershell
# Check a settings module without running it:
.venv\Scripts\python manage.py check --settings=config.settings.dev
.venv\Scripts\python manage.py check --deploy --settings=config.settings.prod
```

## Tests

```powershell
.venv\Scripts\python manage.py test          # everything, including the top-level
                                              # dependency-rule check in backend/tests/
.venv\Scripts\python manage.py test users    # just one app
```

## Dependencies

Managed with uv. Direct dependencies live in `backend/pyproject.toml`: runtime ones
under `[project.dependencies]`, development tools under `[dependency-groups].dev`.
`backend/uv.lock` is the generated lock file (exact versions and hashes); commit it,
never edit it by hand.

From `backend/`:

```powershell
.venv\Scripts\uv add <package>          # add a runtime dependency
.venv\Scripts\uv add --dev <package>    # add a development dependency
.venv\Scripts\uv remove <package>
.venv\Scripts\uv lock --upgrade         # upgrade within the allowed ranges
.venv\Scripts\uv sync                   # make the venv match the lock file
.venv\Scripts\uv sync --no-dev          # production: runtime dependencies only
```

Keep `uv` in the dev group: `uv sync` removes anything not in the lock file,
including uv itself.
