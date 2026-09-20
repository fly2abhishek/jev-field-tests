"""Calibration of the `choice` type on 300 news articles, and where a house labelling convention breaks it."""
import collections
from concurrent.futures import ThreadPoolExecutor

from jevlab import client, datasets, stats

TITLE = "Calibration on AG News (four-way choice)"
LABELS = ["world", "sports", "business", "sci_tech"]
CRITERIA = {
    "world": "International affairs, politics, conflict, diplomacy.",
    "sports": "Sport, athletes, matches, leagues.",
    "business": "Companies, markets, the economy, finance.",
    "sci_tech": "Science, technology, software, internet, space, health research.",
}


def run(args):
    count = args.n or 300
    data = datasets.rows("fancyzhx/ag_news", "test", [0, 3000, 6000][: max(1, -(-count // 100))])[:count]

    def one(row):
        response, _ = client.ask(row["text"], {"c": {"type": "choice", "instructions": "Which news section does this article belong to?", "criteria": CRITERIA}})
        answer = response["answers"]["c"]
        return {"pred": answer["choice"], "p": answer["probabilities"][answer["choice"]], "label": LABELS[row["label"]], "text": row["text"][:140]}

    with ThreadPoolExecutor(args.workers) as pool:
        out = list(pool.map(one, data))
    rows = [(r["p"], r["pred"] == r["label"]) for r in out]
    bins, ece = stats.calibration(rows, edges=(0, 0.6, 0.8, 0.9, 0.97, 1.0001))
    print(f"{len(out)} articles, accuracy {sum(ok for _, ok in rows) / len(rows):.3f}")
    stats.print_calibration(bins, ece)
    errors = collections.Counter((r["label"], r["pred"]) for r in out if r["pred"] != r["label"])
    print("\nErrors, as dataset label -> Jev's choice:")
    for (label, pred), n in errors.most_common():
        print(f"  {label:9} -> {pred:9} {n}")
    print("\nConfident errors (p >= 0.97), first few:")
    for r in [r for r in out if r["p"] >= 0.97 and r["pred"] != r["label"]][:8]:
        print(f"  [{r['label']} -> {r['pred']}] {r['text']}")
    return {"accuracy": sum(ok for _, ok in rows) / len(rows), "ece": ece, "bins": bins, "errors": {f"{a}->{b}": n for (a, b), n in errors.items()}}
