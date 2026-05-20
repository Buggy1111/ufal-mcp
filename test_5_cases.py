"""Comprehensive end-to-end test — 5 reálných use cases × všechny tools × více jazyků.

Cíl: ověřit že ufal-mcp v0.5.0 zvládne reálné workflow scénáře z legal-tech praxe.

Use cases:
1. CZ právní spis (Jiříkův typ) — celá pipeline
2. SK právní spis (Bratislavský soud) — multilingvální NER + UDPipe SK
3. UA žádost o azyl — UK→CZ překlad → CZ NER → CZ anonymize
4. EN korporátní smlouva — EN NER → CZ překlad → CZ analýza
5. DE právní dopis — DE NER → CZ překlad → readability check

Spouští se přes: python3 test_5_cases.py
"""

import asyncio
import json
import time
from typing import Any

from ufal_mcp.server import (
    analyze_morphology,
    anonymize,
    check_readability,
    correct_text,
    extract_entities,
    translate_text,
)

# ============================================================================
# REÁLNÉ TEST CASES
# ============================================================================

CASE_1_CZ = """Žaloba na zrušení vyživovací povinnosti

Žalobce: Jiří Pluhařík, narozený 15.02.1971, bytem Oderská 176, 749 01 Vítkov,
státní příslušnost: Česká republika, telefon: +420 777 123 456,
email: jiri.pluharik@seznam.cz, IČO: -

Žalovaný: Alexandra Tóthová, narozená 14.10.2004, bytem Slivková 36, 821 09 Bratislava,
státní příslušnost: Slovenská republika.

Mestský súd Bratislava II, sp. zn. 17Pc/53/2024, sudkyňa Mgr. Paulína Čaplánová.
Předchozí spisová značka: 28F/31/2017. Advokát žalobce: JUDr. Richard Pustějovský,
sídlem Matiční 730/3, 702 00 Ostrava 2, telefon 777 18 18 10.

Žalobce platil dceři výživné po dobu 9 let v celkové výši 700 000 Kč.
Účetní Šoltýsová ze společnosti ZR Trade s.r.o., IČO 12345678, od 04/2022
neoprávněně navýšila srážky z 3 000 Kč na 4 550 Kč bez soudního rozhodnutí.
Škoda žalobce z neoprávněných srážek činí 74 400 Kč."""

CASE_2_SK = """Návrh na zrušenie výživného

Navrhovateľ: Jiří Pluhařík, narodený 15.02.1971, bytom Oderská 176, Vítkov,
Česká republika. Telefón: +420 777 123 456.

Odporkyňa: Alexandra Tóthová, narodená 14.10.2004 v Bratislave, bytom
Slivková 36, 821 09 Bratislava. Mestský súd Bratislava II prejednáva vec
pod sp. zn. 17Pc/53/2024 pred sudkyňou Mgr. Paulínou Čaplánovou.

Odporkyňa je plnoletá, zamestnaná v spoločnosti Tatra Banka a.s. v Bratislave,
má vlastné dieťa. Otec je diabetik prvého typu, práceneschopný, platí mesačne
15 000 Kč na rôzne výživné. Konanie trvá viac ako 9 rokov, návrh na zrušenie
čaká 17 mesiacov bez prejednania."""

CASE_3_UA = """Заява про надання притулку

Я, Олександр Петренко, народжений 12 травня 1985 року в Києві, Україна,
проживав за адресою вул. Хрещатик 22, м. Київ. Я працював інженером
у компанії Київстар з 2018 по 2022 рік.

Після початку повномасштабного вторгнення Російської Федерації в Україну
24 лютого 2022 року, я був вимушений залишити свою країну. Через Польщу
я прибув до Чеської республіки 15 березня 2022 року.

Прошу про надання міжнародного захисту відповідно до Женевської конвенції
1951 року. Мій адвокат: JUDr. Marie Nováková, sídlem Václavské náměstí 17,
110 00 Praha 1, телефон +420 222 333 444."""

CASE_4_EN = """LEGAL NOTICE — Service Agreement Termination

To: John Smith, residing at 42 Baker Street, London W1U 7DD, United Kingdom,
born March 10, 1980, ID number: GB12345678.

From: Microsoft Corporation, 1 Microsoft Way, Redmond, WA 98052, USA.
Counsel: Linklaters LLP, One Silk Street, London EC2Y 8HQ.

This notice serves to inform you that pursuant to Section 12.3 of the Master
Service Agreement dated June 1, 2024, between Microsoft Corporation and
yourself, the Agreement is hereby terminated effective March 31, 2025.

The High Court of Justice, case reference HC-2025-001234, has confirmed
the validity of this notice on January 15, 2025. Should you wish to
contest this termination, you must file a response within 14 days."""

CASE_5_DE = """Klage gegen die Siemens AG

Kläger: Hans Müller, geboren am 5. Juni 1975, wohnhaft in der Hauptstraße 12,
80331 München, Deutschland. Vertreten durch Rechtsanwalt Dr. Klaus Weber,
Maximilianstraße 45, 80539 München.

Beklagte: Siemens AG, Werner-von-Siemens-Straße 1, 80333 München.

Das Landgericht München I, Aktenzeichen 5 O 1234/25, behandelt eine
Streitigkeit über den Arbeitsvertrag vom 1. Januar 2018. Der Kläger
verlangt eine Entschädigung in Höhe von 50.000 EUR wegen ungerechtfertigter
Kündigung am 15. März 2025. Verhandlungstermin: 20. April 2025, 9:00 Uhr."""


# ============================================================================
# REPORT HELPERS
# ============================================================================

class Report:
    def __init__(self):
        self.lines: list[str] = []
        self.errors: list[str] = []
        self.metrics: dict[str, Any] = {}

    def header(self, title: str):
        self.lines.append("")
        self.lines.append("=" * 80)
        self.lines.append(f" {title}")
        self.lines.append("=" * 80)

    def section(self, title: str):
        self.lines.append("")
        self.lines.append(f"--- {title} ---")

    def info(self, msg: str):
        self.lines.append(f"  {msg}")

    def ok(self, msg: str):
        self.lines.append(f"  ✓ {msg}")

    def warn(self, msg: str):
        self.lines.append(f"  ⚠ {msg}")

    def fail(self, msg: str):
        self.lines.append(f"  ✗ {msg}")
        self.errors.append(msg)

    def text_preview(self, label: str, text: str, max_len: int = 200):
        preview = text.replace("\n", " ").strip()
        if len(preview) > max_len:
            preview = preview[:max_len] + "…"
        self.lines.append(f"  {label}: {preview}")

    def emit(self):
        print("\n".join(self.lines))


# ============================================================================
# PIPELINE — for each case run relevant tools
# ============================================================================

async def run_pipeline(name: str, text: str, lang_hint: str, r: Report):
    """Spustí celou pipeline pro daný text."""
    r.header(f"{name}  (hint: {lang_hint})")
    r.text_preview("Vstup", text, max_len=250)
    r.info(f"délka: {len(text)} znaků, {text.count(chr(10)) + 1} řádků")

    # === 1. NER ===
    r.section("1. extract_entities (auto)")
    t0 = time.time()
    try:
        ents = await extract_entities(text)
        dt = time.time() - t0
        r.ok(f"model: {ents['model']}, detected: {ents.get('detected_language', 'n/a')}, "
             f"{ents['count']} entit ({dt:.1f}s)")
        if ents.get("warnings"):
            for w in ents["warnings"]:
                r.warn(w)
        # Show top 5 entities
        types_seen = {}
        for e in ents["entities"][:10]:
            r.info(f"  [{e['type']:6}] {e['label']:25} {e['text']!r}")
            types_seen.setdefault(e["type"], 0)
            types_seen[e["type"]] += 1
        if len(ents["entities"]) > 10:
            r.info(f"  ... +{len(ents['entities']) - 10} dalších entit")
        r.metrics[f"{name}_ner_count"] = ents["count"]
    except Exception as e:
        r.fail(f"extract_entities failed: {type(e).__name__}: {e}")

    # === 2. UDPipe morfologie ===
    r.section("2. analyze_morphology (auto SK/CZ)")
    try:
        morph = await analyze_morphology(text[:500])  # first 500 chars for speed
        r.ok(f"model: {morph['model']}, detected: {morph.get('detected_language', 'n/a')}, "
             f"{morph['token_count']} tokenů ve {morph['sentence_count']} větách")
    except Exception as e:
        r.fail(f"analyze_morphology failed: {type(e).__name__}: {e}")

    # === 3. Anonymize (jen pro CZ a SK) ===
    if lang_hint in ("cs", "sk"):
        r.section("3. anonymize (MasKIT + strict pre-pass)")
        try:
            anon = await anonymize(text)
            sources = anon.get("sources", {})
            r.ok(f"replacements: maskit={sources.get('maskit', 0)}, "
                 f"wrapper={sources.get('wrapper', 0)}, "
                 f"warnings={len(anon.get('warnings', []))}")
            r.text_preview("Anonymized", anon["anonymized"], max_len=200)
        except Exception as e:
            r.fail(f"anonymize failed: {type(e).__name__}: {e}")
    else:
        r.section("3. anonymize — SKIP (MasKIT je CZ-only)")
        r.info(f"  pro {lang_hint} text bychom nejprve přeložili → CZ → anonymize")

    # === 4. Korektor — jen pro CZ ===
    if lang_hint == "cs":
        r.section("4. correct_text (diacritics restore)")
        # Strip diacritics first to test restoration
        try:
            stripped = await correct_text(text[:300], mode="strip")
            r.info(f"  Stripped: {stripped['corrected'][:150]}...")
            restored = await correct_text(stripped["corrected"], mode="diacritics")
            r.ok(f"diacritics restored, changed={restored['changed']}")
            r.text_preview("Restored", restored["corrected"], max_len=200)
        except Exception as e:
            r.fail(f"correct_text failed: {type(e).__name__}: {e}")
    else:
        r.section("4. correct_text — SKIP (Korektor je CZ-only)")

    # === 5. PONK readability — jen pro CZ ===
    if lang_hint == "cs":
        r.section("5. check_readability (PONK)")
        try:
            pn = await check_readability(text)
            metrics = pn.get("metrics", {})
            ari = metrics.get("Automated readability index", {}).get("value", "?")
            verb_dist = metrics.get("Verb Distance", {}).get("value", "?")
            activity = metrics.get("Activity", {}).get("value", "?")
            lex_div = metrics.get("Lexical diversity", {}).get("value", "?")
            r.ok(f"ARI={ari}, Verb Distance={verb_dist}, Activity={activity}, "
                 f"Lexical diversity={lex_div}")
        except Exception as e:
            r.fail(f"check_readability failed: {type(e).__name__}: {e}")
    else:
        r.section("5. check_readability — SKIP (PONK je CZ-only)")


async def run_translation_pipeline(name: str, text: str, src: str, tgt: str, r: Report):
    """Test překladu + post-translation NER."""
    r.section(f"6. translate_text ({src} → {tgt})")
    t0 = time.time()
    try:
        tr = await translate_text(text, src=src, tgt=tgt)
        dt = time.time() - t0
        r.ok(f"pair={tr['pair']}, {tr['input_chars']} → {tr['output_chars']} znaků ({dt:.1f}s)")
        r.text_preview("Přeloženo", tr["translated"], max_len=250)

        # Post-translation NER on translated text
        if tgt == "cs":
            r.info("→ Post-translation NER (cs):")
            ents = await extract_entities(tr["translated"])
            r.ok(f"  {ents['count']} entit v překladu, detected={ents.get('detected_language')}")
            for e in ents["entities"][:5]:
                r.info(f"    [{e['type']:6}] {e['text']!r}")
    except Exception as e:
        r.fail(f"translate_text failed: {type(e).__name__}: {e}")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    print("\n" + "█" * 80)
    print("█  ufal-mcp v0.5.0 — END-TO-END TEST 5 USE CASES × ALL TOOLS")
    print("█  Datum: 2026-05-20")
    print("█  Backend: live ÚFAL/LINDAT REST API")
    print("█" * 80)

    r = Report()
    overall_start = time.time()

    # CASE 1 — CZ právní spis (Jiříkův typ)
    await run_pipeline("CASE 1: CZ právní spis (žaloba na zrušení výživného)", CASE_1_CZ, "cs", r)
    await run_translation_pipeline("CASE 1 translation", CASE_1_CZ[:400], "cs", "en", r)

    # CASE 2 — SK právní spis
    await run_pipeline("CASE 2: SK právní spis (Mestský súd Bratislava)", CASE_2_SK, "sk", r)
    # SK → CZ translation není v Charles Translatoru, ale CZ→EN via mutual intelligibility
    r.section("6. translate_text SK — N/A")
    r.info("  Charles Translator nemá SK↔CZ pár; pro SK použij UDPipe SK + NameTag UNER + MasKIT")
    r.info("  (CZ a SK jsou mutual intelligible, anonymizace funguje napřímo)")

    # CASE 3 — UA žádost o azyl
    await run_pipeline("CASE 3: UA žádost o azyl (Ukrainian refugee)", CASE_3_UA, "uk", r)
    await run_translation_pipeline("CASE 3 translation", CASE_3_UA, "uk", "cs", r)

    # CASE 4 — EN korporátní notice
    await run_pipeline("CASE 4: EN korporátní termination notice", CASE_4_EN, "en", r)
    await run_translation_pipeline("CASE 4 translation", CASE_4_EN, "en", "cs", r)

    # CASE 5 — DE právní dopis
    await run_pipeline("CASE 5: DE Klage gegen Siemens AG", CASE_5_DE, "de", r)
    await run_translation_pipeline("CASE 5 translation", CASE_5_DE, "de", "en", r)

    # === FINAL REPORT ===
    overall_dt = time.time() - overall_start
    r.header("VÝSLEDEK")
    r.info(f"Celkový čas: {overall_dt:.1f}s")
    r.info(f"Errors: {len(r.errors)}")
    if r.errors:
        for e in r.errors:
            r.fail(e)
    else:
        r.ok("Žádné chyby — všechny pipelines proběhly úspěšně.")
    r.info("")
    r.info("Metrics:")
    for k, v in r.metrics.items():
        r.info(f"  {k}: {v}")

    r.emit()


if __name__ == "__main__":
    asyncio.run(main())
