# UFAL MCP v0.7.5 — Stress Test Bug Report (vstup pro v0.7.6)

**Datum**: 2026-05-21 19:25
**Test suite**: `dev/ufal-mcp-stress-v076/`
**Server**: ÚFAL MFF UK / Univerzita Karlova v Praze
**Verze**: ufal-mcp 0.7.5

## Summary

- Total tests run: **94**
- OK (pass + expected_fail): **85** (90%)
- **P0**: 2
- **P1**: 1
- **P2**: 6

## Per-tool breakdown

| Nástroj | OK | P0 | P1 | P2 | P3 |
|---|---|---|---|---|---|
| `analyze_morphology` | 5 | 0 | 0 | 0 | 0 |
| `anonymize` | 25 | 2 | 1 | 1 | 0 |
| `check_readability` | 4 | 0 | 0 | 1 | 0 |
| `correct_text` | 7 | 0 | 0 | 0 | 0 |
| `cross-tool` | 3 | 0 | 0 | 2 | 0 |
| `extract_entities` | 37 | 0 | 0 | 1 | 0 |
| `translate_text` | 4 | 0 | 0 | 1 | 0 |

## 🔴 P0 — Crash / PII leak / data loss

### [E2] `anonymize` — 5 RC format variants

**Reason**: PII LEAK: ['800312', '8003121234'] (2/2)

**Input** (64B):
```
RČ formáty: 800312/1234, 800312 1234, 8003121234, 80-03-12/1234.
```
**Args**: `{"text": "RČ formáty: 800312/1234, 800312 1234, 8003121234, 80-03-12/1"}`

**Status**: `fail`  |  **Note**: PII LEAK: ['800312', '8003121234'] (2/2)

**Elapsed**: 1.172s
**stderr tail**:
```
2026-05-21 19:21:31,688 [INFO] ufal-mcp: Processing request of type CallToolRequest
2026-05-21 19:21:32,147 [INFO] ufal-mcp: HTTP Request: POST https://lindat.mff.cuni.cz/services/nametag/api/recognize "HTTP/1.1 200 OK"
2026-05-21 19:21:32,964 [INFO] ufal-mcp: HTTP Request: POST https://quest.ms.mff.cuni.cz/maskit/api/process "HTTP/1.1 200 OK"
2026-05-21 19:21:33,204 [INFO] ufal-mcp: HTTP Request: POST https://lindat.mff.cuni.cz/services/nametag/api/recognize "HTTP/1.1 200 OK"
2026-05-21 19:21:33,208 [INFO] ufal-mcp: Processing request of type CallToolRequest
2026-05-21 19:21:33,657 [INFO] ufal-mcp: HTTP Request: POST https://lindat.mff.cuni.cz/services/nametag/api/recognize "HTTP/1.1 200 OK"
2026-05-21 19:21:34,377 [INFO] ufal-mcp: HTTP Request: POST https://quest.ms.mff.cuni.cz/maskit/api/process "HTTP/1.1 200 OK"
```
**Payload preview**:
```json
{
  "anonymized": "RČ formáty: RC1, 800312 1234, 8003121234, 80-03-12/1234.",
  "count": 1,
  "warnings": [],
  "sources": {
    "maskit": 0,
    "wrapper-regex": 1,
    "wrapper-strict": 0,
    "wrapper-placeholder": 0,
    "wrapper-nametag-fallback": 0
  },
  "replacements": [
    {
      "original": "800312/1234",
      "placeholder": "RC1",
      "type": "rodné číslo",
      "source": "wrapper-regex"
    }
  ]
}
```

---

### [E6] `anonymize` — IBAN + cislo uctu placeholder mode

**Reason**: PII LEAK: ['19-2000145399'] (1/2)

**Input** (60B):
```
IBAN CZ65 0800 0000 1920 0014 5399, č.ú. 19-2000145399/0800.
```
**Args**: `{"text": "IBAN CZ65 0800 0000 1920 0014 5399, č.ú. 19-2000145399/0800.", "placeholder_mode": "..."}`

**Status**: `fail`  |  **Note**: PII LEAK: ['19-2000145399'] (1/2)

**Elapsed**: 1.433s
**stderr tail**:
```
etag/api/recognize "HTTP/1.1 200 OK"
2026-05-21 19:21:37,397 [INFO] ufal-mcp: Processing request of type CallToolRequest
2026-05-21 19:21:37,751 [INFO] ufal-mcp: HTTP Request: POST https://lindat.mff.cuni.cz/services/nametag/api/recognize "HTTP/1.1 200 OK"
2026-05-21 19:21:38,423 [INFO] ufal-mcp: HTTP Request: POST https://quest.ms.mff.cuni.cz/maskit/api/process "HTTP/1.1 200 OK"
2026-05-21 19:21:38,676 [INFO] ufal-mcp: HTTP Request: POST https://lindat.mff.cuni.cz/services/nametag/api/recognize "HTTP/1.1 200 OK"
2026-05-21 19:21:38,680 [INFO] ufal-mcp: Processing request of type CallToolRequest
2026-05-21 19:21:39,050 [INFO] ufal-mcp: HTTP Request: POST https://lindat.mff.cuni.cz/services/nametag/api/recognize "HTTP/1.1 200 OK"
2026-05-21 19:21:39,651 [INFO] ufal-mcp: HTTP Request: POST https://quest.ms.mff.cuni.cz/maskit/api/process "HTTP/1.1 200 OK"
2026-05-21 19:21:40,109 [INFO] ufal-mcp: HTTP Request: POST https://lindat.mff.cuni.cz/services/nametag/api/recognize "HTTP/1.1 200 OK"
```
**Payload preview**:
```json
{
  "anonymized": "IBAN IBAN1, č.ú. 19-2000145399/0800.",
  "count": 1,
  "warnings": [],
  "sources": {
    "maskit": 0,
    "wrapper-regex": 1,
    "wrapper-strict": 0,
    "wrapper-placeholder": 0,
    "wrapper-nametag-fallback": 0
  },
  "replacements": [
    {
      "original": "CZ65 0800 0000 1920 0014 5399",
      "placeholder": "IBAN1",
      "type": "IBAN",
      "source": "wrapper-regex"
    }
  ]
}
```

---

## 🟠 P1 — Wrong output / unresponsive for real-world size

### [B6] `anonymize` — 120KB soft warn

**Reason**: timeout for 120000B (large but should work)

**Input** (120000B, prvních 200 znaků):
```
Jan Novák. Jan Novák. Jan Novák. Jan Novák. Jan Novák. Jan Novák. Jan Novák. Jan Novák. Jan Novák. Jan Novák. Jan Novák. Jan Novák. Jan Novák. Jan Novák. Jan Novák. Jan Novák. Jan Novák. Jan Novák. Ja
```
**Args**: `{"text": "Jan Novák. Jan Novák. Jan Novák. Jan Novák. Jan Novák. Jan N"}`

**Status**: `error`  |  **Note**: timeout — possible hang: timeout after 60.0s

**Elapsed**: 60.035s
**Exception**: `timeout after 60.0s`
**stderr tail**:
```
ng request of type CallToolRequest
2026-05-21 19:16:02,486 [INFO] ufal-mcp: HTTP Request: POST https://lindat.mff.cuni.cz/services/nametag/api/recognize "HTTP/1.1 200 OK"
2026-05-21 19:16:58,958 [INFO] ufal-mcp: Processing request of type CallToolRequest
2026-05-21 19:18:04,881 [INFO] ufal-mcp: Processing request of type CallToolRequest
2026-05-21 19:18:40,429 [INFO] ufal-mcp: HTTP Request: POST https://quest.ms.mff.cuni.cz/ponk/api/process "HTTP/1.1 200 OK"
2026-05-21 19:19:10,573 [INFO] ufal-mcp: Processing request of type CallToolRequest
2026-05-21 19:19:10,573 [ERROR] ufal-mcp: extract_entities validation failed: Input too large: 600,000 bytes (max 500,000). Pro velké dokumenty rozděl na menší části a volej API postupně.
2026-05-21 19:19:43,539 [INFO] ufal-mcp: Processing request of type CallToolRequest
2026-05-21 19:19:43,540 [WARNING] ufal-mcp: anonymize input: Velký vstup: 130,909 bytes. ÚFAL API může být pomalé (zvaž timeout >180s) a Charles Translator může selhat pro doc mode.
```

---

## 🟡 P2 — Quality degradation

### [B2] `extract_entities` — 10KB

**Reason**: timeout for 10000B (small input)

**Input** (10000B, prvních 200 znaků):
```
Jan Novák bydlí v Ostravě. Jan Novák bydlí v Ostravě. Jan Novák bydlí v Ostravě. Jan Novák bydlí v Ostravě. Jan Novák bydlí v Ostravě. Jan Novák bydlí v Ostravě. Jan Novák bydlí v Ostravě. Jan Novák b
```
**Args**: `{"text": "Jan Novák bydlí v Ostravě. Jan Novák bydlí v Ostravě. Jan No"}`

**Status**: `error`  |  **Note**: timeout — possible hang: timeout after 60.0s

**Elapsed**: 60.052s
**Exception**: `timeout after 60.0s`
**stderr tail**:
```
2026-05-21 19:15:51,590 [INFO] ufal-mcp: Processing request of type CallToolRequest
2026-05-21 19:15:53,029 [INFO] ufal-mcp: HTTP Request: POST https://lindat.mff.cuni.cz/services/nametag/api/recognize "HTTP/1.1 200 OK"
2026-05-21 19:15:53,040 [INFO] ufal-mcp: Processing request of type CallToolRequest
2026-05-21 19:16:02,486 [INFO] ufal-mcp: HTTP Request: POST https://lindat.mff.cuni.cz/services/nametag/api/recognize "HTTP/1.1 200 OK"
```

---

### [B3] `anonymize` — 50KB legal-ish anonymize

**Reason**: timeout for 47500B (small input)

**Input** (47500B, prvních 200 znaků):
```
Pan Jiří Pluhařík, narozen 12.3.1980, bydlí v Ostravě na ulici Hlavní 5. Telefon: 777 123 456. Pan Jiří Pluhařík, narozen 12.3.1980, bydlí v Ostravě na ulici Hlavní 5. Telefon: 777 123 456. Pan Jiří P
```
**Args**: `{"text": "Pan Jiří Pluhařík, narozen 12.3.1980, bydlí v Ostravě na uli"}`

**Status**: `error`  |  **Note**: timeout — possible hang: timeout after 60.0s

**Elapsed**: 60.057s
**Exception**: `timeout after 60.0s`
**stderr tail**:
```
2026-05-21 19:15:51,590 [INFO] ufal-mcp: Processing request of type CallToolRequest
2026-05-21 19:15:53,029 [INFO] ufal-mcp: HTTP Request: POST https://lindat.mff.cuni.cz/services/nametag/api/recognize "HTTP/1.1 200 OK"
2026-05-21 19:15:53,040 [INFO] ufal-mcp: Processing request of type CallToolRequest
2026-05-21 19:16:02,486 [INFO] ufal-mcp: HTTP Request: POST https://lindat.mff.cuni.cz/services/nametag/api/recognize "HTTP/1.1 200 OK"
2026-05-21 19:16:58,958 [INFO] ufal-mcp: Processing request of type CallToolRequest
```

---

### [B4] `check_readability` — 50KB readability

**Reason**: timeout for 35200B (small input)

**Input** (35200B, prvních 200 znaků):
```
Žalobce uvedl, že žalovaný porušil smlouvu. Žalobce uvedl, že žalovaný porušil smlouvu. Žalobce uvedl, že žalovaný porušil smlouvu. Žalobce uvedl, že žalovaný porušil smlouvu. Žalobce uvedl, že žalova
```
**Args**: `{"text": "Žalobce uvedl, že žalovaný porušil smlouvu. Žalobce uvedl, ž"}`

**Status**: `error`  |  **Note**: timeout — possible hang: timeout after 60.0s

**Elapsed**: 60.025s
**Exception**: `timeout after 60.0s`
**stderr tail**:
```
2026-05-21 19:15:51,590 [INFO] ufal-mcp: Processing request of type CallToolRequest
2026-05-21 19:15:53,029 [INFO] ufal-mcp: HTTP Request: POST https://lindat.mff.cuni.cz/services/nametag/api/recognize "HTTP/1.1 200 OK"
2026-05-21 19:15:53,040 [INFO] ufal-mcp: Processing request of type CallToolRequest
2026-05-21 19:16:02,486 [INFO] ufal-mcp: HTTP Request: POST https://lindat.mff.cuni.cz/services/nametag/api/recognize "HTTP/1.1 200 OK"
2026-05-21 19:16:58,958 [INFO] ufal-mcp: Processing request of type CallToolRequest
2026-05-21 19:18:04,881 [INFO] ufal-mcp: Processing request of type CallToolRequest
2026-05-21 19:18:40,429 [INFO] ufal-mcp: HTTP Request: POST https://quest.ms.mff.cuni.cz/ponk/api/process "HTTP/1.1 200 OK"
```

---

### [B7] `translate_text` — 10KB+ translate cs->en

**Reason**: timeout for 11200B (small input)

**Input** (11200B, prvních 200 znaků):
```
Soud rozhodl. Soud rozhodl. Soud rozhodl. Soud rozhodl. Soud rozhodl. Soud rozhodl. Soud rozhodl. Soud rozhodl. Soud rozhodl. Soud rozhodl. Soud rozhodl. Soud rozhodl. Soud rozhodl. Soud rozhodl. Soud
```
**Args**: `{"text": "Soud rozhodl. Soud rozhodl. Soud rozhodl. Soud rozhodl. Soud", "src": "...", "tgt": "..."}`

**Status**: `error`  |  **Note**: timeout — possible hang: timeout after 180.0s

**Elapsed**: 180.059s
**Exception**: `timeout after 180.0s`
**stderr tail**:
```
-mcp: HTTP Request: POST https://quest.ms.mff.cuni.cz/ponk/api/process "HTTP/1.1 200 OK"
2026-05-21 19:19:10,573 [INFO] ufal-mcp: Processing request of type CallToolRequest
2026-05-21 19:19:10,573 [ERROR] ufal-mcp: extract_entities validation failed: Input too large: 600,000 bytes (max 500,000). Pro velké dokumenty rozděl na menší části a volej API postupně.
2026-05-21 19:19:43,539 [INFO] ufal-mcp: Processing request of type CallToolRequest
2026-05-21 19:19:43,540 [WARNING] ufal-mcp: anonymize input: Velký vstup: 130,909 bytes. ÚFAL API může být pomalé (zvaž timeout >180s) a Charles Translator může selhat pro doc mode.
2026-05-21 19:20:49,435 [INFO] ufal-mcp: Processing request of type CallToolRequest
2026-05-21 19:20:54,705 [INFO] ufal-mcp: HTTP Request: POST https://lindat.mff.cuni.cz/services/translation/api/v2/models/cs-en "HTTP/1.1 200 OK"
2026-05-21 19:21:55,521 [WARNING] ufal-mcp: ReadTimeout na https://lindat.mff.cuni.cz/services/nametag/api/recognize (pokus 1/4), retry za 1.0s
```

---

### [H1_idempotence] `cross-tool` — anonymize(anonymize(x)) != anonymize(x)

**Reason**: anonymize(anonymize(x)) != anonymize(x)

**Input** (0B):
```

```

**Status**: `fail`  |  **Note**: anonymize(anonymize(x)) != anonymize(x)


---

### [H3_chain] `cross-tool` — 1 placeholdery zachyceny jako entity

**Reason**: 1 placeholdery zachyceny jako entity

**Input** (0B):
```

```

**Status**: `fail`  |  **Note**: 1 placeholdery zachyceny jako entity


---

## 🟢 P3 — Cosmetic / silent quality (curated z `pass` výsledků)

Tyto testy formálně proletěly ("pass" status), ale výstup obsahuje
nezdokumentované degradace, které by user mohl přehlédnout. Patří do
v0.7.6 minimálně jako warning nebo dokumentace.

### [A18] `extract_entities` — NUL byte v jméně tise rozsekne entitu

**Input**: `Jan\x00Novák` (12 bytes UTF-8 s NUL)
**Očekáváno**: 1 entita typu osoba "Jan Novák", nebo warning o NUL znaku
**Skutečnost**: 1 entita "Jan" (typ `pf` křestní jméno) — "Novák" se ztratil.
**Dopad**: silent data loss. Pokud OCR / kopírování z PDF vloží NUL byte, jméno se v PII pipeline rozpadne.
**Fix návrh**: do `validation.py` přidat strip / warning na C0 control chars (0x00-0x1F kromě tab/lf/cr).

### [A6, C9] `extract_entities` — emoji-only → `detected_language=czech`

**Input**: `🦊🌍🇨🇿` (A6), `𓂀 Hieroglyph and Jan Novák. 🦊` (C9)
**Skutečnost**: heuristika fallback na češtinu i pro vstupy bez latinky.
**Dopad**: misleading API — user vidí `detected_language: czech` u textu, kde žádná čeština není.
**Fix návrh**: pokud žádný CZ marker nenalezen, vrátit `detected_language: null` nebo `"unknown"`.

### [A2, A3, A15] whitespace input → `model: null` (tichý no-op)

**Input**: `"   "`, `"\n\n\n\t"` (extract_entities, correct_text)
**Skutečnost**: tool vrátí prázdný výsledek s `model: null` — bez ValidationError, bez warningu.
**Dopad**: API contract nekonzistence — empty raises, whitespace tiše projde s null modelem.
**Fix návrh**: buď validovat (raise) jako empty, nebo přidat warning "whitespace-only input, no model invoked".

### [C2, C3] zero-width / zwj v jménu — entity text obsahuje invisible char

**Input**: `Jan​Novák` (ZWS), `Jan‍Novák` (ZWJ)
**Skutečnost**: 1 entita osoba "Jan​Novák" — ZWS zachováno v `text` poli.
**Dopad**: downstream matching (např. dedup v `anonymize` placeholder_mode) selže — "Jan Novák" != "Jan​Novák".
**Fix návrh**: ZWS/ZWJ stripnout buď v `_prepare_input`, nebo v entity post-processingu.

### [H3 vedlejší] anonymized text drops opening parenthesis

**Input**: `Pan Jiří Pluhařík (Ostrava) podepsal smlouvu s ABC s.r.o.`
**Skutečnost**: anonymized `Pan OSOBA1 OSOBA2 MESTO1) podepsal smlouvu s FIRMA1` — chybí opening `(`, dotečku, taky chybí.
**Dopad**: kosmetická porucha textu — nedělá PII leak, ale anonymized output má sloučené znaky.
**Fix návrh**: revidovat regex sentinel restore, který odstraní interpunkci společně s tokenem.

---

## Patterns observed

1. **MasKIT regex pre-pass postihuje jen jeden variant RČ (s lomítkem)**. Formáty bez lomítka (`8003121234`) a hybridní (`800312` jako standalone 6-digit) projdou anonymizací netknuté. Stejný pattern u čísel účtů — IBAN se chytí, `19-2000145399/0800` ne. (P0 — E2, E6.)

2. **Velké vstupy (>10KB) způsobí UFAL upstream ReadTimeout** napříč nástroji (NameTag, MasKIT, PONK, Translator). 60s default timeout je málo, ale i 180s nestačí na 11KB translate. Wrapper retry logic dělá svou práci (vidno v stderr), ale uživatel dostane null/timeout bez čistšího error message. (P1/P2 — B2-B7.)

3. **Anonymize není idempotentní** — placeholdery v re-volání vytvoří nové placeholdery, někdy s narušením předchozích (`ENTITA1` → `ENTITA1ULICE1`). Pro pipeline `anonymize → review → re-anonymize` to může způsobit nečekané změny. (P1 — H1.)

4. **NameTag detekuje placeholdery jako entity** — text `FIRMA1` (z anonymize) extract_entities klasifikuje jako `if` (firma/společnost). To dává smysl tokenizerově (FIRMA = známé slovo), ale komplikuje cross-tool pipeline. (P2 — H3.)

5. **Whitespace a degenerate inputs handluje server "tichým no-op"** místo konzistentního validation errorem. (P3 — A2/A3/A15.)

6. **Encoding edge cases (ZWS/ZWJ, NUL byte) se propagují do entity textu** bez warningu — pro downstream pipeline neviditelný foot-gun. (P2/P3 — A18, C2, C3.)

7. **Auto-detect jazyka padá na "czech" pro vstupy bez latinky** (emoji, hieroglyfy). Heuristika by měla mít explicit "unknown" fallback. (P3 — A6, C9.)

---

## Suggested fixes for v0.7.6

### Priority 1 — bezpečnost (P0)

- [ ] **`maskit_patterns.py`**: rozšířit RČ regex o varianty bez lomítka — `8003121234` (10 digits), `800312` standalone (6 digits, ambiguous; možná za feature flag s warning), `80-03-12/1234` (s pomlčkami).
- [ ] **`maskit_patterns.py`**: rozšířit cislo-uctu regex — formát `prefix-base/bank` (`19-2000145399/0800`) zatím nechytá, jen IBAN.
- [ ] Přidat regression test pro 102/102 PII operations z Jiříkova batche + nový test pro variantní formáty.

### Priority 2 — kvalita / robustnost (P1-P2)

- [ ] **`validation.py`**: bumpnout MAX_INPUT_BYTES dolů a / nebo přidat chunking helper pro velké texty; momentální 500KB hard cap je vysoký vzhledem k tomu, že UFAL upstream timeoutuje na 10KB-50KB.
- [ ] **`maskit.py`**: idempotence fix — když input obsahuje sentinely formátu `OSOBA[0-9]+`, `MESTO[0-9]+` atd., přeskočit je v MasKIT pipeline.
- [ ] **`server.py`**: bumpnout default timeout per tool, zvlášť pro `translate_text` (doc mode) a `anonymize` (4 HTTP roundtripy v pipeline).
- [ ] **`validation.py`**: stripnout C0 control chars (0x00-0x1F kromě \t\n\r) a vrátit warning.
- [ ] **`validation.py`**: stripnout zero-width chars (U+200B, U+200C, U+200D, U+FEFF) a vrátit warning — analogicky k PUA.
- [ ] **`nametag.py`**: post-process entity text — strip ZW chars z `entities[].text` a `entities[].tokens`.

### Priority 3 — API consistency (P3)

- [ ] **`langdetect.py`**: pro vstupy bez latinkových znaků vrátit `detected_language=null` nebo `"unknown"` místo fallback na `czech`.
- [ ] **`validation.py`**: whitespace-only inputs → raise `ValidationError` jako empty, nebo přidat warning + skip server call deterministicky.
- [ ] **`maskit.py`**: review sentinel-restore step — opening parenthesis (`(`) chybí v anonymized output (viz H3 příklad).

### Priority 4 — runner / client (P3, externí)

- [ ] V testovacím MCP klientovi bumpnout asyncio subprocess `limit=2**20` (1MB) — defaultní 64KB stačí na běžné odpovědi, ale překlad >10KB může vrátit JSON-RPC odpověď nad limit. Tohle byl bug v testovacím klientovi, ne v UFAL MCP — uvedeno pro úplnost.

---

## Reprodukovatelnost

Kompletní test suite v `/home/buggy1111/dev/ufal-mcp-stress-v076/`:

```bash
# Vše (94 testů — 89 maticových + 5 cross-tool chain)
python runner/run_stress.py
python runner/cross_tool.py

# Jeden test
python runner/run_stress.py --id E2

# Jen kategorie
python runner/run_stress.py --category E

# Jen nástroj
python runner/run_stress.py --tool anonymize

# Regenerovat report
python runner/analyze.py
```

Raw výsledky per test: `results/raw/<id>.json`.

