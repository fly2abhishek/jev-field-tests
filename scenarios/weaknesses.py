"""The weaknesses TypeSafe documents: counting, arithmetic, date logic. Truth in brackets."""
import random

from jevlab import client

TITLE = "Counting, arithmetic and dates"


def _p(state, statement):
    return client.ask(state, {"a": {"type": "noul", "instructions": statement}})[0]["answers"]["a"]["noul"]


def run(args):
    random.seed(11)
    out = []

    def record(group, label, truth, p):
        out.append({"group": group, "case": label, "truth": truth, "p": p})
        print(f"  {label:58} [{truth}] {p:.2f}{'' if (p >= 0.5) == truth else '  <- wrong'}")

    print("Counting")
    fruits = ["apple", "pear", "fig", "plum", "kiwi", "lime", "date", "peach", "mango", "grape", "melon", "guava", "lemon"]
    bag = [random.choice(fruits) for _ in range(60)]
    n = bag.count("kiwi")
    for claim in (n, n + 2, max(0, n - 2)):
        record("count", f"'kiwi' appears exactly {claim} times in 60 items", claim == n, _p("Delivery log: " + ", ".join(bag), f"The word kiwi appears exactly {claim} times in the delivery log."))

    print("Arithmetic")
    items = [("Laptop", 1249.00), ("Dock", 189.50), ("Monitor", 415.25), ("Cable", 18.75), ("Warranty", 129.00)]
    total = sum(v for _, v in items)
    for claimed in (total, total + 100, total - 10):
        state = {"line_items": [{"item": k, "amount": v} for k, v in items], "invoice_total": claimed}
        record("sum", f"invoice total {claimed:.2f} equals the sum {total:.2f}", abs(claimed - total) < 0.01, _p(state, "The invoice total equals the sum of the line items."))
    record("compare", "1849.50 is within a limit of 1850.00", True, _p({"invoice_total": 1849.50, "approval_limit": 1850.00}, "The invoice total is within the approval limit."))
    record("compare", "18500.00 is within a limit of 1850.00", False, _p({"invoice_total": 18500.00, "approval_limit": 1850.00}, "The invoice total is within the approval limit."))

    print("Dates")
    for opened, closed, truth, days in (("2026-01-15", "2026-05-02", True, 107), ("12 Nov 2025", "2026-02-14", True, 94), ("12 Nov 2025", "2026-02-09", False, 89), ("2026-03-01", "2026-05-20", False, 80)):
        record("dates", f"{opened} -> {closed} is more than 90 days ({days})", truth, _p({"opened": opened, "closed": closed}, "More than 90 days passed between opened and closed."))
    record("dates", "27 Feb comes before 3 Mar, mixed formats", True, _p({"contract_signed": "3 March 2026", "contract_cancelled": "2026-02-27"}, "The contract was cancelled before it was signed."))
    chain = "Order A shipped on 4 Sept. Order B shipped two days before Order A. Order C shipped the day after Order B."
    record("dates", "two-step reasoning: C shipped on 3 Sept", True, _p(chain, "Order C shipped on 3 Sept."))
    record("dates", "two-step reasoning: C shipped on 5 Sept", False, _p(chain, "Order C shipped on 5 Sept."))
    return {"rows": out}
