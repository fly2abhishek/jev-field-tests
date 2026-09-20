"""Code review as a yes/no judgement: can request input change the structure of this SQL?"""
from jevlab import client

from . import _data as d

TITLE = "SQL injection in 12 snippets"
QUESTION = {"vulnerable": {"type": "noul", "instructions": "Can an attacker who controls the request input change the structure of the SQL statement in this snippet?"}}


def run(args):
    rows = []
    for label, code in d.SQL_SNIPPETS:
        response, _ = client.ask({"code": code}, QUESTION)
        p = response["answers"]["vulnerable"]["noul"]
        rows.append({"label": label, "p": p, "code": code})
        print(f"  [{label}] {p:.2f}{' WRONG' if (p >= 0.5) != bool(label) else ''} | {code.splitlines()[-1][:90]}")
    print(f"\n  {sum((r['p'] >= 0.5) == bool(r['label']) for r in rows)}/{len(rows)} correct")
    return {"rows": rows}
