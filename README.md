# Portfolio Dashboard

See [PLAN.md](PLAN.md) for the full plan. Backend first: Django + DRF in `backend/`.

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
.venv\Scripts\python manage.py check
```

`backend/.env` is gitignored - every checkout needs its own.

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
.venv\Scripts\python manage.py test accounts # just the accounts app
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
