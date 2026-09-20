"""Are the probabilities honest? 400 labelled yes/no questions from BoolQ, with an optional Gemini baseline."""
from concurrent.futures import ThreadPoolExecutor

from jevlab import client, datasets, gemini, stats

TITLE = "Calibration on BoolQ (yes/no questions with human labels)"
SCHEMA = {"type": "OBJECT", "properties": {"answer": {"type": "BOOLEAN"}, "confidence": {"type": "NUMBER"}}, "required": ["answer", "confidence"]}


def run(args):
    count = args.n or 400
    offsets = [0, 1000, 2000, 3000][: max(1, -(-count // 100))]
    data = datasets.rows("google/boolq", "validation", offsets)[:count]

    def jev_one(row):
        response, ms = client.ask({"passage": row["passage"]}, {"a": {"type": "noul", "instructions": f"According to the passage: {row['question']}?"}})
        return {"p": response["answers"]["a"]["noul"], "label": bool(row["answer"]), "ms": ms, "tokens": response["usage"]["input_tokens"]}

    with ThreadPoolExecutor(args.workers) as pool:
        jev = list(pool.map(jev_one, data))
    rows = [(max(r["p"], 1 - r["p"]), (r["p"] >= 0.5) == r["label"]) for r in jev]
    bins, ece = stats.calibration(rows)
    tokens = sum(r["tokens"] for r in jev)
    print(f"Jev: {len(jev)} questions, accuracy {sum(ok for _, ok in rows) / len(rows):.3f}, {tokens} input tokens (${tokens * 0.042 / 1e6:.4f})")
    stats.print_calibration(bins, ece)
    latencies = [r["ms"] for r in jev]
    print(f"  latency p50 {stats.percentile(latencies, 0.5):.0f} ms, p95 {stats.percentile(latencies, 0.95):.0f} ms")
    print(f"  distinct confidence values (2 dp): {len({round(c, 2) for c, _ in rows})}")
    result = {"jev": {"accuracy": sum(ok for _, ok in rows) / len(rows), "ece": ece, "bins": bins, "rows": jev}}

    if not gemini.available():
        print("\nGemini baseline skipped: set GEMINI_API_KEY to enable it.")
        return result

    def llm_one(row):
        prompt = (
            f"Passage: {row['passage']}\n\nQuestion: {row['question']}?\n\nAnswer the question from the passage. Give `answer` and "
            "`confidence`, the probability between 0.5 and 1 that your answer is correct. Be honest about uncertainty."
        )
        parsed, ms, _ = gemini.ask(prompt, SCHEMA)
        if parsed is None:
            return None
        return {"answer": parsed["answer"], "c": min(max(float(parsed["confidence"]), 0.5), 1.0), "label": bool(row["answer"]), "ms": ms}

    with ThreadPoolExecutor(args.workers) as pool:
        llm = list(pool.map(llm_one, data))
    answered = [r for r in llm if r]
    lrows = [(r["c"], r["answer"] == r["label"]) for r in answered]
    lbins, lece = stats.calibration(lrows)
    print(f"\n{gemini.model()}: {len(answered)} answered, accuracy {sum(ok for _, ok in lrows) / len(lrows):.3f}")
    stats.print_calibration(lbins, lece)
    print(f"  latency p50 {stats.percentile([r['ms'] for r in answered], 0.5):.0f} ms")
    print(f"  distinct confidence values (2 dp): {len({round(c, 2) for c, _ in lrows})}")
    pairs = [(j, l) for j, l in zip(jev, llm) if l]
    same = sum((j["p"] >= 0.5) == l["answer"] for j, l in pairs) / len(pairs)
    jev_wrong = {i for i, (j, _) in enumerate(pairs) if (j["p"] >= 0.5) != j["label"]}
    llm_wrong = {i for i, (_, l) in enumerate(pairs) if l["answer"] != l["label"]}
    print(f"\nSame answer on {same:.3f} of questions. Jev wrong {len(jev_wrong)}, LLM wrong {len(llm_wrong)}, both wrong {len(jev_wrong & llm_wrong)}.")
    result["llm"] = {"model": gemini.model(), "accuracy": sum(ok for _, ok in lrows) / len(lrows), "ece": lece, "bins": lbins}
    return result
