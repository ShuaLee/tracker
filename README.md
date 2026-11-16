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
.venv\Scripts\python manage.py check
```

Do not run `migrate` until the custom user model from step B1 exists (see PLAN.md, B1.1).

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
