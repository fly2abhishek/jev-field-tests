"""Run-to-run variance, option-order sensitivity, and whether noul and choice agree on the same question."""
import random

from jevlab import client

from . import _data as d

TITLE = "Stability and internal consistency"


def run(args):
    random.seed(7)
    print("1. The same request eight times.")
    questions = {k: d.requirement(q) for k, q in d.REQUIREMENTS.items()}
    runs = [client.ask({"resume": d.CANDIDATES["B_described"]}, questions)[0]["answers"] for _ in range(8)]
    variance = {}
    for k in questions:
        values = [r[k]["noul"] for r in runs]
        variance[k] = {"min": min(values), "max": max(values)}
        print(f"  {k:24} min {min(values):.4f}  max {max(values):.4f}")

    print("\n2. A five-option choice with the options shuffled six times.")
    seen = []
    for _ in range(6):
        items = list(d.TEAMS.items())
        random.shuffle(items)
        a = client.ask(d.TICKET, {"team": {"type": "choice", "instructions": "Which team should handle this message?", "criteria": dict(items)}})[0]["answers"]["team"]
        seen.append((a["choice"], round(a["probabilities"][a["choice"]], 2)))
    print(f"  {seen}")

    print("\n3. One ambivalent review, asked three ways.")
    a = client.ask(d.AMBIVALENT_REVIEW, {
        "satisfied": {"type": "noul", "instructions": "The customer is satisfied with the new dashboard."},
        "not_satisfied": {"type": "noul", "instructions": "The customer is not satisfied with the new dashboard."},
        "as_choice": {"type": "choice", "instructions": "Is the customer satisfied with the new dashboard?", "criteria": {"yes": "Satisfied.", "no": "Not satisfied."}},
    })[0]["answers"]
    p, n, c = a["satisfied"]["noul"], a["not_satisfied"]["noul"], a["as_choice"]["probabilities"]["yes"]
    print(f"  P(satisfied) {p:.2f} + P(not satisfied) {n:.2f} = {p + n:.2f}; the two-option choice gives yes = {c:.2f}")
    return {"variance": variance, "shuffled": seen, "consistency": {"satisfied": p, "not_satisfied": n, "choice_yes": c}}
