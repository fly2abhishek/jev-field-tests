"""TypeSafe says adding questions barely changes the response time. One ticket, 1 to 120 questions."""
import statistics

from jevlab import client

from . import _data as d

TITLE = "Latency against questions per request"


def run(args):
    out = []
    for n in (1, 5, 20, 60, 120):
        questions = {
            f"q{i}": {"type": "noul", "instructions": f"The message {d.TICKET_FACTS[i % len(d.TICKET_FACTS)]}" + ("" if i < len(d.TICKET_FACTS) else f" (check {i})")}
            for i in range(n)
        }
        timings = []
        for _ in range(3):
            response, ms = client.ask(d.TICKET, questions)
            timings.append(ms)
        out.append({"questions": n, "median_ms": statistics.median(timings), "input_tokens": response["usage"]["input_tokens"]})
        print(f"  {n:3} questions: median {statistics.median(timings):5.0f} ms, {response['usage']['input_tokens']} input tokens")
    return {"rows": out}
