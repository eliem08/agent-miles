import contextlib
import io
import json
import os
import tempfile
import unittest

from agent_miles.__main__ import main
from agent_miles.ops import load


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = main(list(argv))
    return code, out.getvalue()


class MilesOpsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "miles.json")
        self.s = ["--store", self.path]
        self.ok("program-init", "RunCo", "--rate", "shoes=3")
        self.ok("reward-add", "Free socks", "800")
        self.ok("join", "bot")

    def tearDown(self):
        self.tmp.cleanup()

    def ok(self, *argv):
        code, out = run(*argv, *self.s)
        self.assertEqual(code, 0, out)
        return out

    def test_earn_redeem_pay_and_persist(self):
        self.assertIn("earned 860 points", self.ok("purchase", "bot", "120", "--category", "shoes"))  # 360 + bonus
        self.assertIn("balance 60", self.ok("redeem", "bot", "Free socks"))
        self.assertIn("cash due $49.40", self.ok("pay", "bot", "50"))
        prog = load(self.path)
        self.assertEqual(len(prog.members["bot"].purchases), 1)
        self.assertEqual(run("redeem", "bot", "Free socks", *self.s)[0], 1)  # nothing left to spend

    def test_promo_multiplies_points_inside_its_window_only(self):
        self.ok("promo-add", "--category", "shoes", "--multiplier", "2", "--start", "2026-12-01", "--end", "2026-12-31")
        self.ok("purchase", "bot", "10", "--on", "2026-11-30")  # first purchase: 30 + 500 bonus
        self.assertIn("earned 60 points", self.ok("purchase", "bot", "10", "--category", "shoes", "--on", "2026-12-05"))
        self.assertIn("earned 30 points", self.ok("purchase", "bot", "10", "--category", "shoes", "--on", "2027-01-05"))

    def test_offer_feed_is_machine_readable(self):
        feed = json.loads(self.ok("offers"))
        self.assertEqual((feed["merchant"], feed["rewards"][0]["value_usd"]), ("RunCo", 8.0))

    def test_refusals(self):
        for argv in (
            ["program-init", "Other"],  # one programme per store
            ["join", "bot"],
            ["join", "x", "--referred-by", "nobody"],
            ["purchase", "ghost", "5"],
            ["purchase", "bot", "-5"],
            ["pay", "bot", "-5"],
            ["reward-add", "free", "0"],
            ["promo-add", "--category", "*", "--multiplier", "2", "--start", "2026-12-31", "--end", "2026-12-01"],
        ):
            with self.subTest(argv=argv):
                self.assertEqual(run(*argv, *self.s)[0], 1)

    def test_commands_need_a_programme_first(self):
        empty = ["--store", os.path.join(self.tmp.name, "none.json")]
        self.assertEqual(run("join", "bot", *empty)[0], 1)


if __name__ == "__main__":
    unittest.main()
