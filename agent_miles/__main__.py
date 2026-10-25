import argparse
import csv
import json
import os
import sys
from datetime import date

from .core import Program, best_merchant


def _sample():
    beans = Program(
        "BeanCo",
        {"coffee": 5, "default": 1},
        point_value=0.01,
        first_purchase_bonus=300,
        promos=[{"category": "coffee", "multiplier": 2.0, "start": "2026-10-01", "end": "2026-10-31"}],
        catalog={"free bag": 2500, "mug": 1500},
    )
    grind = Program("GrindHouse", {"coffee": 3}, point_value=0.02, first_purchase_bonus=0, catalog={"free bag": 1200})
    return beans, grind


def _run(argv=None):
    ap = argparse.ArgumentParser(prog="agent-miles")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo")
    sub.add_parser("feed")
    a = ap.parse_args(argv)
    today = date(2026, 10, 24)
    beans, grind = _sample()
    if a.cmd == "feed":
        print(json.dumps(beans.feed(today), indent=2))
        return 0
    beans.join("agent-42")
    grind.join("agent-42")
    grind.purchase("agent-42", 40, "coffee", date(2026, 9, 1))
    print("Agent comparing a $24 bag of coffee:")
    for r in best_merchant(
        [{"merchant": "BeanCo", "price": 24.0}, {"merchant": "GrindHouse", "price": 22.0}],
        {"BeanCo": beans, "GrindHouse": grind},
        {"BeanCo": "agent-42", "GrindHouse": "agent-42"},
        "coffee",
        today,
    ):
        print(
            f"  {r['merchant']:<11} ${r['price']:.2f} + {r['points']} pts (${r['points_value']:.2f}) -> effective ${r['effective_price']:.2f}"
        )
    pts = beans.purchase("agent-42", 24, "coffee", today)
    print(
        f"Bought at BeanCo, earned {pts} pts; balance {beans.members['agent-42'].balance(today)}; tier {beans.tier('agent-42', today)[0]}"
    )
    print("Pay with points on next $5 order:", beans.pay_with_points("agent-42", 5, today))
    return 0


def main(argv=None):
    """Run the CLI; a bad input file or argument exits 2 with a one-line error instead of a traceback.

    Set AGENT_ECONOMY_DEBUG=1 to see the full traceback.
    """
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    try:
        return _run(argv)
    except (OSError, ValueError, KeyError, csv.Error) as e:
        if os.environ.get("AGENT_ECONOMY_DEBUG"):
            raise
        msg = e.args[0] if isinstance(e, KeyError) and e.args else e
        print(f"error: {msg}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
