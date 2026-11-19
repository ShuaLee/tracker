# Personal Wealth App — Plan v3.1

## 1. What we are building

A personal asset and portfolio manager for **individuals**, built to compete with Kubera and Snowball Analytics.

A person signs up, records everything they own (stocks, ETFs, bonds, crypto, real estate, physical gold, watches, cards — anything), organises it with their own tags, sets their own targets, and builds their own summary **sheets** out of **widgets**.

**What sets it apart**

1. **Sheets** — users build their own summary pages from widgets: a main dashboard, a "Dashboard v2", a non-investment sheet, a sheet per theme. Nobody else in this space lets people lay out their own views like a spreadsheet.
2. **Targets** — their own allocation goals, nested (net worth plan → investment themes), with drift and how much to add or trim.
3. **Tags** — their own way of classifying anything they hold.

**In scope**

- One kind of user: an individual. No advisors, clients or sharing.
- Free tier plus one or two paid tiers.
- Holdings of any kind, standard or user-defined.
- **Positions only**: each holding records quantity, average cost and current price. No buy/sell/dividend history.
- **CSV import** of positions first; live account sync later.
- Live prices from FMP (after the core works).

**Out of scope (for now)**

- Advisors, clients, sharing.
- Transaction history, realized gains, time-weighted returns.
- Trading or giving advice.
- User-designed widget types (users configure our widgets; they don't invent new ones).

**Ground rules**

- Build step by step; each step is usable and tested before the next starts.
- Backend first (Django + DRF); Django admin is the working interface until the frontend step.
- Money and quantities are `DecimalField`, never floats.
- **Complexity guardrail for sheets:** a small set of well-made widgets, each with a short config. New capability comes from adding a widget type, never from adding options to every widget.

## 2. Key decisions

### 2.1 One portfolio per user — yes, but invisible

Every user gets exactly one `Portfolio`, created automatically at sign-up. Everything they own hangs off the portfolio, not the user.

- **Why:** almost free now, and later features become additive: export or delete as one unit, a second portfolio as a paid perk, a "what-if" portfolio.
- **Rule:** the UI never mentions portfolios until a feature needs more than one.

### 2.2 Holdings: positions with average cost

Every holding works the same way, whether it's COAL or a watch:

| Field | Meaning |
|---|---|
| `quantity` | Units held (1 for a house or a watch) |
| `avg_cost` | Average purchase price per unit (optional) |
| `current_price` | Price per unit: from the instrument when priced automatically, otherwise typed in by the user |
| *value* | `quantity × current_price` (calculated) |
| *cost basis* | `quantity × avg_cost` (calculated) |
| *unrealized gain* | value − cost basis, only when `avg_cost` is set |

- **Instrument** — a market-traded thing shared by all users (`COAL`, `AAPL`, `BTC`), priced from FMP later. A holding may point to one.
- Holdings without an instrument (house, gold coin, private business) use a manual `current_price` and a `price_updated_at` date so the user can see how stale it is.
- Each holding has a `currency`; totals convert to the user's base currency.

**What positions-only means:** we can show value, cost, unrealized gain and projected income, but not realized gains or true return over time. Return over time comes from daily snapshots (2.8) instead.

### 2.3 Asset types and custom fields

- **Asset type** = what kind of thing it is. We ship standard types (Stocks & ETFs, Bonds, Cash, Crypto, Precious metals, Real estate, Vehicles, Private investment). Users can create their own (Watches, Trading cards, Jewellery).
- Each type can carry **custom fields** (Watches → Brand, Reference, Condition).
- A type is **investment** or **personal** by default; a holding can override it. Net worth includes both; investment figures exclude personal.

### 2.4 Accounts

- **Account** = where a holding is held: "IBKR TFSA", "Tangerine savings", "Home safe".
- Optional on a holding. CSV imports go into an account.

### 2.5 Tags

- **Tag group** (user-defined): Sector, Theme, Region, Purpose…
- **Tag** inside a group, optionally nested: Energy → Coal → Producers. Selecting a parent includes its children.
- One tag per group per holding, so each group adds to 100%. Splitting a holding across tags is a possible later addition.

### 2.6 Targets

A **target plan** has a **base** and **lines**.

- **Base**: net worth, investments, or the value of a line in another plan (how plans nest).
- **Line**: name, goal, and what counts toward it.
  - Goal = **percentage** of the base, **fixed amount**, or **remainder**.
  - What counts = a tag (recommended), an asset type, or specific holdings.
- Fixed amounts are taken first, then percentages; the remainder line gets the rest.
- Every plan shows **Unassigned**: holdings in the base that no line claims.
- Each line shows actual value and %, target value and %, drift, and amount to add or trim.
- "Add a holding under a theme" in the UI applies that line's tag.

Example:

```
Plan "Net worth"            base = net worth
  Physical gold    10%      tag Asset class = Gold
  Silver          2.5%      tag Asset class = Silver
  Bitcoin         2.5%      holding BTC
  Home savings  $40,000     tag Purpose = Home savings
  Investments   remainder   tag Asset class = Investments

Plan "Investment themes"    base = line "Investments"
  Natural gas exploration 10%   tag Theme = Nat gas E&P
  Oil production          10%   tag Theme = Oil producers
  AI                      10%   tag Theme = AI
  Tankers                 10%   tag Theme = Tankers
  (Unassigned shows the other 60%)
```

### 2.7 Sheets and widgets (core feature)

- **Sheet** — a named page. Everyone starts with "Dashboard"; it is not special, just the first sheet. Sheets can nest under other sheets and can be duplicated ("Dashboard v2").
- **Sheet scope** — optional selection every widget on the sheet inherits ("only holdings tagged Personal"). This is how a sheet is linked to certain assets.
- **Widget** — type, title, position on a grid, config. Widgets only read data; they never store holdings or values of their own.
- **Starter templates** — a few ready-made sheets (Net worth, Investments, Income) the user can add with one click, built from the same widgets.

**Selection** — the building block every widget uses: include holdings by asset type, account, tag or holding; exclude the same way.

First widget types:

| Widget | Shows | Example config |
|---|---|---|
| Value | One number from a formula of selections | "Net worth" = all; "Investable" = investments − tag Home savings |
| Holdings list | Table of holdings in a selection | Columns, sort, top N |
| Breakdown | Pie/bar grouped by asset type, account or a tag group | "% by Sector" within Investments |
| Target progress | A plan's lines with drift and $ to add/trim | Plan "Investment themes" |
| History | Value of a selection over time (from snapshots) | Net worth, last 12 months |
| Income | Projected annual/monthly income from yields | Investments, by holding |
| Note | Free text | |

### 2.8 Value history (snapshots) — early

- A daily `Snapshot` of each portfolio: net worth, investments, personal, cost basis; plus `HoldingSnapshot` (holding, date, quantity, price, value).
- Taken by a scheduled command and after each CSV import.
- Built early because history cannot be recreated later, especially for manually priced items.
- Powers the History widget and "change since last month" figures.

### 2.9 CSV import (before any live sync)

- User picks an account, uploads a positions CSV, chooses a format: **IBKR Open Positions**, **generic**, more later.
- Generic columns: `symbol` or `name` (required), `quantity` (required), `avg_cost`, `current_price`, `currency`, `asset_type`.
- Match rows to existing holdings in that account by symbol (or name) → show a review: **new / changed / missing** → apply on confirm. Missing holdings can be removed or kept.
- Tags and targets survive re-imports, because matched holdings are updated in place.
- `ImportBatch` keeps the file, format, summary and date, so a bad import can be inspected.
- Live sync (IBKR Flex, aggregators) is a later step built on the same review-and-apply flow.

### 2.10 Income without transactions

- Projected income = value × dividend/interest yield.
- Yield comes from FMP for priced instruments; users can type a yield for anything else (savings account rate, bond coupon).
- Shows annual and monthly figures and yield on cost. Actual received dividends are out of scope with positions-only.

### 2.11 Tiers

- `Plan` (Free, Plus, Pro) with **entitlements**: limits and feature flags (max holdings, max sheets, max widgets per sheet, live prices, history length, CSV import formats, sync).
- `Subscription` on each user; everyone starts on Free. One helper, `entitlements(user)`, checked wherever a limit applies.
- Billing (Stripe) comes last; until then plans are set in admin.
- Working idea: Free = manual holdings, CSV import, a few sheets, short history. Paid = live prices, unlimited sheets, full history, income, later sync.

### 2.12 Market data licensing — check before launch

Showing FMP prices to paying users is redistribution. Personal FMP plans may not allow it; a commercial licence may be needed. Confirm the terms before charging anyone.

## 3. Data model (summary)

| App | Model | Key fields |
|---|---|---|
| `users` | `User` | email (login), is_active, is_staff, date_joined |
| | `Profile` | user, display_name, base_currency (CAD), timezone |
| | `Plan`, `Subscription` | entitlements (JSON); user, plan, status, renews_at |
| `portfolios` | `Portfolio` | owner (one per user), name, base_currency |
| | `Account` | portfolio, name, kind, institution |
| | `ExchangeRate` | portfolio, from_currency, to_currency, rate — manual rates until `marketdata.FxRate` (step 9) |
| `assets` | `AssetType` | portfolio (null = standard), key (standard types), name, icon, is_investment, is_priced |
| | `AssetField` | portfolio, asset_type, name, key, field_type, options — `portfolio` so a user's fields on a *standard* type stay private |
| | `Instrument` | symbol, exchange, name, currency, kind, last_price, last_price_at, yield (global) — **step 9** |
| | `Holding` | portfolio, asset_type, account, instrument (nullable, step 9), name, symbol, quantity, avg_cost, current_price, price_updated_at, currency, yield_override (step 9), custom_fields (JSON), investment_override, notes |
| `tags` | `TagGroup` | portfolio, name, sort_order |
| | `Tag` | group, parent (nullable), name, color |
| | `HoldingTag` | holding, tag (one per group per holding) |
| `targets` | `TargetPlan` | portfolio, name, base_kind (net_worth / investments / line), base_line |
| | `TargetLine` | plan, name, goal_kind (percent / amount / remainder), goal_value, match_kind (tag / asset_type / holdings), match fields, sort_order |
| `history` | `Snapshot`, `HoldingSnapshot` | portfolio, date, totals; holding, date, qty, price, value |
| `imports` | `ImportBatch` | portfolio, account, format, file, status, summary (JSON), created_at |
| `sheets` | `Sheet` | portfolio, parent (nullable), name, scope (selection JSON), sort_order, is_template |
| | `Widget` | sheet, widget_type, title, x, y, w, h, config (JSON) |
| `marketdata` (later) | `Price`, `FxRate` | instrument/date/close; base/quote/date/rate |

The user app is `users`, not `accounts`, so it isn't confused with `portfolios.Account` (where a holding is held).

**Dependency direction:** `users` ← `portfolios` ← `assets` ← `tags` ← `targets` ← `sheets`. `history` and `imports` sit beside `assets`; `marketdata` is used by `assets`. Nothing imports `sheets`.

**Calculation layer** (plain functions, most tests):

- `valuation.py` — value, cost and gain of a holding, in base currency;
- `selection.py` — resolve a selection to holdings and sum them;
- `targets/compute.py` — plan results;
- `sheets/widgets.py` — one function per widget type.

## 4. Build steps

Admin is the UI until step 10.

| # | Step | Done when |
|---|---|---|
| 1 | **Project + users.** Django project, email login, profile, register / login / logout / password change and reset, auto-created portfolio, Free subscription, user admin. Protections: Argon2, password rules, login throttling and lockout, single-use expiring tokens, secure cookies, secrets in `.env`. | Sign-up creates user + profile + portfolio + Free plan; all auth flows tested; `check --deploy` clean |
| 2 | **Asset types, accounts, holdings.** Standard types seeded; custom types and fields; quantity, avg cost, current price; investment vs personal; base-currency totals (manual FX rate for now). | Your own holdings entered in admin; net worth, investments, cost and gain correct in tests |
| 3 | **CSV import.** IBKR Open Positions + generic format; review new / changed / missing; apply. | Your two IBKR files import into TFSA and FHSA accounts; re-import updates in place |
| 4 | **Tags.** Tag groups, nested tags, one per group per holding. | Holdings tagged in admin; value-by-tag tested |
| 5 | **Selections.** Include/exclude by type, account, tag, holding; formula of selections. | "Net worth minus Personal", "Coal % of investments" tested |
| 6 | **Targets.** Plans, lines, nested bases, unassigned, drift. | The two-plan example computes correctly |
| 7 | **Snapshots.** Daily snapshot command; snapshot after import. | Snapshot rows created; value-over-time function tested |
| 8 | **Sheets + widgets API.** Sheet CRUD, nesting, duplicate, scope, widget types, one endpoint returning a sheet with computed widgets, starter templates, default Dashboard per user. | Dashboard JSON returns net worth, sector breakdown, target progress, history |
| 9 | **Market data.** Instruments, FMP client, stored prices and yields, FX rates, `sync_prices`. Income widget. | A COAL holding revalues and shows projected income |
| 10 | **Frontend.** Login, holdings, import, tags, targets, sheets with drag-and-drop widgets. | Usable end to end in a browser |
| 11 | **Tiers enforced + billing.** Limits checked; Stripe checkout. | Free user hits limits; upgrade unlocks them |
| 12 | **Live sync** (later). IBKR Flex, then an aggregator; reuses the import review flow. Two-factor login before storing broker credentials. | An IBKR account syncs positions on a schedule |

## 5. Open questions

1. Can a holding be split across two themes, or always one tag per group? (Plan: one, splits later.)
2. Position-level targets inside a theme (COAL = 40% of Coal) — now or later?
3. Free vs paid split — needed by step 11.
4. Default base currency CAD, user-selectable — confirm.
