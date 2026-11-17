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
  user admin) — **not started**. Nothing from the backend build order is built yet.
- **What exists:** a stock Django 5.2 project (`backend/config`) with dependencies
  declared and locked. No apps, no models, no migrations, no database.
- **Blocking rule:** do **not** run `manage.py migrate` before the custom `accounts.User`
  from B1.1 exists. `AUTH_USER_MODEL` cannot be changed cleanly once migrations have run,
  and that mistake is exactly what forced the restart in v1.
- **Next action:** create the `accounts` app and the custom `User` / `Profile` models
  (PLAN.md § 1.3 B1.1), then the first migration.

### Machine / environment notes

| | |
|---|---|
| Repo path (this machine) | `C:\Users\engineer\Desktop\tracker` |
| Repo path in PLAN.md | `C:\Users\Josh\Desktop\portfolio-dashboard` — stale, do not treat as authoritative |
| Python | 3.12 (`backend/.python-version`) |
| Venv | `backend/.venv`, **not committed** — a fresh machine must bootstrap it (see README.md) |
| Package manager | uv, installed *inside* the venv, pinned in the dev group so `uv sync` cannot remove it |
| `.env` | not present on this machine and never committed; needed for `SECRET_KEY`, `DEBUG`, `FMP_API_KEY` once B1 lands |

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
