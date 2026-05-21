"""Multilingual test — testuje UFAL MCP napric jazyky.

Pokryti:
  - extract_entities (NameTag UNER multilingual): vsechny jazyky
  - analyze_morphology (UDPipe 961 modelu, auto-detect): vsechny jazyky
  - translate_text (Charles Translator): jen cs/en/fr/de/pl/ru/uk/hi
  - anonymize (MasKIT, CZ-only): testovano pro degradaci (mel by projit, ale ne CZ-style)
  - check_readability (PONK, CZ-only): skip / quick degradation check
  - correct_text (Korektor, CZ-only): skip / quick degradation check

Per-language report:
  - detected language (UDPipe + NameTag agreement)
  - entity count + top types
  - token / sentence count
  - translation length ratio (cs/en/fr/de/pl/ru/uk/hi only)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from stdio_client import UfalMcpClient, extract_tool_payload


CORPUS_DIR = os.path.join(os.path.dirname(__file__), "..", "corpus", "multilingual")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "multilingual")
os.makedirs(OUT_DIR, exist_ok=True)


# Jazyky v korpusu + ocekavany detection + Charles support
LANGUAGES = [
    # code, expected_lang_name, charles_supported
    ("sk", "slovak", False),
    ("en", "english", True),
    ("de", "german", True),
    ("pl", "polish", True),
    ("uk", "ukrainian", True),
    ("ru", "russian", True),
    ("fr", "french", True),
    ("hi", "hindi", True),
    ("es", "spanish", False),
    ("it", "italian", False),
    ("ar", "arabic", False),
]


async def test_language(client: UfalMcpClient, code: str, expected_lang: str, charles_ok: bool) -> dict:
    path = os.path.join(CORPUS_DIR, f"{code}.txt")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    result: dict = {
        "lang_code": code,
        "expected_lang": expected_lang,
        "text_bytes": len(text.encode("utf-8")),
        "text_chars": len(text),
        "charles_supported": charles_ok,
    }
    print(f"\n=== {code.upper()} ({expected_lang}, {result['text_bytes']}B) ===")

    # 1. extract_entities (auto-detect)
    print("  >> extract_entities...", end=" ", flush=True)
    ent_info: dict = {}
    try:
        t0 = time.time()
        r = await client.call_tool("extract_entities", {"text": text, "model": "auto"}, timeout=60.0)
        elapsed = time.time() - t0
        p = extract_tool_payload(r)
        ent_info = {"ok": r.ok, "elapsed_s": round(elapsed, 2)}
        if isinstance(p, dict):
            ents = p.get("entities", [])
            ent_info["count"] = len(ents)
            ent_info["model"] = p.get("model")
            ent_info["detected_language"] = p.get("detected_language")
            from collections import Counter
            types = Counter(e.get("label", e.get("type", "?")) for e in ents if isinstance(e, dict))
            ent_info["top_types"] = dict(types.most_common(5))
            ent_info["sample_entities"] = [
                {"text": e.get("text", ""), "type": e.get("label", e.get("type", "?"))}
                for e in ents[:8] if isinstance(e, dict)
            ]
        print(f"ok={r.ok} entities={ent_info.get('count', '?')} detected={ent_info.get('detected_language', '?')} ({elapsed:.1f}s)")
    except Exception as e:
        ent_info["error"] = f"{type(e).__name__}: {e}"
        print(f"EXCEPTION {ent_info['error']}")
    result["extract_entities"] = ent_info

    # 2. analyze_morphology (auto-detect)
    print("  >> analyze_morphology...", end=" ", flush=True)
    morph_info: dict = {}
    try:
        t0 = time.time()
        r = await client.call_tool("analyze_morphology", {"text": text, "model": "auto"}, timeout=60.0)
        elapsed = time.time() - t0
        p = extract_tool_payload(r)
        morph_info = {"ok": r.ok, "elapsed_s": round(elapsed, 2)}
        if isinstance(p, dict):
            morph_info["token_count"] = p.get("token_count")
            morph_info["sentence_count"] = p.get("sentence_count")
            morph_info["model"] = p.get("model")
            morph_info["detected_language"] = p.get("detected_language")
            sents = p.get("sentences", [])
            if sents:
                first = sents[0]
                if isinstance(first, dict):
                    first_tokens = first.get("tokens", [])
                elif isinstance(first, list):
                    first_tokens = first
                else:
                    first_tokens = []
                morph_info["sample_tokens"] = [
                    {"text": t.get("text") or t.get("form"),
                     "lemma": t.get("lemma"),
                     "upos": t.get("upos") or t.get("pos")}
                    for t in first_tokens[:6] if isinstance(t, dict)
                ]
        print(f"ok={r.ok} tokens={morph_info.get('token_count', '?')} model={morph_info.get('model', '?')} ({elapsed:.1f}s)")
    except Exception as e:
        morph_info["error"] = f"{type(e).__name__}: {e}"
        print(f"EXCEPTION {morph_info['error']}")
    result["analyze_morphology"] = morph_info

    # 3. translate_text (only for Charles-supported)
    # Charles ma 17 par s pivoty CZ (cs<->en/uk/ru) a EN (en<->fr/de/pl/ru, en->hi).
    # Pro lang->cs ktere nejsou v primem paru, pivot pres EN: lang->en->cs (2 volani).
    DIRECT_TO_CS = {"en", "uk", "ru"}
    EN_PIVOT_NEEDED = {"fr", "de", "pl", "hi"}

    if charles_ok and code != "cs":
        tr_info: dict = {}
        try:
            excerpt = text[:1500]
            if code in DIRECT_TO_CS:
                print(f"  >> translate {code}->cs (direct)...", end=" ", flush=True)
                t0 = time.time()
                r = await client.call_tool(
                    "translate_text", {"text": excerpt, "src": code, "tgt": "cs"}, timeout=90.0,
                )
                elapsed = time.time() - t0
                p = extract_tool_payload(r)
                tr_info = {"ok": r.ok, "elapsed_s": round(elapsed, 2), "excerpt_chars": len(excerpt), "path": "direct"}
                if isinstance(p, dict):
                    tr_info["translated_chars"] = p.get("output_chars")
                    tr_info["pair"] = p.get("pair")
                    tr_info["translated_excerpt"] = (p.get("translated") or "")[:300]
                print(f"ok={r.ok} chars_out={tr_info.get('translated_chars', '?')} ({elapsed:.1f}s)")
            elif code in EN_PIVOT_NEEDED:
                # 2-step pivot: lang -> en -> cs
                print(f"  >> translate {code}->en->cs (EN pivot)...", end=" ", flush=True)
                t0 = time.time()
                r1 = await client.call_tool(
                    "translate_text", {"text": excerpt, "src": code, "tgt": "en"}, timeout=90.0,
                )
                p1 = extract_tool_payload(r1)
                en_text = ""
                if isinstance(p1, dict):
                    en_text = p1.get("translated", "")
                if not en_text:
                    tr_info = {"ok": False, "elapsed_s": round(time.time()-t0, 2),
                               "path": "en-pivot", "step1_failed": True}
                else:
                    r2 = await client.call_tool(
                        "translate_text", {"text": en_text[:1500], "src": "en", "tgt": "cs"}, timeout=90.0,
                    )
                    p2 = extract_tool_payload(r2)
                    elapsed = time.time() - t0
                    tr_info = {"ok": r2.ok, "elapsed_s": round(elapsed, 2), "excerpt_chars": len(excerpt),
                               "path": "en-pivot"}
                    if isinstance(p2, dict):
                        tr_info["translated_chars"] = p2.get("output_chars")
                        tr_info["pair"] = f"{code}->en->cs"
                        tr_info["intermediate_en_excerpt"] = en_text[:200]
                        tr_info["translated_excerpt"] = (p2.get("translated") or "")[:300]
                print(f"ok={tr_info.get('ok')} chars_out={tr_info.get('translated_chars', '?')} ({tr_info['elapsed_s']}s)")
        except Exception as e:
            tr_info["error"] = f"{type(e).__name__}: {e}"
            print(f"EXCEPTION {tr_info['error']}")
        result["translate_text"] = tr_info
    else:
        result["translate_text"] = {"skipped": "not supported by Charles Translator"}

    # 4. CZ-only tools degradation (quick check, no full output)
    print("  >> anonymize (CZ-only, degradation test)...", end=" ", flush=True)
    anon_info: dict = {}
    try:
        t0 = time.time()
        r = await client.call_tool(
            "anonymize", {"text": text[:1000], "placeholder_mode": True}, timeout=60.0,
        )
        elapsed = time.time() - t0
        p = extract_tool_payload(r)
        anon_info = {"ok": r.ok, "elapsed_s": round(elapsed, 2)}
        if isinstance(p, dict):
            anon_info["replacements"] = len(p.get("replacements", []))
            anon_info["sources"] = p.get("sources", {})
        print(f"ok={r.ok} replacements={anon_info.get('replacements', '?')} ({elapsed:.1f}s)")
    except Exception as e:
        anon_info["error"] = f"{type(e).__name__}: {e}"
        print(f"EXCEPTION {anon_info['error']}")
    result["anonymize"] = anon_info

    return result


def write_summary(all_results: list[dict]) -> None:
    """Generate human-readable markdown summary."""
    lines = ["# Multilingual test — ÚFAL MCP", ""]
    lines.append(f"**Datum**: {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Languages tested**: {len(all_results)}")
    lines.append("")
    lines.append("## Per-language summary")
    lines.append("")
    lines.append("| Lang | Bytes | Entities | Lang detected | Tokens | UDPipe model | Translate (cs) |")
    lines.append("|---|---:|---:|---|---:|---|---|")
    for r in all_results:
        e = r["extract_entities"]
        m = r["analyze_morphology"]
        t = r.get("translate_text", {})
        tr_str = "—" if t.get("skipped") else f"{t.get('elapsed_s', '?')}s / {t.get('translated_chars', '?')} chars"
        lines.append(
            f"| {r['lang_code']} | {r['text_bytes']} | {e.get('count', '?')} | "
            f"{e.get('detected_language', m.get('detected_language', '?'))} | "
            f"{m.get('token_count', '?')} | "
            f"`{m.get('model', '?')}` | {tr_str} |"
        )
    lines.append("")
    lines.append("## Per-language detail")
    lines.append("")
    for r in all_results:
        lines.append(f"### {r['lang_code']} — {r['expected_lang']}")
        lines.append("")
        e = r["extract_entities"]
        lines.append(f"- **extract_entities**: {e.get('count', '?')} entities, model `{e.get('model', '?')}`, detected `{e.get('detected_language', '?')}`")
        if e.get("top_types"):
            tt = ", ".join(f"{k}={v}" for k, v in e["top_types"].items())
            lines.append(f"  - Top types: {tt}")
        if e.get("sample_entities"):
            lines.append("  - Sample entities:")
            for s in e["sample_entities"][:5]:
                lines.append(f"    - `{s.get('text', '')}` ({s.get('type', '?')})")
        m = r["analyze_morphology"]
        lines.append(f"- **analyze_morphology**: {m.get('token_count', '?')} tokens, {m.get('sentence_count', '?')} sentences, model `{m.get('model', '?')}`")
        if m.get("sample_tokens"):
            lines.append("  - First-sentence sample tokens:")
            for t in m["sample_tokens"][:5]:
                lines.append(f"    - `{t.get('text')}` → lemma `{t.get('lemma')}` ({t.get('upos')})")
        t = r.get("translate_text", {})
        if t.get("skipped"):
            lines.append(f"- **translate_text**: skipped — {t['skipped']}")
        else:
            lines.append(f"- **translate_text** ({r['lang_code']}→cs): {t.get('translated_chars', '?')} chars in {t.get('elapsed_s', '?')}s, pair `{t.get('pair', '?')}`")
            if t.get("translated_excerpt"):
                excerpt = t["translated_excerpt"].replace("\n", " ")[:200]
                lines.append(f"  - Translated excerpt: *{excerpt}...*")
        a = r["anonymize"]
        lines.append(f"- **anonymize** (CZ-only, degradation test on first 1000B): ok={a.get('ok')}, {a.get('replacements', '?')} replacements")
        lines.append("")

    p = os.path.join(OUT_DIR, "MULTILINGUAL-TEST.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nReport: {p}")


async def main():
    print(f"=== UFAL MCP — Multilingual test ({len(LANGUAGES)} languages) ===\n")
    all_results: list[dict] = []
    async with UfalMcpClient() as client:
        for code, expected, charles_ok in LANGUAGES:
            try:
                r = await test_language(client, code, expected, charles_ok)
            except Exception as e:
                print(f"  EXCEPTION: {type(e).__name__}: {e}")
                r = {"lang_code": code, "expected_lang": expected, "error": str(e)}
            all_results.append(r)
            with open(os.path.join(OUT_DIR, f"{code}.json"), "w", encoding="utf-8") as f:
                json.dump(r, f, ensure_ascii=False, indent=2, default=str)

    with open(os.path.join(OUT_DIR, "all.json"), "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    write_summary(all_results)
    print(f"\n=== DONE — {len(all_results)} languages tested ===")


if __name__ == "__main__":
    asyncio.run(main())
