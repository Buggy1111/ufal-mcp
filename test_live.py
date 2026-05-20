"""Smoke test — volá živé ÚFAL API a tiskne výstupy.

Testuje všech 5 MCP tools na reálných právních a vícejazyčných textech:
1. CZ právní text (Jiřík Pluhařík case + reálný NS rozsudek 21 Cdo 2929/2016)
2. SK právní text (Bratislavský soud)
3. Multilingvální NER (EN/DE/PL/UK/RU + auto-detect)
4. Korektor — spell check + diacritics
"""

import asyncio
import json

from ufal_mcp.server import (
    analyze_morphology,
    anonymize,
    check_readability,
    correct_text,
    extract_entities,
)


# --- Real-world test samples ---

CZ_JIRIK = (
    "Jiří Pluhařík, bytem Sokolovská 12, Příbor, PSČ 74258, narozen 1.1.1980, "
    "telefon 777 123 456, podal žalobu na ZR Trade s.r.o., IČO 12345678, "
    "u Krajského soudu v Ostravě dne 16. dubna 2026, č.j. 25 C 123/2026."
)

CZ_NS_ROZSUDEK = (
    "Rozsudek Nejvyššího soudu České republiky sp. zn. 21 Cdo 2929/2016 "
    "ze dne 19. ledna 2017, ve věci žalobce T. N., zastoupeného Mgr. J. Š., "
    "advokátkou se sídlem v Mladé Boleslavi, proti žalované J. N., zastoupené "
    "Mgr. H. K., advokátkou se sídlem v Praze. Smluvní strany ujednaly dne "
    "24. května 2012 jednorázové vyplacení 350 000 Kč na úhradu výživného "
    "do 24. března 2023. Krajský soud v Praze zrušil rozsudek a vrátil věc."
)

SK_BRATISLAVA = (
    "Alexandra Tóthová, narodená 14.10.2004 v Bratislave, podala u Mestského "
    "súdu Bratislava II návrh proti otcovi Jiřímu Pluhaříkovi, narodenému "
    "15.02.1971 v Příbore. Konanie sa vedie pod sp. zn. 17Pc/53/2024, "
    "sudkyňa Mgr. Paulína Čaplánová. Zastupuje JUDr. Richard Pustějovský, "
    "Matiční 730/3, Ostrava 2."
)

EN_LEGAL = (
    "John Smith from London filed a lawsuit against Microsoft Corporation "
    "at the High Court of Justice on March 15, 2025. The case is registered "
    "under reference HC-2025-001234. Smith is represented by Linklaters LLP."
)

DE_LEGAL = (
    "Hans Müller aus Berlin reichte am 15. März 2025 beim Landgericht München "
    "eine Klage gegen die Siemens AG ein. Das Verfahren wird unter dem "
    "Aktenzeichen 5 O 1234/25 geführt."
)

PL_LEGAL = (
    "Jan Kowalski z Warszawy wniósł pozew przeciwko Orlen S.A. "
    "do Sądu Okręgowego w Warszawie dnia 15 marca 2025 roku. "
    "Sprawa toczy się pod sygnaturą I C 1234/25."
)

RU_LEGAL = (
    "Иван Петров из Москвы подал иск против ПАО Газпром в Арбитражный "
    "суд города Москвы 15 марта 2025 года. Дело № А40-1234/2025."
)

NO_DIA = (
    "Jiri Pluharik podal zalobu u Krajskeho soudu v Ostrave dne 16. dubna 2026."
)

CZ_LONG_SENTENCE = (
    "Účastníku řízení se ukládá povinnost ve lhůtě patnácti dnů ode dne "
    "doručení tohoto usnesení uhradit státu na účet Krajského soudu v Ostravě "
    "náklady řízení sestávající z odměny ustanoveného zástupce a hotových výdajů "
    "spočívajících v cestovném a stravném ve výši celkem osmnácti tisíc pěti set korun."
)


# --- Test runners ---

def _dump(obj, max_chars=2000):
    s = json.dumps(obj, ensure_ascii=False, indent=2)
    if len(s) > max_chars:
        return s[:max_chars] + f"\n  ... (truncated, total {len(s)} chars)"
    return s


async def test_cz_jirik():
    print("\n" + "=" * 70)
    print("TEST 1: CZ právní text (Jiřík Pluhařík)")
    print("=" * 70)
    print(f"Vstup: {CZ_JIRIK[:100]}...")

    ents = await extract_entities(CZ_JIRIK)
    print(f"\n→ extract_entities (CZ CNEC2.0): model={ents['model']}, count={ents['count']}, "
          f"detected={ents.get('detected_language')}")
    for e in ents["entities"][:10]:
        print(f"    [{e['type']:6}] {e['label']:25} '{e['text']}'")

    anon = await anonymize(CZ_JIRIK)
    print(f"\n→ anonymize: {anon['sources']}, {len(anon['warnings'])} warnings")
    print(f"    Anonymized: {anon['anonymized'][:150]}...")


async def test_cz_ns():
    print("\n" + "=" * 70)
    print("TEST 2: CZ právní text (reálný NS rozsudek 21 Cdo 2929/2016)")
    print("=" * 70)
    ents = await extract_entities(CZ_NS_ROZSUDEK)
    print(f"→ entities: {ents['count']} ({ents.get('detected_language')})")
    org_ents = [e for e in ents["entities"] if e["type"] in {"io", "if", "ic", "ORG"}]
    print(f"   Z toho institucí/firem: {len(org_ents)}")
    for e in org_ents[:5]:
        print(f"    [{e['type']:4}] {e['text']}")


async def test_sk():
    print("\n" + "=" * 70)
    print("TEST 3: SK právní text (Bratislavský soud) — multilingvální NER")
    print("=" * 70)
    print(f"Vstup: {SK_BRATISLAVA[:100]}...")

    ents = await extract_entities(SK_BRATISLAVA)
    print(f"\n→ extract_entities (auto): model={ents['model']}, detected={ents.get('detected_language')}")
    print(f"  count={ents['count']}, warnings={len(ents['warnings'])}")
    for e in ents["entities"][:10]:
        print(f"    [{e['type']:4}] {e['label']:18} '{e['text']}'")

    morph = await analyze_morphology(SK_BRATISLAVA[:200])
    print(f"\n→ analyze_morphology: model={morph['model']}, detected={morph.get('detected_language')}, "
          f"tokens={morph['token_count']}")


async def test_multilingual():
    print("\n" + "=" * 70)
    print("TEST 4: Multilingvální stress test (EN, DE, PL, RU)")
    print("=" * 70)
    samples = [("EN", EN_LEGAL), ("DE", DE_LEGAL), ("PL", PL_LEGAL), ("RU", RU_LEGAL)]
    for lang, text in samples:
        ents = await extract_entities(text)
        types = [(e["type"], e["text"]) for e in ents["entities"]]
        print(f"\n  {lang} (detect={ents.get('detected_language')}, model={ents['model']}):")
        for t, txt in types[:8]:
            print(f"    [{t:6}] {txt}")


async def test_korektor():
    print("\n" + "=" * 70)
    print("TEST 5: Korektor (diakritika + spellcheck)")
    print("=" * 70)
    print(f"Vstup bez diakritiky: {NO_DIA}")

    fixed = await correct_text(NO_DIA, mode="diacritics")
    print(f"\n→ diacritics: changed={fixed['changed']}, model={fixed['model']}")
    print(f"   Výsledek: {fixed['corrected']}")

    sp = await correct_text("Jirka napisl dopis svemu kameradovi z mest.", mode="spellcheck")
    print(f"\n→ spellcheck: changed={sp['changed']}")
    print(f"   Výsledek: {sp['corrected']}")


async def test_ponk():
    print("\n" + "=" * 70)
    print("TEST 6: PONK (čitelnost CZ právního textu)")
    print("=" * 70)
    pn = await check_readability(CZ_LONG_SENTENCE)
    print(f"  version={pn['version']}")
    print(f"  metrics:")
    for k, v in pn["metrics"].items():
        val = v.get("value") if isinstance(v, dict) else v
        print(f"    {k}: {val}")


async def main():
    print("\n" + "█" * 70)
    print("█  ufal-mcp v0.4.0 — REAL-WORLD SMOKE TEST")
    print("█  Datum: 2026-05-20, testy běží proti živým ÚFAL REST API")
    print("█" * 70)

    try:
        await test_cz_jirik()
        await test_cz_ns()
        await test_sk()
        await test_multilingual()
        await test_korektor()
        await test_ponk()
        print("\n" + "█" * 70)
        print("█  ✓ VŠECHNY TESTY PROBĚHLY")
        print("█" * 70 + "\n")
    except Exception as e:
        print(f"\n✗ TEST SELHAL: {type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
