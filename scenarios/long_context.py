"""One error line hidden in log noise: position sensitivity, latency growth, and the hard 32k limit."""
from jevlab import client

TITLE = "Needle in a long state, and the context limit"
NEEDLE = "2026-09-14T03:12:09Z ERROR payments-db primary failed over to replica eu-2 after disk latency alarm"
QUESTIONS = {
    "failover": {"type": "noul", "instructions": "The log shows a database failover."},
    "oom": {"type": "noul", "instructions": "The log shows an out-of-memory kill."},
}


def _lines(n):
    return [f"2026-09-{(i % 28) + 1:02d}T10:{i % 60:02d}:00Z INFO worker-{i % 17} processed batch {i} in {(i * 37) % 900 + 100}ms queue=default" for i in range(n)]


def run(args):
    out = {"needle": [], "size": []}
    print("1. 300 log lines, the needle at the start, middle, end, and absent.")
    for position in (0.0, 0.5, 1.0, None):
        lines = _lines(300)
        if position is not None:
            lines.insert(int(position * len(lines)), NEEDLE)
        response, ms = client.ask("\n".join(lines), QUESTIONS)
        a = response["answers"]
        out["needle"].append({"position": position, "failover": a["failover"]["noul"], "oom": a["oom"]["noul"], "ms": ms})
        print(f"  needle at {str(position):5}: failover {a['failover']['noul']:.2f}  oom (never present) {a['oom']['noul']:.2f}  {response['usage']['input_tokens']} tokens  {ms:.0f} ms")

    print("\n2. Growing the state until the API refuses it.")
    for n in (100, 300, 500, 700, 900):
        try:
            response, ms = client.ask("\n".join(_lines(n)), QUESTIONS)
            out["size"].append({"lines": n, "tokens": response["usage"]["input_tokens"], "ms": ms})
            print(f"  {n:4} lines: {response['usage']['input_tokens']:6} tokens  {ms:.0f} ms")
        except client.JevError as error:
            out["size"].append({"lines": n, "error": str(error)})
            print(f"  {n:4} lines: refused, {error}")
    return out
