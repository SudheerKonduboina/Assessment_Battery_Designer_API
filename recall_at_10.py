# recall_at_10.py
# ─────────────────────────────────────────────────────────────────────────────
# Recall@10 computation module.
# Formula: Recall@10 = |relevant ∩ top_10_recommended| / |relevant|
# Mean Recall@10 = average across all traces
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations


def recall_at_k(
    recommended: list[str],
    relevant: list[str],
    k: int = 10,
) -> float:
    """
    Compute Recall@K for a single query.
    """
    if not relevant:
        return 0.0

    top_k = set(name.strip().lower() for name in recommended[:k])
    ground_truth = set(name.strip().lower() for name in relevant)

    hits = len(top_k & ground_truth)
    return hits / len(ground_truth)


def mean_recall_at_k(
    results: list[dict],
    k: int = 10,
) -> dict:
    """
    Compute Mean Recall@K across multiple traces.
    """
    per_trace = []
    total_recall = 0.0

    for result in results:
        r = recall_at_k(result["recommended"], result["relevant"], k)
        hits = int(r * len(result["relevant"]))
        per_trace.append({
            "trace_id":       result["trace_id"],
            "recall":         round(r, 4),
            "hits":           hits,
            "total_relevant": len(result["relevant"]),
            "recommended":    result["recommended"][:k],
        })
        total_recall += r

    mean = total_recall / len(results) if results else 0.0

    return {
        "mean_recall_at_k": round(mean, 4),
        "k":                k,
        "trace_count":      len(results),
        "per_trace":        per_trace,
    }


if __name__ == "__main__":
    # Quick self-test
    recs = ["Java 8 (New)", "OPQ32r", "SHL Verify Interactive G+", "SQL (New)", "Python (New)"]
    rel  = ["Java 8 (New)", "SQL (New)", "OPQ32r", "Core Java (Advanced Level) (New)"]
    r    = recall_at_k(recs, rel)
    print(f"Self-test Recall@10: {r:.4f}  (expected ~0.75)")
    assert abs(r - 0.75) < 0.01, "Self-test failed"
    print("recall_at_10.py: self-test PASSED")
