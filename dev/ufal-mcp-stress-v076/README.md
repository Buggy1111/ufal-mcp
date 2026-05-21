# ÚFAL MCP — Stress Test v0.7.6

Adversarial test suite pro `ufal-mcp` v0.7.5 → hledání bugů pro v0.7.6.
ÚFAL = Ústav formální a aplikované lingvistiky, **MFF UK / Univerzita Karlova v Praze**.

## Cíl
Najít reprodukovatelné bugy napříč všemi 6 nástroji a zlepšit robustnost.

## Nástroje pod testem
1. `extract_entities` — NameTag 3 (CNEC 2.0 + UNER multilingual)
2. `anonymize` — MasKIT + wrapper pipeline (8 kroků)
3. `analyze_morphology` — UDPipe 2 (961 modelů)
4. `check_readability` — PONK (4 feature sety)
5. `correct_text` — Korektor (spellcheck / strict / diacritics / strip)
6. `translate_text` — Charles Translator (8 jazyků, 17 párů)

## Kategorie testů (A-I)
| ID | Název | Co testuje |
|---|---|---|
| A | Degenerate input | "", whitespace, emoji, single char, control chars |
| B | Size extrémy | 1B, 10KB, 100KB, 500KB+ (validation limit) |
| C | Encoding/Unicode | BOM, zero-width, RTL, kombinující znaky |
| D | Language mixing | CZ+SK+EN+DE+PL+UK code-switching |
| E | PII adversarial | RČ formáty, hybrid PII, OCR typos, fake PII |
| F | Domain stress | legal / medical / technical / social |
| G | Adversarial payload | HTML/JSON/XML v textu, placeholdery v inputu, prompt injection |
| H | Cross-tool / idempotence | `f(f(x))==f(x)`, translate round-trip |
| I | Concurrency | asyncio paralelní volání |

## Použití
```bash
# 1. Spustit celou matrici
python runner/run_stress.py

# 2. Spustit jen jednu kategorii
python runner/run_stress.py --category E

# 3. Spustit jen jeden nástroj
python runner/run_stress.py --tool anonymize
```

Raw výstupy: `results/raw/`
Bug report: `results/BUGS-v076.md`
Demo report: `demo/stress-report.md`
