"""Operating commands: run one merchant's loyalty programme on a persistent store (also served by the web app)."""

import json
import os
from collections import defaultdict
from dataclasses import fields
from datetime import date

from .core import LoyaltyError, Member, Program

OPS = ("program-init", "reward-add", "promo-add", "join", "purchase", "balance", "redeem", "pay", "offers")


def _day(text) -> date:
    if not text:
        return date.today()
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise LoyaltyError(f"{text!r} is not a date like 2026-12-01") from None


def load(path: str) -> Program | None:
    try:
        with open(path, encoding="utf-8-sig") as fh:
            doc = json.load(fh)
    except FileNotFoundError:
        return None
    if not isinstance(doc, dict) or "merchant" not in doc:
        raise LoyaltyError(f"{path}: not an agent-miles store")
    members = {}
    for mid, m in doc.pop("members", {}).items():
        members[mid] = Member(
            mid,
            m["referred_by"],
            [[date.fromisoformat(a), date.fromisoformat(b), n] for a, b, n in m["lots"]],
            [(date.fromisoformat(d), amt) for d, amt in m["purchases"]],
            defaultdict(int, {date.fromisoformat(d): n for d, n in m["earned_by_day"].items()}),
        )
    return Program(**doc, members=members)


def save(p: Program, path: str):
    # not asdict(p): on Python 3.10 it cannot copy the members' defaultdicts
    doc = {f.name: getattr(p, f.name) for f in fields(p) if f.name != "members"}
    doc["members"] = {
        mid: {
            "referred_by": m.referred_by,
            "lots": [[a.isoformat(), b.isoformat(), n] for a, b, n in m.lots],
            "purchases": [[d.isoformat(), amt] for d, amt in m.purchases],
            "earned_by_day": {d.isoformat(): n for d, n in m.earned_by_day.items()},
        }
        for mid, m in p.members.items()
    }
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
    os.replace(tmp, path)


def add_ops(sub):
    store = os.environ.get("AGENT_MILES_STORE", "miles.json")
    p = sub.add_parser("program-init", help="create the merchant's programme")
    p.add_argument("merchant")
    p.add_argument("--rate", action="append", default=[], help="points per $ by category, e.g. default=1 shoes=3")
    p.add_argument("--point-value", type=float, default=0.01, help="$ per point at redemption")
    p.add_argument("--first-purchase-bonus", type=int, default=500)
    p = sub.add_parser("reward-add", help="add a reward to the catalogue")
    p.add_argument("reward")
    p.add_argument("points", type=int)
    p = sub.add_parser("promo-add", help="run a points multiplier for a category and date range")
    p.add_argument("--category", required=True, help="a category, or * for everything")
    p.add_argument("--multiplier", type=float, required=True)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p = sub.add_parser("join", help="enrol an agent (or the person it shops for)")
    p.add_argument("member")
    p.add_argument("--referred-by")
    p = sub.add_parser("purchase", help="record a purchase and award points")
    p.add_argument("member")
    p.add_argument("amount", type=float)
    p.add_argument("--category", default="default")
    p.add_argument("--on", help="YYYY-MM-DD, default today")
    sub.add_parser("balance", help="a member's points, tier and next expiry").add_argument("member")
    p = sub.add_parser("redeem", help="spend points on a reward")
    p.add_argument("member")
    p.add_argument("reward")
    p = sub.add_parser("pay", help="use points against a purchase")
    p.add_argument("member")
    p.add_argument("amount", type=float)
    sub.add_parser("offers", help="the machine-readable offer feed agents read (prints JSON)")
    for name in OPS:
        sub.choices[name].add_argument("--store", default=store)


def run_ops(a) -> int:
    try:
        prog = load(a.store)
        if a.cmd == "program-init":
            if prog:
                raise LoyaltyError(f"this store already runs the {prog.merchant} programme")
            rates = {"default": 1}
            for item in a.rate:
                k, sep, v = item.partition("=")
                try:
                    rates[k.strip()] = float(v)
                except ValueError:
                    raise LoyaltyError(f"--rate must look like category=points, got {item!r}") from None
                if not sep or not k.strip() or rates[k.strip()] <= 0:
                    raise LoyaltyError(f"--rate must look like category=points, got {item!r}")
            if not a.point_value > 0:
                raise LoyaltyError("point value must be > 0")
            prog = Program(a.merchant, rates, a.point_value, a.first_purchase_bonus)
            print(f"{a.merchant} programme created: {rates['default']:g} point(s) per $, ${a.point_value} per point")
        elif not prog:
            raise LoyaltyError("no programme yet: run program-init first")
        else:
            _run(prog, a)
        save(prog, a.store)
        return 0
    except LoyaltyError as e:
        print(f"refused: {e}")
        return 1


def _member(prog: Program, mid: str) -> Member:
    if mid not in prog.members:
        raise LoyaltyError(f"{mid!r} is not a member; run join first")
    return prog.members[mid]


def _run(prog: Program, a):
    c, today = a.cmd, date.today()
    if c == "reward-add":
        if a.points < 1:
            raise LoyaltyError("a reward must cost at least 1 point")
        prog.catalog[a.reward] = a.points
        print(f"{a.reward}: {a.points:,} points (worth ${a.points * prog.point_value:,.2f})")
    elif c == "promo-add":
        start, end = _day(a.start), _day(a.end)
        if end < start or not a.multiplier > 1:
            raise LoyaltyError("a promo needs end >= start and a multiplier above 1")
        promo = {"category": a.category, "multiplier": a.multiplier, "start": start.isoformat(), "end": end.isoformat()}
        prog.promos.append(promo)
        print(f"{a.multiplier:g}x points on {a.category} from {start} to {end}")
    elif c == "join":
        if a.referred_by and a.referred_by not in prog.members:
            raise LoyaltyError(f"referrer {a.referred_by!r} is not a member")
        prog.join(a.member, a.referred_by)
        print(f"{a.member} joined {prog.merchant}")
    elif c == "purchase":
        _member(prog, a.member)
        on = _day(a.on)
        pts = prog.purchase(a.member, a.amount, a.category, on)
        print(f"{a.member} earned {pts:,} points; balance {prog.members[a.member].balance(on):,}")
    elif c == "balance":
        m = _member(prog, a.member)
        tier, mult = prog.tier(a.member, today)
        live = sorted(l for l in m.lots if l[1] > today and l[2])
        nxt = f"; {live[0][2]:,} expire on {min(l[1] for l in live)}" if live else ""
        bal = m.balance(today)
        print(f"{a.member}: {bal:,} points (${bal * prog.point_value:,.2f}), {tier} tier ({mult:g}x){nxt}")
    elif c == "redeem":
        _member(prog, a.member)
        r = prog.redeem(a.member, a.reward, today)
        print(f"{a.member} redeemed {r['reward']} for {r['points']:,} points; balance {r['balance']:,}")
    elif c == "pay":
        _member(prog, a.member)
        r = prog.pay_with_points(a.member, a.amount, today)
        print(f"used {r['points_used']:,} points for ${r['discount']:,.2f} off; cash due ${r['cash_due']:,.2f}")
    else:
        print(json.dumps(prog.feed(today), indent=2))
