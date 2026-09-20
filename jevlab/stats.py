"""Calibration and rank helpers."""


def calibration(rows: list[tuple[float, bool]], edges=(0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0001)):
    """rows = (confidence in the chosen answer, was it correct). Returns (bins, expected calibration error)."""
    bins, ece = [], 0.0
    for low, high in zip(edges, edges[1:]):
        bucket = [(c, ok) for c, ok in rows if low <= c < high]
        if not bucket:
            continue
        mean_conf = sum(c for c, _ in bucket) / len(bucket)
        accuracy = sum(ok for _, ok in bucket) / len(bucket)
        ece += len(bucket) / len(rows) * abs(mean_conf - accuracy)
        bins.append({"low": low, "high": min(high, 1.0), "n": len(bucket), "confidence": mean_conf, "accuracy": accuracy})
    return bins, ece


def print_calibration(bins, ece):
    for b in bins:
        print(f"  conf {b['low']:.2f}-{b['high']:.2f}  n={b['n']:4}  mean conf {b['confidence']:.3f}  accuracy {b['accuracy']:.3f}")
    print(f"  expected calibration error {ece:.4f}")


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * q))]
