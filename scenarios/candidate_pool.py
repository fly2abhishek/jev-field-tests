"""One job, eight candidates written to span the range. Does the score separate them, and in the intended order?"""
from jevlab import client

from . import _data as d

TITLE = "Ranking a graded candidate pool"
FLOOR = 0.3  # a keyword-stuffed résumé earns about 0.2 per requirement; treat that as zero


def run(args):
    rows = []
    for name, text in d.POOL.items():
        response, _ = client.ask({"resume": text}, d.POOL_QUESTIONS)
        answers = response["answers"]
        nouls = {k: answers[k]["noul"] for k in d.POOL_WEIGHTS}
        rows.append({
            "candidate": name,
            "composite": sum(d.POOL_WEIGHTS[k] * v for k, v in nouls.items()),
            "floored": sum(d.POOL_WEIGHTS[k] * (v if v >= FLOOR else 0.0) for k, v in nouls.items()),
            "overall": answers["overall"]["score"] / 4,
            "confidence": answers["overall"]["confidence"],
            "nouls": nouls,
        })
    print(f"Job: {d.JOB}\n")
    for r in rows:
        print(f"  {r['candidate']:30} composite {r['composite']:.2f}  floored {r['floored']:.2f}  overall {r['overall']:.2f} (conf {r['confidence']:.2f})  " + " ".join(f"{k[:5]}={v:.2f}" for k, v in r["nouls"].items()))
    print()
    for key in ("composite", "floored", "overall"):
        order = " ".join(r["candidate"][0] for r in sorted(rows, key=lambda r: -r[key]))
        values = [r[key] for r in rows]
        print(f"  order by {key:9}: {order}   spread {max(values) - min(values):.2f}")
    print("  intended order    : 1 2 3 4 5 6 7 8")
    return {"rows": rows}
