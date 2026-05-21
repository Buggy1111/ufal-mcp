"""Cross-tool tests — H category extension.

Pravy idempotence + round-trip + chain checks vyzaduji 2+ volani s pouzitim
predchoziho vystupu. To delam tady mimo hlavni runner.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from stdio_client import UfalMcpClient, extract_tool_payload


OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "raw")


async def chain_anonymize_idempotence(client):
    """H1: anonymize(anonymize(x)) == anonymize(x) (placeholder mode)."""
    text = "Pan Jiří Pluhařík (RČ 800312/1234) bydlí na ulici Hlavní 5 v Ostravě. Tel: 777 123 456."
    r1 = await client.call_tool("anonymize", {"text": text, "placeholder_mode": True})
    p1 = extract_tool_payload(r1)
    if not p1 or "anonymized" not in p1:
        return {"id": "H1_idempotence", "status": "error", "note": "pass 1 failed", "p1": p1}
    out1 = p1["anonymized"]
    r2 = await client.call_tool("anonymize", {"text": out1, "placeholder_mode": True})
    p2 = extract_tool_payload(r2)
    if not p2 or "anonymized" not in p2:
        return {"id": "H1_idempotence", "status": "error", "note": "pass 2 failed", "p2": p2}
    out2 = p2["anonymized"]
    ok = out1 == out2
    return {
        "id": "H1_idempotence",
        "status": "pass" if ok else "fail",
        "note": "idempotent" if ok else "anonymize(anonymize(x)) != anonymize(x)",
        "pass1_output": out1,
        "pass2_output": out2,
        "pass1_replacements": len(p1.get("replacements", [])),
        "pass2_replacements": len(p2.get("replacements", [])),
    }


async def chain_translate_roundtrip(client):
    """H2: cs -> en -> cs round-trip."""
    text = "Soud rozhodl o povinnosti žalovaného uhradit žalobci 50 000 Kč."
    r1 = await client.call_tool("translate_text", {"text": text, "src": "cs", "tgt": "en"}, timeout=120.0)
    p1 = extract_tool_payload(r1)
    if not p1 or "translated" not in p1:
        return {"id": "H2_roundtrip", "status": "error", "note": "cs->en failed", "p1": p1}
    en = p1["translated"]
    r2 = await client.call_tool("translate_text", {"text": en, "src": "en", "tgt": "cs"}, timeout=120.0)
    p2 = extract_tool_payload(r2)
    if not p2 or "translated" not in p2:
        return {"id": "H2_roundtrip", "status": "error", "note": "en->cs failed", "p2": p2}
    cs_back = p2["translated"]
    # crude semantic check
    keywords = ["soud", "žalovan", "žalob", "50"]
    found = [k for k in keywords if k.lower() in cs_back.lower()]
    return {
        "id": "H2_roundtrip",
        "status": "pass" if len(found) >= 3 else "fail",
        "note": f"keywords preserved {len(found)}/{len(keywords)}",
        "original": text,
        "en": en,
        "back": cs_back,
        "keywords_found": found,
    }


async def chain_anonymize_then_extract(client):
    """H3: extract_entities na anonymized output — placeholdery se nemaji najit jako CZ entity (osoby)."""
    text = "Pan Jiří Pluhařík (Ostrava) podepsal smlouvu s ABC s.r.o."
    r1 = await client.call_tool("anonymize", {"text": text, "placeholder_mode": True})
    p1 = extract_tool_payload(r1)
    if not p1 or "anonymized" not in p1:
        return {"id": "H3_chain", "status": "error", "note": "anonymize failed"}
    anonymized = p1["anonymized"]
    r2 = await client.call_tool("extract_entities", {"text": anonymized})
    p2 = extract_tool_payload(r2)
    if not p2 or "entities" not in p2:
        return {"id": "H3_chain", "status": "error", "note": "extract failed"}
    # check if placeholders were detected as entities
    placeholder_entities = [e for e in p2["entities"] if any(
        ph in e.get("text", "") for ph in ("OSOBA", "MESTO", "FIRMA", "TELEFON", "OSOBA1")
    )]
    return {
        "id": "H3_chain",
        "status": "pass" if not placeholder_entities else "fail",
        "note": f"{len(placeholder_entities)} placeholdery zachyceny jako entity" if placeholder_entities else "placeholdery nedetekovany jako entity",
        "anonymized": anonymized,
        "entities_count": len(p2["entities"]),
        "placeholder_entities": placeholder_entities,
    }


async def chain_correct_then_anonymize(client):
    """H4: diacritics first, then anonymize — porovnani s anonymize-only."""
    text = "Jiri Pluharik bydli v Ostrave, tel 777 123 456."
    # path A: correct -> anonymize
    r1 = await client.call_tool("correct_text", {"text": text, "mode": "diacritics"})
    p1 = extract_tool_payload(r1)
    if not p1 or "corrected" not in p1:
        return {"id": "H4_order", "status": "error", "note": "diacritics failed"}
    corrected = p1["corrected"]
    rA = await client.call_tool("anonymize", {"text": corrected, "placeholder_mode": True})
    pA = extract_tool_payload(rA)
    # path B: anonymize directly
    rB = await client.call_tool("anonymize", {"text": text, "placeholder_mode": True})
    pB = extract_tool_payload(rB)
    if not pA or not pB:
        return {"id": "H4_order", "status": "error", "note": "anonymize failed"}
    # count placeholders in each — better path should have >= placeholders
    repA = len(pA.get("replacements", []))
    repB = len(pB.get("replacements", []))
    note = f"correct-then-anon: {repA} replacements vs anon-only: {repB} replacements"
    return {
        "id": "H4_order",
        "status": "pass",  # informational
        "note": note,
        "diacritics_output": corrected,
        "path_A_anonymized": pA.get("anonymized"),
        "path_B_anonymized": pB.get("anonymized"),
        "replacements_A": repA,
        "replacements_B": repB,
    }


async def chain_entity_count_pre_post_anonymize(client):
    """H5: entity count pred a po anonymize — pocet osobnich entit by mel klesnout."""
    text = "Pan Jiří Pluhařík z Ostravy podal žalobu na ABC s.r.o."
    r_before = await client.call_tool("extract_entities", {"text": text})
    p_before = extract_tool_payload(r_before)
    r_anon = await client.call_tool("anonymize", {"text": text, "placeholder_mode": True})
    p_anon = extract_tool_payload(r_anon)
    if not p_anon:
        return {"id": "H5_count", "status": "error", "note": "anonymize failed"}
    r_after = await client.call_tool("extract_entities", {"text": p_anon["anonymized"]})
    p_after = extract_tool_payload(r_after)
    n_before = len(p_before.get("entities", []))
    n_after = len(p_after.get("entities", []))
    return {
        "id": "H5_count",
        "status": "pass",  # informational
        "note": f"before={n_before} after={n_after}",
        "before_text": text,
        "after_text": p_anon["anonymized"],
        "before_count": n_before,
        "after_count": n_after,
        "before_entities": p_before.get("entities", []),
        "after_entities": p_after.get("entities", []),
    }


async def main():
    print("=== Cross-tool chain tests ===")
    async with UfalMcpClient() as client:
        results = []
        for fn in (
            chain_anonymize_idempotence,
            chain_translate_roundtrip,
            chain_anonymize_then_extract,
            chain_correct_then_anonymize,
            chain_entity_count_pre_post_anonymize,
        ):
            print(f"\n--- {fn.__name__} ---")
            try:
                r = await fn(client)
            except Exception as e:
                r = {"id": fn.__name__, "status": "error", "note": f"exception: {type(e).__name__}: {e}"}
            print(f"  status={r['status']} note={r['note']}")
            results.append(r)
            p = os.path.join(OUT_DIR, f"{r['id']}.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump(r, f, ensure_ascii=False, indent=2, default=str)

    print("\n=== Summary ===")
    for r in results:
        print(f"  {r['id']:30} {r['status']:10} {r['note'][:80]}")


if __name__ == "__main__":
    asyncio.run(main())
