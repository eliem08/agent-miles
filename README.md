<!-- sell-kit:start -->
# Agent Miles

[![CI](https://github.com/eliem08/agent-miles/actions/workflows/ci.yml/badge.svg)](https://github.com/eliem08/agent-miles/actions/workflows/ci.yml)

> **A loyalty program built for AI agents that shop.**

**Who it's for:** Merchants who want agent shoppers to choose them, and agent platforms optimising for users.

**The problem:** Agents compare prices instantly, so merchants need loyalty value that agents can read and factor in.

**What you get:** Point lots with expiry, tiers, fraud and velocity limits, a machine-readable offer feed and an effective-price optimiser for agents.

## Quickstart

Customers receive a release archive with the wheel and the examples. Python 3.10+ and no other dependencies.

```bash
pip install agent_miles-0.1.0-py3-none-any.whl
agent-miles demo
agent-miles feed
```

## Web app and API

Every command is also a JSON API endpoint and a browser form, served by the built-in web app.

```bash
agent-miles-web --port 8000          # then open http://127.0.0.1:8000
agent-miles-web keys create --label "first customer"   # prints an API key (stored hashed)
docker build -t agent-miles . && docker run -p 8000:8000 -e API_KEYS=sk_... -v agent-miles-data:/data agent-miles
```

Every API call needs `Authorization: Bearer <key>` once any key exists; a server on a public address refuses to start without one. Calls are rate-limited per key (60/min, `--rate`) and metered: `agent-miles-web usage` prints calls per key for billing.

Endpoints: `POST /api/demo`, `POST /api/feed`, plus `GET /healthz` and `GET /api/spec` (machine-readable field list).
Files are sent as `{"name": ..., "content": ...}`, folders as `{"files": [...]}` or a base64 zip.

## Pricing

Every plan starts with a 14-day free trial. Prices in USD, billed monthly unless noted.

| Plan | Price | Includes |
|---|---|---|
| **Merchant** | $99 per month | Up to 10,000 members; Tiers and promos; Offer feed |
| **Growth** | $499 per month | Unlimited members; Fraud limits; Analytics |
| **Network** | Custom (contact sales) | Coalition programs; Agent platform integrations; SLA |

To start a trial or buy a plan, [request access](https://github.com/eliem08/agent-miles/issues/new?title=Agent%20Miles%20trial&labels=sales).

## Licence

Proprietary. Copyright (c) 2026 eliem08. All rights reserved. Use requires a paid plan or an active trial; see [LICENSE](LICENSE).
<!-- sell-kit:end -->

## What it does

- **Earn rules**: points per $ by category, first-purchase bonus, promo
  multipliers with date windows, tier multipliers
- **Tiers** (Member / Silver / Gold / Platinum) on trailing-12-month qualifying spend,
  re-evaluated on every purchase
- **Point lots with expiry** (FIFO burn, 18-month expiry by default)
- **Redemption catalogue** (rewards with points cost and $ value) and **pay-with-points**
- **Fraud controls**: daily earn cap per member, velocity limit, self-referral block
- **Machine-readable offer feed** (`offers.json`) — exactly what an agent needs to
  compute value: earn rates, active promos, point value in $, tier thresholds
- **Agent optimiser**: given a cart and several merchants' feeds (with prices),
  pick the merchant with the lowest *effective* price (price − value of points earned)

## Quickstart

```bash
pip install -e .
agent-miles demo
agent-miles feed > offers.json
```

## Roadmap

- Program federation: earn at one merchant, redeem at partners (coalition, like airline alliances)
- Signed feeds so agents can trust the published value (pairs with agentwarden)
- Agent-specific perks: API-only discounts, priority fulfilment for high-tier agents

## Development

Zero runtime dependencies; Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m unittest discover -s tests -t .           # unit + CLI smoke tests
ruff check . && ruff format --check .               # lint + format
```

```
agent_miles/core.py       domain logic (pure, importable, fully tested)
agent_miles/__main__.py   CLI (`agent-miles ...` / `python -m agent_miles ...`)
tests/                unit tests + generated CLI smoke tests
```

CI runs lint and tests on Ubuntu and Windows across Python 3.10, 3.12 and 3.13.
Design, data model, trade-offs and production path: **[ARCHITECTURE.md](ARCHITECTURE.md)**.

Part of the [agent-economy](https://github.com/eliem08/agent-economy) portfolio (idea #39).
