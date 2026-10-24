"""Loyalty engine for agent customers: earning, tiers, expiring lots, redemption, fraud limits, offer feed, optimiser."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

__all__ = ["Program", "Member", "LoyaltyError", "best_merchant", "TIERS"]

TIERS = [("Platinum", 10000, 2.0), ("Gold", 5000, 1.5), ("Silver", 1500, 1.25), ("Member", 0, 1.0)]


class LoyaltyError(Exception):
    pass


@dataclass
class Member:
    member_id: str
    referred_by: str | None = None
    lots: list = field(default_factory=list)  # [earned_on, expires_on, remaining]
    purchases: list = field(default_factory=list)  # (day, amount)
    earned_by_day: dict = field(default_factory=lambda: defaultdict(int))

    def balance(self, on: date) -> int:
        return sum(l[2] for l in self.lots if l[1] > on)


@dataclass
class Program:
    merchant: str
    rates: dict = field(default_factory=lambda: {"default": 1})  # points per $ by category
    point_value: float = 0.01  # $ per point at redemption
    first_purchase_bonus: int = 500
    promos: list = field(default_factory=list)  # {"category", "multiplier", "start", "end"}
    expiry_days: int = 548
    daily_cap: int = 20000
    max_purchases_per_day: int = 20
    catalog: dict = field(default_factory=dict)  # reward -> points
    members: dict = field(default_factory=dict)

    def join(self, member_id: str, referred_by: str | None = None) -> Member:
        if referred_by == member_id:
            raise LoyaltyError("self-referral not allowed")
        self.members[member_id] = Member(member_id, referred_by)
        return self.members[member_id]

    def tier(self, member_id: str, on: date) -> tuple[str, float]:
        m = self.members[member_id]
        spend = sum(a for d, a in m.purchases if on - timedelta(days=365) < d <= on)
        for name, threshold, mult in TIERS:
            if spend >= threshold:
                return name, mult
        return "Member", 1.0

    def _promo(self, category: str, on: date) -> float:
        mult = 1.0
        for p in self.promos:
            if p["category"] in (category, "*") and date.fromisoformat(p["start"]) <= on <= date.fromisoformat(
                p["end"]
            ):
                mult = max(mult, p["multiplier"])
        return mult

    def quote_points(self, member_id: str | None, amount: float, category: str, on: date) -> int:
        rate = self.rates.get(category, self.rates.get("default", 1))
        tier_mult = self.tier(member_id, on)[1] if member_id in self.members else 1.0
        pts = amount * rate * tier_mult * self._promo(category, on)
        first = member_id not in self.members or not self.members[member_id].purchases
        return int(pts) + (self.first_purchase_bonus if first else 0)

    def purchase(self, member_id: str, amount: float, category: str, on: date) -> int:
        m = self.members[member_id]
        if amount <= 0:
            raise LoyaltyError("amount must be positive")
        if sum(1 for d, _ in m.purchases if d == on) >= self.max_purchases_per_day:
            raise LoyaltyError("velocity limit: too many purchases today")
        pts = self.quote_points(member_id, amount, category, on)
        room = max(0, self.daily_cap - m.earned_by_day[on])
        pts = min(pts, room)
        m.purchases.append((on, amount))
        if pts:
            m.lots.append([on, on + timedelta(days=self.expiry_days), pts])
            m.earned_by_day[on] += pts
        return pts

    def _burn(self, m: Member, points: int, on: date):
        if m.balance(on) < points:
            raise LoyaltyError(f"insufficient points: have {m.balance(on)}, need {points}")
        for lot in sorted(m.lots, key=lambda l: l[1]):  # soonest-expiring first
            if lot[1] <= on or not points:
                continue
            take = min(lot[2], points)
            lot[2] -= take
            points -= take

    def redeem(self, member_id: str, reward: str, on: date) -> dict:
        if reward not in self.catalog:
            raise LoyaltyError("unknown reward")
        cost = self.catalog[reward]
        m = self.members[member_id]
        self._burn(m, cost, on)
        return {"reward": reward, "points": cost, "balance": m.balance(on)}

    def pay_with_points(self, member_id: str, amount: float, on: date) -> dict:
        m = self.members[member_id]
        usable = min(m.balance(on), int(amount / self.point_value))
        self._burn(m, usable, on)
        return {
            "points_used": usable,
            "discount": round(usable * self.point_value, 2),
            "cash_due": round(amount - usable * self.point_value, 2),
        }

    def feed(self, on: date) -> dict:
        """Machine-readable offer feed for agents."""
        return {
            "merchant": self.merchant,
            "as_of": on.isoformat(),
            "point_value_usd": self.point_value,
            "earn": {
                "rates_per_usd": self.rates,
                "first_purchase_bonus": self.first_purchase_bonus,
                "active_promos": [
                    p for p in self.promos if date.fromisoformat(p["start"]) <= on <= date.fromisoformat(p["end"])
                ],
            },
            "tiers": [{"name": n, "trailing_12m_spend": t, "multiplier": mult} for n, t, mult in reversed(TIERS)],
            "expiry_days": self.expiry_days,
            "rewards": [
                {"reward": r, "points": p, "value_usd": round(p * self.point_value, 2)} for r, p in self.catalog.items()
            ],
        }


def best_merchant(
    offers: list[dict], programs: dict[str, Program], member_ids: dict[str, str], category: str, on: date
) -> list[dict]:
    """offers: [{"merchant", "price"}]. Rank by effective price = price - $value of points earned."""
    rows = []
    for o in offers:
        prog = programs.get(o["merchant"])
        pts = prog.quote_points(member_ids.get(o["merchant"]), o["price"], category, on) if prog else 0
        value = pts * prog.point_value if prog else 0.0
        rows.append(
            {
                "merchant": o["merchant"],
                "price": o["price"],
                "points": pts,
                "points_value": round(value, 2),
                "effective_price": round(o["price"] - value, 2),
            }
        )
    return sorted(rows, key=lambda r: r["effective_price"])
