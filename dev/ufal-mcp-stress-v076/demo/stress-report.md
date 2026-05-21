# ÚFAL MCP — Stress test v0.7.5

> Robustness audit pro Charles Translator / NameTag 3 / UDPipe 2 / PONK / Korektor / MasKIT
> Připraveno pro tým **ÚFAL MFF UK, Univerzita Karlova v Praze**.

**Datum**: 21.5.2026
**Autor**: Michal Bürgermeister (`ufal-mcp` maintainer, MIT)
**Verze pod testem**: `ufal-mcp` 0.7.5 (PyPI, vydáno 21.5.2026 18:57)
**Test suite**: `dev/ufal-mcp-stress-v076/` — 94 testů ve 9 kategoriích, všech 6 nástrojů

---

## 1. Proč tento test

Po sérii real-world testů `ufal-mcp` v0.7.5 na právním spisu skutečného klienta
(*Jiříkův batch* — 17 dokumentů × 6 nástrojů = **102/102 ops OK**) jsem chtěl
wrapper vystavit **adversarial** vstupům: věcem, které v běžném použití nepřijdou,
ale rozhodují o tom, jestli se MCP server hodí pro produkční nasazení v citlivém
prostředí (právo, zdravotnictví).

Cílem **není** test ÚFAL backend služeb — ty jsou skvělé a tento test je
opakovaně potvrzuje. Cílem je **wrapper layer** (`ufal-mcp`), kterým prochází
vstup před voláním NameTag / UDPipe / PONK / Korektor / MasKIT / Translator.

---

## 2. Co bylo testováno

| Kategorie | Co testuje | Tests |
|---|---|---|
| **A** Degenerate | `""`, whitespace, emoji, single char, NUL byte, control chars | 19 |
| **B** Size | 1KB → 600KB (přes hard limit `MAX_INPUT_BYTES=500_000`) | 7 |
| **C** Encoding | BOM, ZWS, ZWJ, RTL override, kombinující znaky, PUA range | 9 |
| **D** Language mix | CZ+SK, CZ+EN+DE, CZ+UK (Cyrillic) | 8 |
| **E** PII adversarial | RČ ve 5 formátech, hybrid PII, OCR typos, false positive | 12 |
| **F** Domain | legal / medical (propouštěcí zpráva) / technical (ČSN) / social (tweet) | 6 |
| **G** Adversarial payload | HTML / JSON / SQL inj. / prompt inj. / path traversal | 8 |
| **H** Cross-tool | idempotence, round-trip překlad, anonymize→extract | 5 |
| **I** Concurrency | 15 paralelních asyncio calls (10 různých + 5 stejných) | 15 |
| **Σ** | | **94** |

**Test stack**:
- Standalone Python asyncio MCP **stdio** client (~200 LOC, bez `mcp` SDK)
- JSON-RPC 2.0 — stejný protokol, jaký používá Claude Code, Cline, atd.
- Per-test raw JSON v `results/raw/` → plně reprodukovatelné, audit-friendly

---

## 3. Headline

| Severity | Počet | Status |
|---|---|---|
| 🟢 OK (pass / expected_fail) | **85 / 94** (90 %) | wrapper v0.7.5 dobře drží |
| 🔴 **P0** PII leak | 2 | RČ bez lomítka + č.ú. prefix-base/bank |
| 🟠 **P1** idempotence / scale | 2 | anonymize není idempotentní; UFAL timeout na >10KB |
| 🟡 **P2** quality / data loss | ~5 | NUL/ZW chars rozsekávají entity; placeholdery se detekují jako entity |
| 🟢 **P3** API consistency | ~3 | whitespace = tichý no-op, emoji → lang=czech |

**Klíčový obrázek pro Univerzitu Karlovu**: backendové služby ÚFAL drží
robustně i pod adversarial loadem; všechny zásahy potřebné pro v0.7.6 jsou
ve **wrapper layeru** (mém kódu) — k upstream NameTag/MasKIT/UDPipe/PONK/Korektor/Translator
nemám žádnou stížnost ani requirement.

---

## 4. Top 5 nálezů

### 🔴 1. PII leak na ne-standardních formátech RČ (P0)

Vstup:
```
RČ formáty: 800312/1234, 800312 1234, 8003121234, 80-03-12/1234.
```
Output:
```
RČ formáty: RC1, 800312 1234, 8003121234, 80-03-12/1234.
```
Jen formát `800312/1234` se chytí. `8003121234` (10 digits bez separátoru)
prošel netknutý. To je kritické pro legal use — OCR z PDF často odstraní lomítko.

**Fix**: rozšířit regex v `maskit_patterns.py` o multiple RČ varianty.

---

### 🔴 2. PII leak na české bankovní číslo účtu (P0)

Vstup:
```
IBAN CZ65 0800 0000 1920 0014 5399, č.ú. 19-2000145399/0800.
```
Output:
```
IBAN IBAN1, č.ú. 19-2000145399/0800.
```
IBAN se chytí, ale klasický český formát `prefix-base/bank` ne. Pro legal/
banking workflow je to standardní zápis.

**Fix**: přidat regex pro CZ bankovní formát do `maskit_patterns.py`.

---

### 🟠 3. Anonymize není idempotentní (P1)

Re-volání `anonymize` na již anonymizovaný text vytváří nové placeholdery
a poškozuje původní:

```
Pass 1: ... bydlí na ulici ULICE1 ENTITA1 v MESTO1. Tel: TELEFON1.
Pass 2: ... bydlí na ulici ULICE1 ENTITA1ULICE1 v MESTO1. Tel: TELEFON1.
                                  ^^^^^^^^^^^^
                                  pass 2 spojil dvě placeholdery
```
Pro pipeline `anonymize → human review → re-anonymize` to je land mine.

**Fix**: v MasKIT pipeline detekovat existující sentinely (`OSOBA\d+`, `MESTO\d+`,
…) a skipnout je z replace operací.

---

### 🟠 4. UFAL upstream ReadTimeout pro vstupy >10KB (P1/P2)

Pro několik nástrojů se 10-50KB vstup nevejde do timeoutu:

| Test | Tool | Velikost | Výsledek |
|---|---|---|---|
| B2 | extract_entities | 10 KB | timeout 60s |
| B3 | anonymize | 50 KB | timeout 60s |
| B4 | check_readability | 50 KB | timeout 60s |
| B6 | anonymize | 120 KB | timeout 60s |
| B7 | translate_text | 11 KB | timeout 180s |

`validation.py` má hard cap **500 KB** (`MAX_INPUT_BYTES`) a soft warning na 100 KB,
ale v reálu upstream začíná škytat výrazně dřív. Pro real-world legal texty
(20-50KB spisy) to znamená že wrapper potřebuje **chunking** layer.

**Fix**: snížit soft warning na 10-20KB, dokumentovat doporučení chunkovat,
nebo přidat helper `chunked_call()`.

---

### 🟡 5. NUL byte tise rozseká entitu (P2)

Vstup:
```
Jan\x00Novák bydlí v Ostravě.
```
Výstup:
```json
{"entities": [{"text": "Jan", "type": "pf", "label": "křestní jméno"}]}
```
"Novák" zmizel bez warningu. OCR / PDF copy-paste občas NUL byte inject — jméno se
v PII pipeline rozpadne.

**Fix**: do `validation.py` přidat strip + warning na C0 control chars (0x00-0x1F
mimo \t\n\r) a zero-width chars (U+200B/C/D, U+FEFF). Analogicky k existujícímu
PUA strippingu.

---

## 5. Co funguje robustně (positive findings)

Tyto kategorie projely **100 %** — wrapper i upstream drží:

- **Concurrency** (kategorie I, 15/15 pass): 10 paralelních NameTag calls
  doběhlo za 1.75s wall clock (vs ~15s serial). 5 paralelních anonymize
  za 7.35s — placeholder mode je **deterministický i pod load** (stejný vstup → stejný output).
- **Encoding** (C, 9/9 pass): BOM, RTL override, NFD combining accents, astral
  plane znaky (𓂀) — wrapper přežije bez crashů. PUA range je správně stripped + warning.
- **Adversarial payloads** (G, 8/8 pass): HTML, JSON, SQL injection, prompt injection,
  path traversal, repetition flood — wrapper ani upstream nic neexplodují.
- **Language mixing** (D, 8/8 pass): CZ+SK+EN+DE, EN+CZ diakritika, ukrajinská cyrilice
  s CZ latinkou — model auto-detect funguje.
- **Domain stress** (F, 6/6 pass): právní judgment header, medical propouštěcí zpráva
  s diagnózami a léčbou (placeholder_mode + medical PII), ČSN technical, tweet social.
- **Round-trip překlad** (H2): CZ → EN → CZ zachoval 4/4 klíčová slova.
- **Validation hard cap**: 600KB vstup byl správně odmítnut (`ValidationError: Input
  too large: 600,000 bytes (max 500,000)`) — i když to zabralo víc času, než by mělo
  (>30s na JSON-RPC dispatch + validace).

---

## 6. Co to znamená pro ÚFAL backend

**Nic kritického nelíčí na vás.** Většina nálezů je čistě ve wrapper layeru
a opravím to v `ufal-mcp` 0.7.6 sám.

Jedno pozorování, které **může být zajímavé pro ÚFAL upstream**:

- **Timeoutové chování pod >10KB** by zaslouželo upstream review. Pro real-world
  legal texty 20-50KB se NameTag/MasKIT/PONK občas dostane do ReadTimeoutu.
  Možná jen tuning serverového queue / batchování. Nejde o bug, spíš o
  konfiguraci. Pokud byste měli rozhraní pro pre-batched chunky nebo asynchronní
  upload velkých dokumentů, hodilo by se to.

---

## 7. Reprodukovatelnost

Kompletní test suite je open-source (MIT, součást `ufal-mcp` repository).
Žádné dependency mimo Python stdlib + `mcp>=1.2.0`.

```bash
# 1. Spustit vše
python runner/run_stress.py
python runner/cross_tool.py

# 2. Vybrané kategorie / nástroje
python runner/run_stress.py --category E    # PII tests
python runner/run_stress.py --tool anonymize
python runner/run_stress.py --id E2

# 3. Regenerovat bug report
python runner/analyze.py
```

Raw výsledky per test v `results/raw/<id>.json` — každý JSON obsahuje
vstup, výstup, stderr tail z MCP serveru, timing, JSON-RPC error (pokud).

---

## 8. Plán pro v0.7.6

Detailní bug list je v `results/BUGS-v076.md` (8 P0-P2 nálezů + 8 P3 curated
quality findings z "pass" výsledků).

Aktuálně plánuji:
1. **Týden 22-26.5.** — RČ + č.ú. regex patche (P0), kompletní regression test rerun
2. **Týden 27.5.-2.6.** — idempotence fix, ZW/control chars strip, lang detect fallback
3. **v0.7.6 release** — cílově do 7.6.2026

Pak proběhne další round adversarial testu a publikace BUGS-v077.md, pokud nějaké zůstanou.

---

*Děkuji ÚFAL týmu za 6 skvělých služeb. Wrapper je jen tenká vrstva nad nimi
— jejich robustnost je důvod, proč ho můžu psát tak agresivně.*
