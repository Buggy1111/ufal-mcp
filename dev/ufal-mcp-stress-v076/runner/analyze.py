"""Analyze raw results -> categorize bugs P0-P3 + write BUGS-v076.md.

P0 = crash / hang / data loss
P1 = wrong output (PII leak, broken entity boundaries)
P2 = quality degradation (timeout for normal-size input, missing warnings)
P3 = cosmetic (wrong language detection, edge case output formatting)
"""

from __future__ import annotations

import glob
import json
import os
from collections import defaultdict
from datetime import datetime


RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "raw")
OUT_REPORT = os.path.join(os.path.dirname(__file__), "..", "results", "BUGS-v076.md")


def load_all() -> list[dict]:
    out = []
    for p in sorted(glob.glob(os.path.join(RAW_DIR, "*.json"))):
        with open(p, "r", encoding="utf-8") as f:
            out.append(json.load(f))
    return out


def classify(r: dict) -> tuple[str, str]:
    """Vrati (severity, reason)."""
    s = r["status"]
    note = r["note"]
    cat = r.get("category", r["id"][0] if r.get("id") else "?")
    tool = r.get("tool", "cross-tool")

    if s == "pass" or s == "expected_fail":
        return ("OK", "")

    # error / fail
    if s == "error":
        if "timeout" in note.lower() or "hang" in note.lower():
            # for normal-size: P1 quality (server cant handle real-world size)
            # for >MAX: P3 (expected to fail validation, not timeout)
            text_len = r.get("args_text_len", 0) or len(r.get("args_text_preview", ""))
            if text_len > 200_000:
                return ("P1", f"timeout for {text_len}B (> SOFT_WARN, should err early or chunk)")
            elif text_len > 50_000:
                return ("P1", f"timeout for {text_len}B (large but should work)")
            else:
                return ("P2", f"timeout for {text_len}B (small input)")
        if "crash" in note.lower() or "exception" in note.lower():
            return ("P0", f"runtime crash: {note}")
        return ("P1", note)

    if s == "fail":
        if "PII LEAK" in note:
            return ("P0", note)  # absolutely critical for legal use
        if "expected ValidationError but call succeeded" in note:
            return ("P3", note)
        if "PUA chars passed without warning" in note:
            return ("P2", note)
        return ("P2", note)

    return ("?", note)


def write_report(results: list[dict]) -> None:
    by_sev = defaultdict(list)
    for r in results:
        sev, reason = classify(r)
        if sev == "OK":
            continue
        by_sev[sev].append((r, reason))

    by_tool_total = defaultdict(lambda: defaultdict(int))
    for r in results:
        sev, _ = classify(r)
        by_tool_total[r.get("tool", "cross-tool")][sev] += 1

    lines = []
    lines.append(f"# UFAL MCP v0.7.5 — Stress Test Bug Report (vstup pro v0.7.6)")
    lines.append("")
    lines.append(f"**Datum**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Test suite**: `dev/ufal-mcp-stress-v076/`")
    lines.append(f"**Server**: ÚFAL MFF UK / Univerzita Karlova v Praze")
    lines.append(f"**Verze**: ufal-mcp 0.7.5")
    lines.append("")
    lines.append(f"## Summary")
    lines.append("")
    total = len(results)
    ok = sum(1 for r in results if r["status"] in ("pass", "expected_fail"))
    lines.append(f"- Total tests run: **{total}**")
    lines.append(f"- OK (pass + expected_fail): **{ok}** ({100*ok/total:.0f}%)")
    for sev in ("P0", "P1", "P2", "P3"):
        n = len(by_sev.get(sev, []))
        if n:
            lines.append(f"- **{sev}**: {n}")
    lines.append("")

    lines.append("## Per-tool breakdown")
    lines.append("")
    lines.append("| Nástroj | OK | P0 | P1 | P2 | P3 |")
    lines.append("|---|---|---|---|---|---|")
    for tool in sorted(by_tool_total):
        d = by_tool_total[tool]
        lines.append(f"| `{tool}` | {d.get('OK',0)} | {d.get('P0',0)} | {d.get('P1',0)} | {d.get('P2',0)} | {d.get('P3',0)} |")
    lines.append("")

    severity_titles = {
        "P0": "🔴 P0 — Crash / PII leak / data loss",
        "P1": "🟠 P1 — Wrong output / unresponsive for real-world size",
        "P2": "🟡 P2 — Quality degradation",
        "P3": "🟢 P3 — Cosmetic / edge case",
    }
    for sev in ("P0", "P1", "P2", "P3"):
        items = by_sev.get(sev, [])
        if not items:
            continue
        lines.append(f"## {severity_titles[sev]}")
        lines.append("")
        for r, reason in items:
            lines.append(f"### [{r['id']}] `{r.get('tool', 'cross-tool')}` — {r.get('desc', r.get('note', ''))}")
            lines.append("")
            lines.append(f"**Reason**: {reason}")
            lines.append("")
            preview = r.get("args_text_preview", "") or ""
            preview_len = r.get("args_text_len", len(preview)) or len(preview)
            if preview_len > 200:
                lines.append(f"**Input** ({preview_len}B, prvních 200 znaků):")
            else:
                lines.append(f"**Input** ({preview_len}B):")
            # truncate display only
            display = preview[:200].replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
            lines.append("```")
            lines.append(display)
            lines.append("```")
            args_keys = r.get("args_keys") or []
            if args_keys:
                lines.append(f"**Args**: `{json.dumps({k: (r['args_text_preview'] or '')[:60] if k == 'text' else '...' for k in args_keys}, ensure_ascii=False)}`")
            lines.append("")
            lines.append(f"**Status**: `{r['status']}`  |  **Note**: {r['note']}")
            lines.append("")
            call = r.get("call") or {}
            if call.get("elapsed_s") is not None:
                lines.append(f"**Elapsed**: {call['elapsed_s']}s")
            if call.get("exception"):
                lines.append(f"**Exception**: `{call['exception']}`")
            if call.get("error"):
                lines.append(f"**JSON-RPC error**: `{json.dumps(call['error'], ensure_ascii=False)[:300]}`")
            stderr_tail = (call.get("stderr_tail") or "").strip()
            if stderr_tail:
                lines.append("**stderr tail**:")
                lines.append("```")
                lines.append(stderr_tail[-1000:])
                lines.append("```")
            pp = r.get("payload_preview")
            if pp:
                lines.append("**Payload preview**:")
                lines.append("```json")
                lines.append(json.dumps(pp, ensure_ascii=False, indent=2)[:1500])
                lines.append("```")
            lines.append("")
            lines.append("---")
            lines.append("")

    # Patterns / themes section
    lines.append("## Patterns observed")
    lines.append("")
    lines.append("(plní se manuálně po review)")
    lines.append("")

    # Suggested fixes
    lines.append("## Suggested fixes for v0.7.6")
    lines.append("")
    lines.append("(plní se manuálně po review)")
    lines.append("")

    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {OUT_REPORT}")


if __name__ == "__main__":
    results = load_all()
    print(f"Loaded {len(results)} results")
    write_report(results)
