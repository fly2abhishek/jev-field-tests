#!/usr/bin/env python3
"""Run one scenario, several, or all of them. Standard library only."""
import argparse
import importlib
import json
import sys
import time
from pathlib import Path

SCENARIOS = [
    "scaling", "stability", "weaknesses", "long_context",
    "requirement_evidence", "candidate_pool", "identity_swap", "interview",
    "guardrail", "sql_injection",
    "calibration_boolq", "calibration_agnews",
]
ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenarios", nargs="*", help="scenario names, 'all', or 'list'")
    parser.add_argument("--n", type=int, default=None, help="items to use in the dataset scenarios (default 400 BoolQ, 300 AG News)")
    parser.add_argument("--workers", type=int, default=6, help="parallel requests in the dataset scenarios")
    args = parser.parse_args()

    if not args.scenarios or args.scenarios == ["list"]:
        for name in SCENARIOS:
            print(f"  {name:22} {importlib.import_module(f'scenarios.{name}').TITLE}")
        print("\nUsage: python run.py <scenario> [<scenario> ...] | all")
        return
    names = SCENARIOS if args.scenarios == ["all"] else args.scenarios
    unknown = [n for n in names if n not in SCENARIOS]
    if unknown:
        sys.exit(f"Unknown scenario: {', '.join(unknown)}. Try: python run.py list")

    from jevlab import client
    client.api_key()  # fail early, before any work
    (ROOT / "runs").mkdir(exist_ok=True)
    for name in names:
        module = importlib.import_module(f"scenarios.{name}")
        print(f"\n=== {name}: {module.TITLE}  (model {client.model()})\n")
        started = time.time()
        result = module.run(args)
        path = ROOT / "runs" / f"{name}.json"
        path.write_text(json.dumps({"scenario": name, "model": client.model(), "result": result}, indent=1, default=str))
        print(f"\n  done in {time.time() - started:.0f}s, raw output in runs/{name}.json")


if __name__ == "__main__":
    main()
