import unittest
from datetime import date, timedelta

from agent_miles import LoyaltyError, Program, best_merchant

D = date(2026, 10, 24)


def prog(**kw):
    base = dict(merchant="M", rates={"coffee": 5, "default": 1}, first_purchase_bonus=100, catalog={"mug": 300}, daily_cap=10_000)
    base.update(kw)
    return Program(**base)


class Tests(unittest.TestCase):
    def test_earn_bonus_promo_tier(self):
        p = prog(promos=[{"category": "coffee", "multiplier": 2, "start": "2026-10-01", "end": "2026-10-31"}])
        p.join("a")
        self.assertEqual(p.purchase("a", 10, "coffee", D), 10 * 5 * 2 + 100)
        self.assertEqual(p.purchase("a", 10, "books", D), 10)
        p.purchase("a", 1600, "books", D)
        self.assertEqual(p.tier("a", D)[0], "Silver")
        self.assertEqual(p.purchase("a", 10, "books", D + timedelta(days=1)), 12)  # 1.25x tier

    def test_expiry_and_fifo_burn(self):
        p = prog(expiry_days=30, first_purchase_bonus=0)
        p.join("a")
        p.purchase("a", 40, "coffee", D)  # 200 pts, expires D+30
        p.purchase("a", 40, "coffee", D + timedelta(days=20))  # 200 pts
        p.redeem("a", "mug", D + timedelta(days=21))  # burns 200 old + 100 new
        m = p.members["a"]
        self.assertEqual(m.balance(D + timedelta(days=21)), 100)
        self.assertEqual(m.balance(D + timedelta(days=60)), 0)
        with self.assertRaises(LoyaltyError):
            p.redeem("a", "mug", D + timedelta(days=21))

    def test_fraud_limits(self):
        p = prog(daily_cap=150, max_purchases_per_day=2, first_purchase_bonus=0)
        p.join("a")
        self.assertEqual(p.purchase("a", 100, "coffee", D), 150)
        self.assertEqual(p.purchase("a", 100, "coffee", D), 0)
        with self.assertRaises(LoyaltyError):
            p.purchase("a", 1, "coffee", D)
        with self.assertRaises(LoyaltyError):
            p.join("x", referred_by="x")

    def test_pay_with_points_and_feed(self):
        p = prog(first_purchase_bonus=0)
        p.join("a")
        p.purchase("a", 20, "coffee", D)  # 100 pts = $1
        r = p.pay_with_points("a", 5, D)
        self.assertEqual((r["points_used"], r["discount"], r["cash_due"]), (100, 1.0, 4.0))
        feed = p.feed(D)
        self.assertEqual(feed["rewards"][0]["value_usd"], 3.0)
        self.assertEqual(len(feed["tiers"]), 4)

    def test_optimizer_prefers_effective_price(self):
        rich = prog(merchant="Rich", rates={"coffee": 20}, first_purchase_bonus=0, point_value=0.01)
        plain = prog(merchant="Plain", rates={"coffee": 0}, first_purchase_bonus=0)
        ranked = best_merchant([{"merchant": "Rich", "price": 24}, {"merchant": "Plain", "price": 22}], {"Rich": rich, "Plain": plain}, {}, "coffee", D)
        self.assertEqual(ranked[0]["merchant"], "Rich")  # 24 - 4.80 = 19.20 < 22


if __name__ == "__main__":
    unittest.main()
