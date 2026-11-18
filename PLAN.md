# Portfolio Dashboard — Plan (v2: backend first)

## Context

The first version of this app grew too complex and was abandoned. This is a deliberate restart: a system where someone can view and manage holdings (not trade) across fully user-defined asset types (stocks, crypto, physical gold, collectibles, vehicles, private businesses), and see whether their allocation targets and themes are being met.

**Direction change in v2 of this plan:** the work is now **backend first**. Django is the product for now; Django admin is the working interface; the React app is kept as a thin skeleton and only catches up later. The plan is therefore split into two parts:

- **Part 1 — Backend (Django + DRF):** where all new work happens.
- **Part 2 — Frontend (React):** what exists, frozen, plus what it will need later.

Guardrails carried over from v1, still in force:

1. **No special "Dashboard" page type.** The only top-level page concept is `Page`, a generic container of widgets. Templates are just pages with `is_template=True`.
2. **Portfolio is the container above everything.** One retail user usually has one portfolio; an advisor may have many. Everything a user owns hangs off a `Portfolio`.
3. **Scope stays tight.** No brokerage linking, no trading, no advice. Manual entry, CSV import and price data only.
4. Money and quantity fields are `DecimalField`, never floats.

Stack: Django + DRF, SQLite in dev, React SPA (Vite). Project at `C:\Users\Josh\Desktop\portfolio-dashboard`. Python 3.12, Node 22.17.

---

# Part 1 — Backend

## 1.1 App layout and dependency rule

```
backend/
  config/       settings, urls
  accounts/     User, Profile, SecurityEvent, auth endpoints   (NEW – build first)
  holdings/     Portfolio, PortfolioAccess, Account, AssetClass, Asset, AssetField, Transaction, ValueSnapshot
  marketdata/   Security, Price, FxRate, FMP client   (NEW)
  targets/      AllocationNode (theme tree), Assignment, drift maths   (NEW)
  layouts/      Page, Widget, widget computation
```

Apps are split by **what the data means**, never by page type.

**Dependencies run one way only:**

```
accounts  ←  holdings  ←  targets  ←  layouts
marketdata ←  holdings
```

- `accounts` and `marketdata` import from nothing else in the project.
- `holdings` may import `accounts` and `marketdata`.
- `targets` may import `holdings`.
- `layouts` may import everything; nothing imports `layouts`.

Add a test that fails if these rules are broken (grep the import lines).

## 1.2 Can Django admin run all of this?

**Yes for now, no for real users.**

- **Use admin as the whole interface during the backend phase.** Every model is registered, with list filters, search, inlines (assets inside an account, transactions inside an asset, child nodes inside a theme) and admin actions (refresh prices, take snapshot, run import). This lets the data model be proven without writing any React.
- **Do not plan on admin being the product.** Admin assumes trusted staff. Limiting each user to their own rows means overriding `get_queryset`, `formfield_for_foreignkey` and permissions on every model, and the result is still a database editor, not a simple investing app. Customers get the API + frontend; admin stays your operator console.
- Practical rule: only `is_staff` users can log in to admin. Ordinary users never see it.

## 1.3 Step B1 — Users, profiles and account security (do this first)

Nothing else is built until this step is complete and tested. It has four parts: models, account endpoints, protections, and admin.

### B1.1 Models

**Custom user model from day one.** Changing `AUTH_USER_MODEL` after migrations exist is painful, and v1 already ran migrations against Django's default user. Since the dev database only holds seed data, the clean route is: delete `db.sqlite3` and the existing migration files, add `accounts`, set `AUTH_USER_MODEL = "accounts.User"`, re-run `makemigrations` / `migrate` / `seed_demo`.

`accounts` app:

- `User(AbstractBaseUser, PermissionsMixin)` with a custom `UserManager` (`create_user`, `create_superuser`):
  - `email` (unique, stored lower-cased, `USERNAME_FIELD = "email"`), no username field;
  - `is_active`, `is_staff`, `is_superuser`, `date_joined`, `last_login`;
  - `email_verified_at` (nullable), `password_changed_at`.
- `Profile`: `user` (OneToOne), `display_name`, `base_currency` (default `CAD`), `timezone` (default `America/Toronto`), `created_at`, `updated_at`. Created automatically by a `post_save` signal on `User`. (*A `role` field — `individual` | `advisor` — was built and then removed on 2026-11-17: the app is individual-only for now. Re-add it with the advisor work, B9.*)
- `holdings.Portfolio.owner` → FK to `settings.AUTH_USER_MODEL` (required, `PROTECT`). Add `Portfolio.base_currency`.
- `holdings.PortfolioAccess` (see 1.4) — the table is created in this step so every portfolio has an owner row from the start. *(Removed 2026-11-17 — deferred to sharing, B9.)*
- On sign-up, one default `Portfolio` is created for the user, and the starter template pages are duplicated into it.
- *As built:* the three bullets above landed in **B2**, not B1 — `accounts` may not import other project apps, so the sign-up receiver lives in `holdings`. Duplicating starter template pages waits for `layouts`.
- Templates stay unowned (`Page.portfolio = None`, `is_template = True`).

### B1.2 Account endpoints

All under `/api/auth/`. Session authentication (cookie) to start; token/JWT can be added later without model changes.

| Endpoint | Purpose | Notes |
|---|---|---|
| `GET csrf/` | Hand the SPA a CSRF cookie | Called once on load |
| `POST register/` | Create account | Email + password (+ display name). Runs password validators. Sends verification email. Same response whether or not the email already exists |
| `POST verify-email/` | Confirm email | Signed, single-use, time-limited token |
| `POST resend-verification/` | Send the email again | Throttled |
| `POST login/` | Start session | Generic error ("email or password is incorrect"). Rotates the session key on success |
| `POST logout/` | End session | |
| `POST logout-all/` | Log out everywhere | `keep_current: true` ends only the *other* sessions. No password needed (only removes access) |
| `GET/PATCH me/` | Read / update user + profile | Email is not changed here. Timezone must be a valid IANA zone |
| `GET options/` | Profile form choices | Currencies and timezones - so the frontend never hard-codes them. Public |
| `GET security-events/` | Own recent security activity | Last 50 `SecurityEvent`s for the caller, newest first (logins, failed attempts, password/email changes) |
| `POST password/change/` | Change password while logged in | Requires current password. Keeps this session, ends all others |
| `POST password/reset/` | Request reset email | Always returns 200 (no account enumeration) |
| `POST password/reset/confirm/` | Set new password from emailed link | Django's `PasswordResetTokenGenerator` (single-use, expires). Ends all sessions |
| `POST email/change/` | Change email | Requires current password; new address must be verified before it takes effect; notice sent to the old address |
| `POST deactivate/` | Close account | Requires current password; sets `is_active=False` (soft). Hard delete is an admin action |

Emails use Django's console email backend in development, a real provider later.

### B1.3 Protections

Passwords:

- Hashing: Argon2 first in `PASSWORD_HASHERS` (`argon2-cffi`), PBKDF2 kept as fallback.
- `AUTH_PASSWORD_VALIDATORS`: minimum length 12, common-password list, similarity to email/name, not entirely numeric.
- Passwords are never logged, never returned by any serializer, and never sent by email.
- Changing or resetting a password invalidates other sessions (`update_session_auth_hash` for the current one).

Sign-in abuse:

- DRF throttles with their own scopes: `login`, `register`, `password_reset`, `resend_verification` (for example 5/min per IP and 10/hour per account).
- Lockout after repeated failures by account + IP (`django-axes`), with a cool-off period and an admin unlock action.
- Login, reset and register responses do not reveal whether an email is registered.
- Tokens (verification, reset) are single-use and expire (`PASSWORD_RESET_TIMEOUT` about 1 hour).

Sessions and transport (production settings; relaxed only in `settings/dev.py`):

- `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE = "Lax"`.
- `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS = "DENY"`.
- CSRF protection stays on for every session-authenticated write. `CSRF_TRUSTED_ORIGINS` and `CORS_ALLOWED_ORIGINS` list the frontend origin only; `CORS_ALLOW_CREDENTIALS = True`; never `CORS_ALLOW_ALL_ORIGINS`.
- Session expiry set (for example 14 days sliding), and a "log out everywhere" action.

Configuration:

- `SECRET_KEY`, `FMP_API_KEY`, email credentials and `DEBUG` come from environment variables (`.env`, not committed). `DEBUG = False` and explicit `ALLOWED_HOSTS` outside development.
- Settings split into `base.py`, `dev.py`, `prod.py`. `manage.py check --deploy` must pass against `prod.py`.

Access rules:

- Default DRF permission is `IsAuthenticated`; only the auth endpoints above are public.
- Unverified users can log in but cannot be granted access to someone else's portfolio until verified.
- Inactive users cannot log in or use the API.

Audit:

- `accounts.SecurityEvent`: `user` (nullable), `event` (`register`, `login`, `login_failed`, `logout`, `password_changed`, `password_reset_requested`, `password_reset_done`, `email_changed`, `deactivated`, `locked`), `ip`, `user_agent`, `created_at`. Written by signals, read-only in admin.

Deliberately later: two-factor authentication (TOTP), social login, breached-password check.

### B1.4 Django admin for users

- `UserAdmin` built on `django.contrib.auth.admin.UserAdmin`, adapted for email login:
  - custom `UserCreationForm` / `UserChangeForm` (email + two password fields on add; hashed password shown read-only with the standard "change password" link on edit);
  - `list_display`: email, display name, is_active, is_staff, email verified, last login, date joined;
  - `list_filter`: is_active, is_staff, email verified; `search_fields`: email, display name; `ordering`: email;
  - `ProfileInline` (one-to-one, cannot be deleted);
  - read-only: last_login, date_joined, password_changed_at;
  - actions: deactivate (also ends the user's sessions), reactivate, mark email verified, send password-reset email, unlock (clear lockout), end all sessions. Deactivate / reactivate / end sessions write `SecurityEvent` rows.
- `SecurityEventAdmin`: read-only list, filter by event and date, search by email and IP. No add/change/delete.
- `PortfolioAdmin` shows the owner (and, once sharing exists, an inline of who has access).
- Only `is_staff` users can sign in to admin. Admin passwords are never set or shown in plain text; admins trigger a reset email instead.
- Outside development: admin served at a non-default path, and staff accounts are the first to get two-factor when it is added.
- `createsuperuser` works with email only.

### B1.5 Done when

- A user can register, verify, log in, change password, reset a forgotten password, change email, log out and deactivate — each covered by a test.
- Tests also prove: weak passwords rejected; wrong current password rejected; reset token cannot be reused or used after expiry; other sessions end on password change; repeated bad logins lock out; throttles return 429; responses do not reveal whether an email exists; inactive users are refused.
- Two users created in admin each get a profile and a default portfolio.
- `manage.py check --deploy` passes with production settings.
- `seed_demo --user <email>` fills one user's portfolio.

## 1.3a Tiers (structure built 2026-11-17; limits undecided)

There will be pricing tiers — **Free** and **Paid** to start, possibly a middle tier later. Undecided: how many tiers, what each costs, and what each unlocks.

Built now (structure only, so later decisions are small changes):

- `accounts.Subscription` — one per user, `tier` (`free` | `paid`), created at signup alongside the Profile; existing users backfilled to Free. Adding a tier = one more choice.
- Staff set tiers in admin (inline on the user, list column + filter, "Set tier" actions). **No payment provider yet**; when billing comes (Stripe or similar), its fields — customer/subscription ids, status, current period end — go on this same model, and a webhook sets `tier`.
- `GET me/` returns `tier`, read-only.
- `accounts/tiers.py` is the **only** place limits live: `TIER_LIMITS = {tier: {feature_key: limit}}` where a limit is a bool, an int cap, or `None` (unlimited); features call `limit(user, key)` / `allows(user, key)` and never compare tier names. A test asserts every tier defines the same keys. **Nothing is gated yet.**

Candidate gates to decide as each feature lands (not commitments): number of assets / accounts / asset types (B2.5), automatic price updates vs manual values (B3), number of themes (B4), length of value history (B6), CSV import (B7), sharing (B9). Each is one key in `TIER_LIMITS` plus one check in the feature.

Rule for downgrades (decide before the first gate ships): going Paid → Free should never delete data — over-limit items become read-only, not removed.

## 1.4 Step B2 — Portfolio ownership and scoping

**Ownership model (decided 2026-11-17).** Every portfolio has exactly one owner, and for now only the owner can see or change it.

**Now — individuals only:** every user owns **exactly one** portfolio, created at signup and living as long as the account. The API has no create or delete. Grouping inside it uses accounts (where held), asset types (what it is) and themes (what it's for) — never extra portfolios. The whole app is built out for this single-portfolio individual first.

**Future idea — advisors (explored 2026-11-17, built, then removed to keep scope on the individual; see LOG.md):** an advisor creates `Client` records (name, email, phone, notes), each with exactly one portfolio **owned by the advisor**; clients don't log in, or later log in purely to **view** (a viewer row). Client data belongs to the advisor. The advisor's own signup portfolio would be locked. Needs `Profile.role` back. Details in B9.

Scoping (written once, used everywhere):

- **One function decides access:** `holdings.access.accessible_portfolios(user)` — today simply "portfolios you own" (empty for anonymous or inactive users). Every endpoint over portfolios, and over anything inside one, builds its queryset from it; child models filter through `portfolio__in=accessible_portfolios(user)`. No view ever filters on `owner` itself.
- Objects outside the user's access return **404**, not 403 — they're simply not in the queryset.
- Writes validate that any referenced portfolio / account / asset class / node belongs to a portfolio the user can access.
- **Sharing later (B9) is a change inside that one function**, plus a `PortfolioAccess` table (portfolio, user, role `owner` | `manager` | `viewer`, status, granted_by, dates) and a role check for writes. That table was built in the first B2 pass and **removed 2026-11-17** — with one owner per portfolio and no sharing, it only duplicated `Portfolio.owner`.

**Tests that matter most:** user A cannot list, read, edit or duplicate into anything of user B; anonymous and inactive users see nothing.

**As built (B2):** `holdings` app with `Portfolio` (`owner`, `name`, `base_currency`, timestamps) and `holdings/access.py`.

- Signup creates the user's portfolio (`holdings/signals.py`, via `services.create_portfolio`), in their profile currency.
- `/api/portfolios/` — list / retrieve / PATCH (rename, base currency). No create or delete. Staff can still create/delete in admin.
- Admin: portfolio list; owner fixed after creation.
- Data migration backfilled a portfolio for users created before `holdings` existed.
- No DB unique constraint on `Portfolio.owner` — deliberately, since future advisors would own many.
- `v1`'s `summary_metrics` field was not carried over — it's a display setting that belongs with `layouts`.

## 1.5 Step B3 — Market data (`marketdata`, FMP)

Purpose: prices, names and FX for listed holdings, so values are not typed by hand. Manual assets (gold bars, a car, a private business) keep working with no security attached.

Models:

- `Security`: `symbol`, `exchange`, `name`, `currency`, `security_type` (stock / etf / crypto / fx / commodity), `provider_symbol`, `last_price`, `last_price_at`, `dividend_yield` (nullable), `is_active`. Unique on (`symbol`, `exchange`).
- `Price`: `security`, `date`, `close`. Unique on (`security`, `date`).
- `FxRate`: `base`, `quote`, `date`, `rate`. Unique on (`base`, `quote`, `date`).

Link: `Asset.security` nullable FK. `Asset.currency` added. Rule for value:

- security linked → value = quantity × latest price × FX to the portfolio's base currency;
- no security → the manually entered `current_value` is used.

FMP client (`marketdata/providers/fmp.py`):

- One small class behind a provider interface (`get_quote`, `get_history`, `get_fx`, `search`), so FMP can be swapped or supplemented later.
- API key from the environment (`FMP_API_KEY`), never in the repo.
- All calls go through one function with timeout, retry and a daily request counter.
- Prices are **stored**, and the app reads from the database. Nothing calls FMP during a page request.
- Check before building on it: FMP's current endpoint paths and plan limits, and whether your plan covers TSX-listed symbols and the metals/crypto quotes you want. Coverage and rate limits vary by plan.

Jobs (management commands first, scheduler later):

- `sync_prices` — latest quote for every active `Security` in use.
- `backfill_prices --symbol X --from YYYY-MM-DD`.
- `sync_fx` — rates for each currency pair in use.
- Admin action "Refresh price" on `Security`.

Run them by hand or with Windows Task Scheduler / cron. Add Celery only if this becomes a hosted product.

## 1.6 Step B4 — Targets and themes (`targets`) — the core feature

A tree of allocation nodes per portfolio, each with a target, and holdings assigned to leaves.

- `AllocationNode`: `portfolio`, `parent` (nullable self-FK), `name`, `target_percent` (of its parent), `color`, `sort_order`, `kind` (`category` | `theme` | `position`). Top level might be Investments / Gold / Silver / Bitcoin / Cash; under Investments the themes (Coal, Shipping…); under a theme, sub-themes or positions.
- `Assignment`: `node`, `asset`, `weight` (default 1.0). One asset may be split across nodes; weights for an asset must not exceed 1.
- Optional per-node `target_amount` for fixed-dollar goals (e.g. a down-payment fund).

Computation lives in `targets/drift.py` as pure functions, returning for each node: actual value, actual % (of parent and of portfolio), target %, target value, drift, and amount to add or trim. Plus:

- an **Unallocated** bucket at each level (target not handed to a child, and holdings not assigned to any node);
- a validation report (children's targets do not sum to 100%, asset over-assigned).

API: `/api/allocation-nodes/` (CRUD, reorder), `/api/assignments/`, `GET /api/portfolios/<id>/drift/` (the whole tree, computed).

Admin: `AllocationNode` with children and assignments inline; a read-only "Drift" admin view is a cheap way to see results before any frontend exists.

## 1.7 Step B5 — Transactions and income

- `Transaction`: `portfolio`, `account`, `asset` (nullable for pure cash movements), `type` (`buy`, `sell`, `dividend`, `interest`, `fee`, `deposit`, `withdrawal`, `split`, `adjustment`), `date`, `quantity`, `price`, `amount`, `currency`, `fx_rate`, `note`, `import_batch` (nullable).
- For assets **with** transactions, quantity and cost basis are derived (average cost) and cached on `Asset` by a `recalculate_position()` service. For assets **without** transactions, the manual fields remain the source of truth. This keeps simple manual tracking simple.
- Derived figures: realized gain, income received (by year, by asset, by account), projected annual income (yield × value).

## 1.8 Step B6 — Value history

- `ValueSnapshot`: `portfolio`, `date`, `total_value`, `investment_value`, `net_deposits`. Optional `AssetSnapshot` (asset, date, quantity, value) if per-holding history is wanted.
- `take_snapshots` command, run daily after `sync_prices`.
- Enables net-worth-over-time and a deposit-adjusted return (Modified Dietz to start).

## 1.9 Step B7 — CSV import

- `ImportBatch`: `portfolio`, `account`, `source` (`ibkr`, `wealthsimple`, `generic`), `file`, `status`, `summary` (JSON), `created_at`.
- Flow: upload → parse with a per-source parser → match rows to assets by `identifier` → produce a diff (new / changed / missing) → apply on confirm.
- Two kinds: **positions** (snapshot of holdings) and **transactions** (activity).
- Generic columns: `identifier` (required), `name`, `quantity` (required), `current_value`, `cost_basis`, `currency`.
- First version runs from admin (upload on the `ImportBatch` form, "Apply" action).

## 1.10 Step B9 — Sharing and manager accounts (later)

Built only after individuals are using the product. Adds the `PortfolioAccess` table (see B2's scoping notes) and extends `holdings.access.accessible_portfolios` to include shared portfolios, plus a role check for writes.

- `PortfolioInvitation`: `portfolio`, `email`, `role`, `token` (signed, single-use, expires), `invited_by`, `status` (`pending` | `accepted` | `declined` | `expired` | `cancelled`), dates.
- **Advisors and clients:** bring back `Profile.role` (`individual` | `advisor`, staff-set). An advisor creates `Client` records (name, email, phone, notes), each with exactly one portfolio **owned by the advisor**; the advisor's own signup portfolio is locked; client data belongs to the advisor. (This was built once on 2026-11-17 — `holdings.Client`, `Portfolio.client` one-to-one, `/api/clients/`, `access.usable_portfolios` hiding the locked portfolio — then removed to focus on individuals; LOG.md has the design notes.)
- **Client can log in to view:** the advisor invites the client's email as a **viewer** of that portfolio, and the accepted login is linked to the `Client` record. The client accepts — signing up through the invitation if they have no account — and from then on logs in to see it. **No ownership transfer, no "claim" step.**
- An invited client who signs up through the invitation should **not** also get an empty default portfolio (the B2 signup receiver must skip invite signups). Decide then whether such a client may later start their own personal portfolio.
- **Owner invites a helper:** any owner (individual or advisor) can also invite someone as `viewer` or `manager` — e.g. a spouse, an accountant, an assistant at the advisor's practice.
- Every invitation needs explicit acceptance by a verified user. Owners see a list of who has access and can revoke in one action. Viewers/managers can leave a portfolio.
- Advisor view: `GET /api/clients/` — every client portfolio the advisor owns or manages, with summary figures and who has viewer access. Templates, pages and theme trees can be duplicated across those portfolios.
- Firms grouping several advisors: see **B10 — Organizations** below (replaces the earlier one-line `Practice` idea).
- Audit: `PortfolioAuditLog` (portfolio, user, action, object, before/after, timestamp) for changes made by anyone other than the owner, visible to the owner.
- Before real client data is involved: privacy review (consent wording, data export, deletion), and keep the product positioned as tracking and reporting, not a manager's regulatory system of record.

## 1.11 Step B10 — Organizations (later, after B9)

An organization is a firm (advisory practice, family office) that groups advisors. Its **owner can see every advisor in the org and every client portfolio those advisors own.** Built on top of B9's advisor model, not instead of it: advisors own their clients' portfolios, clients are viewers, and access still flows through `holdings/access.py`.

New app `organizations`, slotted into the dependency rule as `accounts ← organizations ← holdings` (update the import-rule test when it lands).

- `Organization`: `name`, `owner` (FK user, `PROTECT`), `created_at`.
- `OrganizationMembership`: `organization`, `user`, `role` (`owner` | `admin` | `advisor`), `status` (`invited` | `active` | `removed`), `invited_by`, dates. Unique on (`organization`, `user`); exactly one active `owner`, kept in step with `Organization.owner`. Joining requires explicit acceptance by a verified user, like B9 invitations.
- `Portfolio.organization` (nullable FK): set on an advisor's client portfolio that belongs to the firm's book. The client sees the org's name on their invitation.

| Org role | See advisors | See org clients | Edit client portfolios | Manage members |
|---|---|---|---|---|
| Owner | all | all, read-only | only portfolios they own or manage | yes; transfer ownership; close org |
| Admin | all | all, read-only | only portfolios they own or manage | invite / remove advisors |
| Advisor | — | their own clients | yes (they own them) | no |

Rules:

- **Scoping:** `accessible_portfolios()` (B2) gains one more source: portfolios whose `organization` is one where the user is an active owner/admin. Org-derived access is **read-only**; writes still need a direct `owner`/`manager` row.
- **Advisor leaves:** their org-tagged client portfolios are **transferred** to another advisor in the org (owner/admin action — the one place ownership changes hands), so the client keeps service and keeps their viewer row. Untagged portfolios (the advisor's personal book) leave with the advisor.
- **Client leaves:** the owning advisor (or an org admin) revokes the client's viewer row. The data stays with the advisor/firm, per B9's ownership model.
- **Audit:** org-level views of a client portfolio are recorded in `PortfolioAuditLog`.
- **API:** `GET /api/orgs/<id>/advisors/` (with client counts and summary figures), `GET /api/orgs/<id>/clients/?advisor=<id>`, membership invite / accept / remove, and portfolio transfer between org advisors.
- **Tests that matter most:** an org owner sees exactly their org's tagged portfolios, never another org's or an advisor's personal book; org access cannot write; transferring a departing advisor's portfolios keeps data and client viewer rows intact.

Open questions (decide when B10 starts, not now): can an advisor belong to more than one org (start with one); should owners be able to edit, or only view (start view-only); per-seat billing (out of scope).

## 1.12 Holdings and layouts design (from v1 — NOT built in this repo)

> **Correction (2026-11-17):** none of the code described in this section exists. This repo was started fresh; the only app built is `accounts`. Treat what follows as the *design* for `holdings`/`layouts`, to be built outward from users/profiles, not as code to keep.

`holdings`:

- `Portfolio`: name, created_at, `summary_metrics` (ordered list of 1–5 keys: `net_worth`, `investments`, `personal`, `cost_basis`, `unrealized_gain`, `total_return`, `holdings`, `type:<id>`).
- `Account`: portfolio, name, kind (brokerage / retirement / managed / bank / crypto / physical / other), institution, sort_order. `Asset.account` is nullable (`SET_NULL`): deleting an account keeps its holdings.
- `AssetClass`: portfolio, name, color, icon, sort_order, `is_investment` (default true).
- `Asset`: asset_class, account, name, identifier, quantity, current_value, cost_basis (nullable), custom_fields (JSON), `investment_override` (`''` | `investment` | `personal`).
- `AssetField`: asset_class, name, key (fixed at creation), options[], sort_order. Values live in `Asset.custom_fields[key]`. `rename_option` / `remove_option` rewrite values on every asset.
- **Type vs account:** a type is what something is; an account is where it is held.
- Gain/loss only counts assets that have a cost basis.

`layouts`:

- `Page`: portfolio (nullable), name, slug, sort_order, is_template.
- `Widget`: page, widget_type (`metric_tile`, `table`, `allocation_breakdown`, `chart`, `note`), x/y/w/h, title, config (JSON).
- `layouts/widgets.py`: pure functions `(queryset, config) -> value`, one per widget type. Supports `asset_class_filter` (ids or names), `field_filter`, `holdings_filter` (`investments` | `personal`), `group_by` (`asset_class` | `account` | `field:<key>`), table `sort_by` / `sort_dir` / `limit`, metric `variant` and `context`.
- Colors: validated colorblind-safe palette (`FALLBACK_COLORS`), keyed to the class, more than 8 slices fold into "Other".

API (existing): `/api/portfolios/`, `/api/accounts/`, `/api/asset-classes/` (+ `reorder/`), `/api/assets/`, `/api/pages/` (+ `<id>/data/`, `<id>/duplicate/`, `<id>/layout/`), `/api/widgets/`, `/api/widget-types/`.

**Follow-ups to existing code once B1–B6 land:**

- Add `group_by: "node"` and a `drift` widget type in `layouts` that read from `targets`.
- Widget values use the security-priced value when an asset has a security.
- `seed_demo` takes `--user`, and seeds a small theme tree, a few securities and transactions.

## 1.13 Backend build order

Each step is runnable and testable on its own, entirely through admin and tests.

| Step | What | Done when |
|---|---|---|
| **B1** | `accounts`: custom User, Profile, register / login / password change and reset / email change / deactivate, protections, user admin | All account flows and protection tests pass; `check --deploy` clean |
| **B1a** | Tiers: `Subscription` (Free / Paid), staff-set, `tiers.py` limit table — structure only (§1.3a) | Built; limits filled in per feature |
| **B2** | One `Portfolio` per user (created at signup); owner-only scoping through `holdings/access.py` on every endpoint | Cross-user tests pass |
| **B2.5** | What's inside a portfolio: `Account`, `AssetClass`, `AssetField`, `Asset` (design in §1.12), each scoped through `holdings/access.accessible_portfolios` | CRUD + admin for each; cross-user tests extended to every model; nothing can reference another portfolio's account/class |
| **B3** | `marketdata` + FMP client + `sync_prices` | A linked asset's value updates from a stored price |
| **B4** | `targets`: node tree, assignments, drift | `/drift/` returns correct numbers for a fixture tree |
| **B5** | Transactions, derived positions, income | Buy/sell/dividend fixtures give expected quantity, cost, income |
| **B6** | Snapshots + return | Daily snapshot rows; Modified Dietz test passes |
| **B7** | CSV import (IBKR first) | An IBKR positions file imports with a correct diff |
| **B8** | Hardening | Import-rule test, API docs (drf-spectacular) |
| **B9** | Sharing + manager accounts (later) | Invite, accept, revoke and claim flows tested; manager client list |
| **B10** | Organizations (later, after B9) | Org owner sees all advisors and their org clients, read-only; advisor departure reassigns clients; cross-org isolation tests pass |

## 1.14 Backend verification

- `manage.py test` for: widget functions, drift maths, position recalculation, FX conversion, ownership scoping, import diffing.
- FMP client tested against recorded responses (no live calls in tests).
- Nothing in `holdings/` imports `targets/` or `layouts/`; nothing in `accounts/` or `marketdata/` imports project apps.

---

# Part 2 — Frontend

**Status: frozen as a skeleton.** No new frontend features until the backend steps above are done. Only changes needed to keep it working against the new backend are allowed.

## 2.1 v1 frontend design (NOT built in this repo)

> **Correction (2026-11-17):** none of this exists. The only frontend is the unstyled `frontend/` auth harness (see LOG.md). Kept as the design target for later.

- Vite + React, `react-grid-layout` for the widget grid, `recharts` for charts, Inter bundled locally, `lucide-react` icons.
- Page switcher listing the portfolio's pages uniformly. "New Page": blank or copy from a template.
- `PageView`: fetches `/api/pages/<id>/data/`, maps `widget_type` → component (`MetricTile`, `DataTable`, `AllocationBreakdown`, `AllocationChart`, `Note`).
- Edit mode: drag/resize, batch save to `/layout/`, "Add widget" modal driven by `/api/widget-types/`.
- **Assets screen** (not a `Page`): one list, two views — by type (`#/assets`) or by account (`#/accounts`); filter chips; each group is a card with Add and a ⋯ menu; short rows (monogram, name, one detail line, value, gain/loss, of total); sortable.
- Add/edit asset form with account and field inputs, inline "+ New account…", live gain/loss preview.
- Field management dialog per type; widget config "Break down by" and "Only include".
- Investments vs personal toggles; customizable summary bar (1–5 metrics).
- Visual design "Keelstone" (placeholder brand): tokens at the top of `styles.css`; every text color clears 4.5:1 contrast; brand color for interface chrome only, charts use the validated palette; 12-column grid, 56px rows, 16px gaps.

## 2.2 Minimum changes forced by the backend work

| Backend step | Frontend change (smallest possible) |
|---|---|
| B1 | Register, verify-email, login, forgot-password and reset-password screens; change password / email in a basic settings page; send session cookie + CSRF token; log out |
| B2 | Load the portfolios the user has access to instead of the hard-coded one; hide edit controls for viewers |
| B3 | Show "priced automatically" vs "manual value" on a holding; optional symbol search when adding a listed asset |
| B4 | None required (drift can be viewed in admin). Later: the Targets screen below |

## 2.3 Later frontend work (not started, in priority order)

1. **Targets screen** — one fixed, opinionated screen (not a widget page): the theme tree with target, actual, drift and amount to add or trim, an Unallocated row, and a form to assign holdings to themes. This is the product's main screen.
2. **Transactions and income** — activity list per holding and account; income by year.
3. **History** — net worth over time, return vs deposits.
4. **CSV import UI** — upload, review diff, apply (the disabled "Import CSV · Soon" item).
5. **Profile/settings** — display name, base currency, timezone.
6. Known gaps: responsive shell (collapsible sidebar on phones), dark mode.
7. Sharing and advisor features (backend step B9): "Who has access" panel with invite and revoke, accept-invitation screen, advisor's client list with a client switcher, a read-only client view, apply a template to many portfolios — only after individuals are using it.
8. Organization views (backend step B10): advisor list, clients grouped by advisor, member invite / remove / reassign — only after B9's manager features are in use.

**Complexity guardrail:** the widget grid is kept but not extended. New capability arrives as fixed screens, not as more widget types and options.
