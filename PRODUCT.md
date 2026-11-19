# Product Brief — Personal Wealth App

> Read this before writing any code. It explains what the app is, who it is for and why it exists. `PLAN.md` explains how and in what order to build it. If the two ever disagree, this file describes the intent and `PLAN.md` should be corrected.

## Mission

**Give everyday investors the tools of a wealth manager, so they can manage everything they own, their way.**

A wealth manager knows what a client owns, what the client is aiming for, and how far off they are. This app gives an individual the same picture for their own money: every asset in one place, organised the way *they* think about it, measured against goals *they* set.

## The problem

People who manage their own money end up in one of three places:

- **Brokerage apps** show one account at a time and only what that broker holds. Gold in a safe, a house, a private stake or a watch collection don't exist there.
- **Net-worth trackers** (Kubera and similar) list everything but don't help you *manage* it: no allocation goals, no "am I on target?".
- **Spreadsheets** do whatever you want, but they break, need constant manual updating, and get harder to trust as they grow.

Thoughtful investors — especially ones who invest by theme ("10% in tanker stocks, 10% in oil producers") and hold real assets alongside stocks — have no tool that fits how they actually think.

## Who it is for

**Individuals managing their own wealth.** Typically someone who:

- holds many positions across several accounts and asset types;
- owns things a broker doesn't track (physical gold and silver, crypto, real estate, collectibles, a small business);
- has a plan for their money ("7.5% of net worth in gold, $40,000 kept for a house, the rest invested across my themes") and wants to see whether they are sticking to it.

There is only one kind of user. No advisors, no clients, no shared accounts.

## What it does

### 1. Holds everything you own

Anything can be a holding: a stock, an ETF, a bond, a crypto coin, a house, a gold bar, a watch. Each holding has a quantity, an average purchase price and a current price, which give its value, its cost and its gain. Listed securities get prices automatically; everything else the user prices by hand.

Users can invent their own asset types (Watches, Trading cards) with their own fields (Brand, Condition). Holdings sit in accounts that say where they are held (IBKR TFSA, a bank, a home safe). Some holdings count as investments; others, like a car you drive, count toward net worth only.

The app tracks **positions, not transactions**: it knows what you hold now and what you paid on average, not every trade you made.

### 2. Organises it your way — tags

Users create their own classifications: a "Sector" group with Energy → Coal → Producers, a "Theme" group with Tankers and AI, a "Purpose" group with Home savings. Every chart, total and target can then be cut by these tags. The app never forces its own categories on anyone.

### 3. Measures it against your goals — targets

Users set allocation goals as percentages, fixed amounts or "whatever is left", and goals can nest:

> Net worth: 10% gold, 2.5% silver, 2.5% Bitcoin, $40,000 home savings, the rest is investments.
> Investments: 10% natural gas explorers, 10% oil producers, 10% AI, 10% tankers.

Holdings count toward a goal through their tags. For every goal the app shows where the user is, where they want to be, the drift, and how much to add or trim, plus anything not assigned to any goal.

This is the heart of the product: **turning a personal investment plan into something you can see and act on.**

### 4. Shows it however you like — sheets

A **sheet** is a page the user builds from **widgets**: a headline value, a list of holdings, a pie chart by sector, a target progress table, net worth over time, projected income, a note. Everyone starts with a Dashboard; they can add more sheets, nest them, duplicate them, or limit a sheet to certain holdings (a "Non-investment" sheet, a sheet per theme).

Widgets are designed by us; the user chooses which ones to use and what each one looks at. A value widget might be "Net worth" (everything) or "Investable cash" (cash minus home savings).

**Sheets are what set this app apart.** Others give everyone the same fixed screens. Here, each person lays out the views that matter to them, with the flexibility of a spreadsheet but none of its fragility.

### 5. Keeps itself up to date

- **CSV import** of brokerage positions (IBKR first), with a review of what's new, changed or gone before anything is applied.
- **Live prices** for listed securities (via FMP).
- **Daily snapshots**, so net worth and every total can be shown over time.
- **Projected income** from dividend and interest yields.
- Later: automatic account sync.

### 6. Free to start, paid to grow

A free tier is genuinely useful on its own (manual holdings, CSV import, tags, targets, a few sheets). One or two paid tiers unlock more: live prices, unlimited sheets, full history, income, sync.

## What it is not

- Not a broker: it never trades or moves money.
- Not an advisor: it shows the user their own plan and position; it never recommends what to buy.
- Not for advisors, teams or households (for now).
- Not an accounting ledger: no transaction history, tax lots or realized gains.

## Product principles

1. **The user's plan, not ours.** Tags, targets and sheets are defined by the user. Avoid baked-in categories and opinions.
2. **Simple by default, powerful when needed.** A new user should see a useful dashboard within minutes. Customisation is there when they want it, never required.
3. **Small, well-made building blocks.** Few widget types, each with a short config. Add a new widget rather than piling options onto existing ones. An earlier version of this app collapsed under its own complexity; don't repeat that.
4. **Numbers you can trust.** Every figure should be explainable: where a price came from, when it was updated, which holdings a total includes. Money is never stored as a float.
5. **One mechanism per idea.** Tags are the only way to classify; targets use tags; widgets use the same selection rules everywhere.
6. **Private by design.** This is someone's entire financial picture. Each user sees only their own data, and security is treated as a feature.

## How the pieces fit

```
User ── Profile, Subscription (Free / paid)
 └─ Portfolio (one per user, never shown in the UI; future-proofing)
     ├─ Accounts          where things are held
     ├─ Asset types       what things are (standard + user-made, with custom fields)
     ├─ Holdings          what is owned: quantity, avg cost, current price
     │    └─ Tags         user-made classifications (groups, nested)
     ├─ Target plans      goals built on tags (%, fixed $, remainder; nestable)
     ├─ Snapshots         daily history of values
     └─ Sheets            user-built pages
          └─ Widgets      our building blocks, configured by the user
```

Data flows one way: holdings → tags → targets → sheets. Sheets and widgets only read and calculate; they never own data.

## How to work on it

- **Build in the order in `PLAN.md`, one step at a time.** Finish, test and confirm each step before starting the next. Don't build ahead.
- **Backend first.** Django + Django REST Framework. Django admin is the interface until the frontend step.
- **Keep calculations in plain, tested functions** (valuation, selections, targets, widgets), not in views or serializers.
- **Default to the simplest version** that meets the step. When something is unclear, ask rather than guess, and prefer leaving a feature out over half-building it.
- **Don't add scope** that isn't in `PLAN.md` (advisors, transactions, sharing, trading) without it being agreed first.
