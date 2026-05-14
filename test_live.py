"""Smoke test — volá živé ÚFAL API a tiskne výstupy."""

import asyncio
import json

from ufal_mcp.server import (
    analyze_morphology,
    anonymize,
    check_readability,
    extract_entities,
)


SAMPLE = (
    "Jiří Pluhařík, bytem Sokolovská 12, Příbor, PSČ 74258, narozen 1.1.1980, "
    "telefon 777 123 456, podal žalobu na ZR Trade s.r.o., IČO 12345678, "
    "u Krajského soudu v Ostravě dne 16. dubna 2026, č.j. 25 C 123/2026."
)


async def main() -> None:
    print("=== extract_entities ===")
    ents = await extract_entities(SAMPLE)
    print(json.dumps(ents, ensure_ascii=False, indent=2))

    print("\n=== anonymize ===")
    anon = await anonymize(SAMPLE)
    print(json.dumps(anon, ensure_ascii=False, indent=2))

    print("\n=== analyze_morphology ===")
    morph = await analyze_morphology("Jiří podal žalobu u Krajského soudu v Ostravě.")
    print(json.dumps({
        "model": morph["model"],
        "tokens": morph["token_count"],
        "first_sentence": morph["sentences"][0],
    }, ensure_ascii=False, indent=2))

    print("\n=== check_readability ===")
    pn = await check_readability(
        "Účastníku řízení se ukládá povinnost ve lhůtě patnácti dnů "
        "ode dne doručení tohoto usnesení uhradit státu náklady řízení "
        "sestávající z odměny ustanoveného zástupce."
    )
    print(json.dumps({
        "version": pn["version"],
        "counts": pn["counts"],
        "metrics": {k: v["value"] for k, v in pn["metrics"].items()},
        "html_len": len(pn["highlighted_html"]),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
