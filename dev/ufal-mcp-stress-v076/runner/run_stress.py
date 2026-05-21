"""Main stress runner — projede vsechny test cases a ulozi vysledky.

Usage:
    python runner/run_stress.py                  # vse
    python runner/run_stress.py --category E     # jen kategorie E
    python runner/run_stress.py --tool anonymize # jen anonymize
    python runner/run_stress.py --id E1          # jen jeden test
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

# allow direct script run
sys.path.insert(0, os.path.dirname(__file__))

from stdio_client import UfalMcpClient, CallResult, extract_tool_payload
from test_cases import all_tests, by_category
from verifiers import verify


RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "raw")
os.makedirs(RESULTS_DIR, exist_ok=True)


def _serialize_call(r: CallResult) -> dict:
    return {
        "ok": r.ok,
        "elapsed_s": round(r.elapsed_s, 3),
        "response": r.response,
        "error": r.error,
        "exception": r.exception,
        "stderr_tail": r.stderr_tail,
    }


async def _run_one(client: UfalMcpClient, test: dict) -> dict:
    timeout = test.get("timeout", 60.0)
    result = await client.call_tool(test["tool"], test["args"], timeout=timeout)
    payload = extract_tool_payload(result)
    status, note = verify(test, result, payload)
    return {
        "id": test["id"],
        "category": test["id"][0],
        "tool": test["tool"],
        "desc": test["desc"],
        "args_keys": list(test["args"].keys()),
        "args_text_preview": test["args"].get("text", "")[:200],
        "args_text_len": len(test["args"].get("text", "")),
        "status": status,
        "note": note,
        "call": _serialize_call(result),
        "payload_preview": _preview_payload(payload),
    }


def _preview_payload(payload) -> Any:
    """Compact preview pro JSON soubor — full payload je v call.response."""
    if payload is None:
        return None
    if isinstance(payload, str):
        return payload[:500]
    if isinstance(payload, dict):
        # vyber zajimave klice
        out = {}
        for k in ("anonymized", "translated", "corrected", "model", "detected_language",
                  "count", "warnings", "sources", "replacements", "metrics"):
            if k in payload:
                v = payload[k]
                if isinstance(v, str):
                    out[k] = v[:500]
                elif isinstance(v, list):
                    out[k] = v[:10] if len(v) <= 10 else f"[{len(v)} items] {v[:3]}..."
                else:
                    out[k] = v
        # entity count
        if "entities" in payload and isinstance(payload["entities"], list):
            out["entities_count"] = len(payload["entities"])
            out["entities_sample"] = payload["entities"][:5]
        return out
    return repr(payload)[:500]


async def _run_concurrent_group(client: UfalMcpClient, tests: list[dict]) -> list[dict]:
    """Spusti vsechny testy ze skupiny paralelne."""
    return await asyncio.gather(*(_run_one(client, t) for t in tests))


async def run_matrix(tests: list[dict], save_individual: bool = True) -> list[dict]:
    print(f"=== UFAL MCP stress v0.7.6 — {len(tests)} tests ===")
    print(f"Started: {datetime.now().isoformat(timespec='seconds')}")

    # separuj concurrent groups
    sequential = [t for t in tests if not t.get("concurrent_group")]
    by_group = defaultdict(list)
    for t in tests:
        if t.get("concurrent_group"):
            by_group[t["concurrent_group"]].append(t)

    results: list[dict] = []

    async with UfalMcpClient(debug=False) as client:
        # sequential first
        for i, t in enumerate(sequential, 1):
            print(f"[{i}/{len(sequential)}] {t['id']:6} {t['tool']:22} {t['desc'][:60]}", end=" ", flush=True)
            try:
                r = await _run_one(client, t)
            except Exception as e:
                r = {
                    "id": t["id"], "category": t["id"][0], "tool": t["tool"],
                    "desc": t["desc"], "status": "error",
                    "note": f"runner exception: {type(e).__name__}: {e}",
                    "call": None, "payload_preview": None,
                }
            print(f"-> {r['status']:14} ({r.get('call', {}).get('elapsed_s', '?')}s) {r['note'][:60]}")
            results.append(r)
            if save_individual:
                _save_one(r)

        # concurrent groups
        for gname, group in by_group.items():
            print(f"\n--- Concurrent group {gname} ({len(group)} parallel) ---")
            t0 = time.time()
            gres = await _run_concurrent_group(client, group)
            elapsed = time.time() - t0
            for r in gres:
                print(f"  {r['id']:10} -> {r['status']:14} ({r.get('call', {}).get('elapsed_s', '?')}s) {r['note'][:60]}")
                results.append(r)
                if save_individual:
                    _save_one(r)
            print(f"  group {gname}: {elapsed:.2f}s wall")

    return results


def _save_one(r: dict) -> None:
    p = os.path.join(RESULTS_DIR, f"{r['id']}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=2, default=str)


def summarize(results: list[dict]) -> None:
    by_status = defaultdict(int)
    by_cat_status = defaultdict(lambda: defaultdict(int))
    failures = []
    for r in results:
        by_status[r["status"]] += 1
        by_cat_status[r["category"]][r["status"]] += 1
        if r["status"] in ("fail", "error"):
            failures.append(r)

    print("\n=== SUMMARY ===")
    print(f"Total: {len(results)}")
    for s in ("pass", "expected_fail", "fail", "error"):
        if by_status[s]:
            print(f"  {s}: {by_status[s]}")

    print("\nBy category:")
    for cat in sorted(by_cat_status):
        cats = by_cat_status[cat]
        line = " ".join(f"{k}={v}" for k, v in cats.items())
        print(f"  {cat}: {line}")

    if failures:
        print(f"\n=== {len(failures)} FAILURES / ERRORS ===")
        for f in failures:
            print(f"  [{f['status']}] {f['id']:6} {f['tool']:22} {f['note'][:120]}")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", help="jen kategorie A-I")
    ap.add_argument("--tool", help="jen jeden nastroj")
    ap.add_argument("--id", help="jen jeden test ID")
    args = ap.parse_args()

    tests = all_tests()
    if args.category:
        tests = by_category(args.category)
    if args.tool:
        tests = [t for t in tests if t["tool"] == args.tool]
    if args.id:
        tests = [t for t in tests if t["id"] == args.id]

    if not tests:
        print("Nothing to run.")
        return

    results = await run_matrix(tests)
    summarize(results)

    # save aggregate
    agg = os.path.join(os.path.dirname(RESULTS_DIR), "all_results.json")
    with open(agg, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nAggregate saved: {agg}")


if __name__ == "__main__":
    asyncio.run(main())
