# evaluation_runner.py
# ─────────────────────────────────────────────────────────────────────────────
# Automated evaluation harness.
# Replays SHL public traces against your live POST /chat endpoint.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations
import argparse
import json
import time
import sys
from pathlib import Path
import requests

from recall_at_10 import mean_recall_at_k

# ── CATALOGUE LOADER (for hallucination check) ────────────────────────────────

def load_valid_names(catalogue_path: str = "app/data/shl_product_catalogue.json") -> set[str]:
    """Load all valid assessment names (lowercased) from the catalogue."""
    with open(catalogue_path, encoding="utf-8") as f:
        data = json.load(f)
    return {entry["name"].strip().lower() for entry in data if "name" in entry}


# ── TRACE LOADER ──────────────────────────────────────────────────────────────

def load_traces(traces_dir: str | Path) -> list[dict]:
    """
    Load all trace JSON files from a directory.
    """
    traces_dir = Path(traces_dir)
    if not traces_dir.exists():
        # Fallback to current dir if traces dir doesn't exist yet
        print(f"[WARN] Traces directory not found: {traces_dir}. Returning empty list.")
        return []

    traces: list[dict] = []
    json_files = sorted(traces_dir.glob("*.json"))
    if json_files:
        for f in json_files:
            with open(f, encoding="utf-8") as fp:
                trace = json.load(fp)
                if isinstance(trace, list):
                    traces.extend(trace)
                else:
                    traces.append(trace)
        print(f"[eval] Loaded {len(traces)} traces from {len(json_files)} files in {traces_dir}")
        return traces

    return []


# ── SCHEMA CHECKER ────────────────────────────────────────────────────────────

def check_schema(response: dict) -> list[str]:
    """Check response schema compliance. Returns list of error strings."""
    errors: list[str] = []
    required_top = {"reply", "recommendations", "end_of_conversation"}
    actual_top   = set(response.keys())

    missing = required_top - actual_top
    extra   = actual_top - required_top

    if missing:
        errors.append(f"Missing top-level keys: {missing}")
    if extra:
        errors.append(f"Extra top-level keys (schema violation): {extra}")

    if not isinstance(response.get("reply", None), str) or not response.get("reply", "").strip():
        errors.append("'reply' must be a non-empty string")

    if not isinstance(response.get("recommendations", None), list):
        errors.append("'recommendations' must be a list")
    else:
        recs = response["recommendations"]
        if len(recs) > 10:
            errors.append(f"recommendations has {len(recs)} items — max is 10")
        for i, r in enumerate(recs):
            allowed = {"name", "url", "test_type"}
            rec_keys = set(r.keys()) if isinstance(r, dict) else set()
            extra_rec = rec_keys - allowed
            missing_rec = allowed - rec_keys
            if extra_rec:
                errors.append(f"rec[{i}] has extra fields: {extra_rec}")
            if missing_rec:
                errors.append(f"rec[{i}] missing fields: {missing_rec}")

    if not isinstance(response.get("end_of_conversation", None), bool):
        errors.append("'end_of_conversation' must be a boolean")

    return errors


# ── CONVERSATION REPLAYER ─────────────────────────────────────────────────────

def replay_conversation(
    trace: dict,
    api_url: str,
    timeout: int = 25,
) -> dict:
    """
    Replay a single trace against the API.
    """
    base_url = api_url.rstrip("/")
    chat_url = f"{base_url}/chat"

    conversation = trace.get("conversation", [])
    trace_id     = trace.get("trace_id", trace.get("id", "unknown"))
    expected     = trace.get("expected_assessments",
                   trace.get("expected_shortlist",
                   trace.get("expected", [])))

    history:         list[dict]  = []
    all_errors:      list[str]   = []
    final_recs:      list[str]   = []
    turn_count:      int         = 0
    hallucinations:  list[str]   = []
    schema_passed:   bool        = True

    for turn in conversation:
        if turn.get("role") != "user":
            continue 

        history.append({"role": "user", "content": turn["content"]})
        turn_count += 1

        try:
            resp = requests.post(
                chat_url,
                json={"messages": history},
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            all_errors.append(f"Turn {turn_count}: {type(e).__name__}: {e}")
            break

        errors = check_schema(data)
        if errors:
            all_errors.extend([f"Turn {turn_count}: " + e for e in errors])
            schema_passed = False

        history.append({"role": "assistant", "content": data.get("reply", "")})

        recs = data.get("recommendations", [])
        if recs:
            final_recs = [r["name"] for r in recs if "name" in r]

        if data.get("end_of_conversation", False) or turn_count >= 8:
            break

    return {
        "trace_id":       trace_id,
        "recommended":    final_recs,
        "relevant":       expected,
        "turn_count":     turn_count,
        "schema_passed":  schema_passed,
        "errors":         all_errors,
        "hallucinations": hallucinations,
    }


# ── HALLUCINATION CHECKER ─────────────────────────────────────────────────────

def check_hallucinations(recommended: list[str], valid_names: set[str]) -> list[str]:
    """Returns list of recommended names NOT in the catalogue."""
    return [
        name for name in recommended
        if name.strip().lower() not in valid_names
    ]


# ── MAIN RUNNER ───────────────────────────────────────────────────────────────

def run_evaluation(
    traces_dir:      str,
    api_url:         str,
    catalogue_path:  str = "app/data/shl_product_catalogue.json",
    delay_seconds:   float = 0.5,
) -> dict:
    """
    Full evaluation run.
    """
    print(f"\n{'='*60}")
    print(f"SHL Assessment API — Evaluation Runner")
    print(f"API URL:     {api_url}")
    print(f"Traces dir:  {traces_dir}")
    print(f"{'='*60}\n")

    try:
        health = requests.get(f"{api_url.rstrip('/')}/health", timeout=120)
        assert health.json().get("status") == "ok"
        print(f"[eval] /health check: PASS\n")
    except Exception as e:
        print(f"[eval] /health check FAILED: {e}")
        sys.exit(1)

    traces      = load_traces(traces_dir)
    if not traces:
        print("[eval] No traces to run.")
        return {}

    valid_names = load_valid_names(catalogue_path)
    print(f"[eval] Loaded {len(traces)} traces | {len(valid_names)} valid catalogue names\n")

    results: list[dict] = []
    for i, trace in enumerate(traces):
        tid = trace.get("trace_id", trace.get("id", f"trace_{i+1}"))
        print(f"[{i+1:02d}/{len(traces):02d}] Replaying trace: {tid}")
        result = replay_conversation(trace, api_url)

        hall = check_hallucinations(result["recommended"], valid_names)
        result["hallucinations"] = hall

        r10  = recall_at_k(result["recommended"], result["relevant"])
        icon = "✅" if r10 >= 0.5 and not hall and result["schema_passed"] else "⚠️ "
        print(f"  {icon}  Recall@10={r10:.2f}  |  Hits={int(r10*len(result['relevant']))}/{len(result['relevant'])}"
              f"  |  Turns={result['turn_count']}  |  Hallucinations={len(hall)}"
              f"  |  Schema={'PASS' if result['schema_passed'] else 'FAIL'}")

        results.append(result)
        time.sleep(delay_seconds)

    recall_results = mean_recall_at_k(results)
    schema_pass_count = sum(1 for r in results if r["schema_passed"])
    total_hallucinations = sum(len(r["hallucinations"]) for r in results)
    total_turns = sum(r["turn_count"] for r in results)

    summary = {
        "mean_recall_at_10":  recall_results["mean_recall_at_k"],
        "hallucination_rate": round(total_hallucinations / max(total_turns, 1), 4),
        "schema_pass_rate":   round(schema_pass_count / len(results), 4),
        "total_traces":       len(results),
        "total_turns":        total_turns,
        "total_hallucinations": total_hallucinations,
        "per_trace_recall":   recall_results["per_trace"],
    }

    print(f"\n{'='*60}")
    print(f"EVALUATION RESULTS")
    print(f"{'='*60}")
    print(f"  Mean Recall@10      : {summary['mean_recall_at_10']:.4f}")
    print(f"  Schema pass rate    : {summary['schema_pass_rate']:.4f}  ({schema_pass_count}/{len(results)} traces)")
    print(f"  Hallucination rate  : {summary['hallucination_rate']:.4f}")
    print(f"{'='*60}\n")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SHL Assessment API Evaluation Runner")
    parser.add_argument("--traces_dir", default="./traces", help="Directory containing traces")
    parser.add_argument("--api_url", default="http://localhost:8000", help="API URL")
    parser.add_argument("--catalogue", default="app/data/shl_product_catalogue.json", help="Catalogue path")
    args = parser.parse_args()

    run_evaluation(
        traces_dir=args.traces_dir,
        api_url=args.api_url,
        catalogue_path=args.catalogue,
    )
