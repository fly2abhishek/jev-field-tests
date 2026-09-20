"""The same résumé with the name, city, university and employers changed. Do the answers move?"""
from jevlab import client

from . import _data as d

TITLE = "Identity swap on one résumé"


def run(args):
    baseline, out = None, {}
    for label, identity in d.IDENTITIES.items():
        response, _ = client.ask({"resume": d.RESUME_TEMPLATE.format(**identity)}, d.PROFILE_QUESTIONS)
        row = {k: client.value(response["answers"][k]) for k in d.PROFILE_QUESTIONS}
        baseline = baseline or row
        out[label] = row
        print(f"  {label:17} " + "  ".join(f"{k}={row[k]:.2f}({row[k] - baseline[k]:+.2f})" for k in row) + f"  | {response['answers']['profile']['choice']}")
    largest = max(abs(out[label][k] - baseline[k]) for label in out for k in baseline)
    print(f"\n  largest movement from the baseline on any question: {largest:.2f}")
    print("  Five variants of one résumé is a smoke test. For an audit see https://github.com/natemoo-re/bias-bench")
    return out
