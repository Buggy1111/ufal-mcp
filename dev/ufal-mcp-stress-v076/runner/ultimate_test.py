"""Ultimate test — projde komplexni cross-sektorovy spis vsemi 6 nastroji.

Pokryti: pravo (rozsudek) + medicina (propousteci zprava) + veda (znalecky posudek).
Vsechny varianty PII typu z pohledu vedcu, pravniku, lekaru.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from stdio_client import UfalMcpClient, extract_tool_payload


SPIS_PATH = os.path.join(os.path.dirname(__file__), "..", "corpus", "ULTIMATE_SPIS.txt")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "ultimate")
os.makedirs(OUT_DIR, exist_ok=True)


# PII inventory — co by mel anonymize chytit, vse v puvodnim textu
PII_INVENTORY = {
    # RC
    "800312/1234": "rodné číslo (slash)",
    "7507051234": "rodné číslo (compact)",
    "855218 4567": "rodné číslo (space)",
    "65-11-18/5432": "rodné číslo (dashed)",
    "580412 1234": "rodné číslo (space, scientist)",
    # č.ú. CZ formats
    "19-2000145399/0800": "č.ú. (prefix-base/bank)",
    "35-1234567890/0100": "č.ú. (prefix advokát)",
    "27-1234567890/0300": "č.ú. (prefix nemocnice)",
    "1234567890/2010": "č.ú. (no prefix)",
    "6015-1234567/0710": "č.ú. (depozit soudu)",
    # IBAN
    "CZ65 0800 0000 1920 0014 5399": "IBAN",
    # IČO
    "12345678": "IČO advokát",
    "28765432": "IČO ABC Manufacturing",
    "00843989": "IČO FNO",
    # DIČ
    "CZ12345678": "DIČ advokát",
    "CZ28765432": "DIČ ABC",
    "CZ00843989": "DIČ FNO",
    # Email
    "cerny.advokat@example.cz": "email advokát",
    "tomas.novak@abc-manufacturing.cz": "email firma",
    "jiri.pluharik@example.cz": "email pacient",
    "info@abc-manufacturing.cz": "email firma 2",
    "svoboda@fno.cz": "email lékař",
    "karel.bily@matfyz.cuni.cz": "email vědec",
    "kbily@example.org": "email vědec 2",
    "eva.hladka@matfyz.cuni.cz": "email Hladká",
    "mirovsky@ufal.mff.cuni.cz": "email Mírovský",
    "valach.lukas@gmail.com": "email Valach",
    "vesela.marta@seznam.cz": "email Veselá",
    "p.modry@centrum.cz": "email Modrý",
    "bily@matfyz.cuni.cz": "email Bílý",
    "kratka@ksoud.justice.cz": "email kancelář",
    # Telefony
    "+420 596 153 111": "telefon soud",
    "777 123 456": "telefon advokát",
    "+420 603 987 654": "telefon firma",
    "728 18 18 10": "telefon mobil 3-2-2-2",
    "602 456 789": "telefon znalec",
    "597 372 100": "telefon lékař",
    "597 372 200": "telefon ambulance",
    "605 111 222": "telefon Valach",
    "596 153 220": "telefon kancelář",
    # Datové schránky
    "ud4abqd": "datovka soud",
    "x9k4lm2": "datovka firma",
    "ab7c2dx": "datovka advokát",
    "gh4nqpr": "datovka FNO",
    "pl3jx5q": "datovka Pluhařík",
    # Č.j. / Sp. zn.
    "12 C 187/2024-45": "č.j. hlavní",
    "12 C 187/2024": "sp. zn.",
    "KZ-2024/187": "č.j. posudku",
    # IBAN BIC
    "CEKOCZPP": "SWIFT",
    # ORCID / Researcher ID
    "0000-0002-1825-0097": "ORCID",
    "AAB-1234-5678": "Researcher ID",
    # MKN-10 diagnózy (probably should NOT be anonymized — code, not PII)
    # Tady jen orientacne
    # Adresy (street + city + PSC)
    "Hlavní 254/15": "ulice",
    "Slezská 47": "ulice",
    "Stodolní 21": "ulice",
    "Průmyslová 1024/8": "ulice",
    "Mírová 12": "ulice",
    "Husova 7": "ulice",
    "17. listopadu 1790/5": "ulice",
    "Havlíčkovo nábřeží 1835/34": "ulice",
    "Malostranské náměstí 25": "ulice",
    # Jména
    "Jiří Pluhařík": "osoba 1",
    "Tomáš Novák": "osoba 2",
    "Marta Veselá": "osoba 3",
    "Pavel Modrý": "osoba 4",
    "Jana Novotná": "soudkyně",
    "Petr Černý": "advokát",
    "Karel Svoboda": "lékař",
    "Tomáš Bílý": "konzultant",
    "Karel Bílý": "znalec",
    "Eva Hladká": "Hladká ÚFAL",
    "Jan Mírovský": "Mírovský",
    "Lukáš Valach": "Valach",
    "Petra Krátká": "kancelář",
    # === SEKCE E — Bank/Commerce ===
    "4539 1488 0343 6467": "platební karta Visa",
    "1234567890": "VS faktury",  # also as VS
    "240412": "var. symbol odchozí",
    "0308": "konst. symbol",  # short, OK as KS
    # === SEKCE F — Real estate ===
    "List vlastnictví č. 4521": "LV vlastníka (unikátní kontext)",
    "LV č. 4520": "LV souseda",
    "LV 4522": "LV města",
    "p.č. 1234/5": "parcela 1 (s prefixem)",
    "parc. č. 1234/6": "parcela 2 (s prefixem)",
    "p.č. 1234/4": "parcela soused (s prefixem)",
    "parcela 1234/7": "parcela město (s prefixem)",
    # === SEKCE G — Insurance/Auto ===
    "8765432101": "č. pojistné smlouvy",
    "ČP-2024-187654": "č. pojistky",
    "5T9 1234": "SPZ",
    "TMBAA9NE3M0123456": "VIN",
    "AB1234567": "č. TP",
    # === SEKCE H — Notary ===
    "NZ 234/2024": "notářský zápis",
    "123456789": "č. OP",
    "66054321": "IČO notář",
    "not9zx2": "datovka notář",
    "Marie Krásná": "notářka",
    # === SEKCE I — Education ===
    "UČO: 12345678": "UČO student (unikátní kontext)",
    "Studijní číslo: 87654321": "studijní číslo (unikátní kontext)",
    "S 410 002 123456 7": "ISIC",
}


async def run_anonymize(client, text):
    print(">> anonymize (placeholder_mode=True)...", flush=True)
    t0 = time.time()
    r = await client.call_tool(
        "anonymize",
        {"text": text, "placeholder_mode": True},
        timeout=180.0,
    )
    elapsed = time.time() - t0
    p = extract_tool_payload(r)
    print(f"   ok={r.ok} elapsed={elapsed:.1f}s replacements={len(p.get('replacements', [])) if isinstance(p, dict) else '?'}")
    return r, p


async def run_extract(client, text):
    print(">> extract_entities (CZ CNEC)...", flush=True)
    t0 = time.time()
    r = await client.call_tool("extract_entities", {"text": text}, timeout=180.0)
    elapsed = time.time() - t0
    p = extract_tool_payload(r)
    n = len(p.get("entities", [])) if isinstance(p, dict) else "?"
    print(f"   ok={r.ok} elapsed={elapsed:.1f}s entities={n}")
    return r, p


async def run_morphology(client, text):
    print(">> analyze_morphology (UDPipe)...", flush=True)
    t0 = time.time()
    r = await client.call_tool("analyze_morphology", {"text": text}, timeout=180.0)
    elapsed = time.time() - t0
    p = extract_tool_payload(r)
    tc = p.get("token_count", "?") if isinstance(p, dict) else "?"
    sc = p.get("sentence_count", "?") if isinstance(p, dict) else "?"
    print(f"   ok={r.ok} elapsed={elapsed:.1f}s tokens={tc} sentences={sc}")
    return r, p


async def run_readability(client, text):
    print(">> check_readability (PONK)...", flush=True)
    t0 = time.time()
    r = await client.call_tool(
        "check_readability", {"text": text, "include_highlighted_html": False}, timeout=180.0,
    )
    elapsed = time.time() - t0
    p = extract_tool_payload(r)
    if isinstance(p, dict):
        m = p.get("metrics", {})
        print(f"   ok={r.ok} elapsed={elapsed:.1f}s ARI={m.get('ari', '?')} rules_triggered={len(p.get('rules', []))}")
    else:
        print(f"   ok={r.ok} elapsed={elapsed:.1f}s payload not dict")
    return r, p


async def run_correct(client, text):
    print(">> correct_text (Korektor spellcheck)...", flush=True)
    t0 = time.time()
    r = await client.call_tool("correct_text", {"text": text, "mode": "spellcheck"}, timeout=180.0)
    elapsed = time.time() - t0
    p = extract_tool_payload(r)
    changed = p.get("changed", "?") if isinstance(p, dict) else "?"
    print(f"   ok={r.ok} elapsed={elapsed:.1f}s changed={changed}")
    return r, p


async def run_translate(client, text):
    # full doc je 8KB — translate může timeoutovat. Použiju první ~3KB.
    excerpt = text[:3000]
    print(f">> translate_text (cs->en, excerpt {len(excerpt)}B)...", flush=True)
    t0 = time.time()
    r = await client.call_tool(
        "translate_text", {"text": excerpt, "src": "cs", "tgt": "en"}, timeout=180.0,
    )
    elapsed = time.time() - t0
    p = extract_tool_payload(r)
    out_chars = p.get("output_chars", "?") if isinstance(p, dict) else "?"
    print(f"   ok={r.ok} elapsed={elapsed:.1f}s out_chars={out_chars}")
    return r, p


def check_pii_coverage(text, anonymized_payload):
    """Spocita kolik PII z PII_INVENTORY se anonymizovalo.

    Pouziva word-boundary check (re.search s \\b), aby substring v jine PII
    (napr. '12345678' uvnitr '1234567890') nezpusobil false positive.
    """
    if not isinstance(anonymized_payload, dict):
        return None
    import re as _re

    anonymized = anonymized_payload.get("anonymized", "")
    coverage = {"caught": [], "leaked": [], "n/a": []}

    def _present(needle: str, haystack: str) -> bool:
        # try word-boundary first; fall back to literal for items with chars
        # that don't form word boundaries (spaces, dashes inside).
        try:
            return _re.search(rf"\b{_re.escape(needle)}\b", haystack) is not None
        except _re.error:
            return needle in haystack

    for pii, label in PII_INVENTORY.items():
        if not _present(pii, text):
            coverage["n/a"].append((pii, label))
            continue
        if _present(pii, anonymized):
            coverage["leaked"].append((pii, label))
        else:
            coverage["caught"].append((pii, label))
    return coverage


async def main():
    with open(SPIS_PATH, "r", encoding="utf-8") as f:
        text = f.read()
    print(f"=== ULTIMATE SPIS: {len(text)} chars, {len(text.encode('utf-8'))} bytes ===\n")

    async with UfalMcpClient() as client:
        results = {}
        for name, fn in [
            ("anonymize", run_anonymize),
            ("extract_entities", run_extract),
            ("analyze_morphology", run_morphology),
            ("check_readability", run_readability),
            ("correct_text", run_correct),
            ("translate_text", run_translate),
        ]:
            try:
                r, p = await fn(client, text)
            except Exception as e:
                print(f"   EXCEPTION: {type(e).__name__}: {e}")
                r, p = None, None
            results[name] = {
                "ok": r.ok if r else False,
                "elapsed_s": round(r.elapsed_s, 2) if r else None,
                "exception": r.exception if r else "wrapper exception",
                "payload": p,
            }
            # save payload separately (some are big)
            with open(os.path.join(OUT_DIR, f"{name}.json"), "w", encoding="utf-8") as f:
                json.dump(results[name], f, ensure_ascii=False, indent=2, default=str)

        print()
        print("=== PII COVERAGE (anonymize) ===")
        cov = check_pii_coverage(text, results["anonymize"]["payload"])
        if cov:
            print(f"  caught: {len(cov['caught'])} / present in text: {len(cov['caught']) + len(cov['leaked'])}")
            print(f"  leaked: {len(cov['leaked'])}")
            print(f"  not in inventory text: {len(cov['n/a'])}")
            if cov["leaked"]:
                print("\n  LEAKED items:")
                for pii, label in cov["leaked"]:
                    print(f"    - {pii!r:50} ({label})")
            with open(os.path.join(OUT_DIR, "coverage.json"), "w", encoding="utf-8") as f:
                json.dump(cov, f, ensure_ascii=False, indent=2, default=str)

        # save aggregate summary
        summary = {
            "spis_bytes": len(text.encode("utf-8")),
            "tools": {k: {"ok": v["ok"], "elapsed_s": v["elapsed_s"]} for k, v in results.items()},
            "anonymize_replacements": len(
                results["anonymize"]["payload"].get("replacements", []) if isinstance(results["anonymize"]["payload"], dict) else []
            ),
            "entities_found": len(
                results["extract_entities"]["payload"].get("entities", []) if isinstance(results["extract_entities"]["payload"], dict) else []
            ),
            "coverage": cov,
        }
        with open(os.path.join(OUT_DIR, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
        print(f"\nResults saved to: {OUT_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())
