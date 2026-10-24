# agent-miles

[![CI](https://github.com/eliem08/agent-miles/actions/workflows/ci.yml/badge.svg)](https://github.com/eliem08/agent-miles/actions/workflows/ci.yml)

> **Frequent flyer miles for agents** — loyalty programs built for agents.

When agents do the shopping, brand loyalty breaks: an agent has no
emotional attachment to your coffee shop. It optimises. So loyalty has to
become **machine-readable value** that agents can see, compare and redeem.
`agent-miles` is a loyalty engine designed for agent customers.

## What the MVP does

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
- Signed feeds so agents can trust the published value (pairs with agent-okta)
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
