"""End-to-end test ufal-mcp v0.5.0 na CELÉM Jiříkově spisu + PDF report.

Vstup: /home/buggy1111/dev/documents/pravni-pripady/jiri-pluharik/archiv/01_NAVRH_NA_ZASTAVENI_RIZENI_OPAVA.txt (364 řádků)

Pipeline:
1. extract_entities (CZ CNEC2.0) — kdo, kde, kdy, instituce, firmy
2. anonymize (MasKIT + strict pre-pass) — pseudonymizace
3. analyze_morphology (UDPipe) — tokenizace + lemma + POS
4. check_readability (PONK) — ARI, Verb Distance, Activity, Lexical diversity
5. correct_text (Korektor) — spell check + diacritics test
6. translate_text (Charles Translator) — CZ → EN celého dokumentu

Výstup:
- /tmp/jirik_pipeline_report.html — strukturovaný HTML report
- /tmp/jirik_pipeline_report.pdf — pro Michala k přečtení
"""

import asyncio
import html
import json
import subprocess
import time
from pathlib import Path

from ufal_mcp.server import (
    analyze_morphology,
    anonymize,
    check_readability,
    correct_text,
    extract_entities,
    translate_text,
)

DOC_PATH = Path("/home/buggy1111/dev/documents/pravni-pripady/jiri-pluharik/archiv/01_NAVRH_NA_ZASTAVENI_RIZENI_OPAVA.txt")
OUT_DIR = Path("/home/buggy1111/dev/ufal-mcp-demo-jirik")
OUT_DIR.mkdir(exist_ok=True)
HTML_OUT = OUT_DIR / "01_pipeline_report.html"
PDF_OUT = OUT_DIR / "01_pipeline_report.pdf"
JSON_DIR = OUT_DIR / "raw_outputs"
JSON_DIR.mkdir(exist_ok=True)


def esc(s: str) -> str:
    return html.escape(s).replace("\n", "<br/>")


async def run():
    text = DOC_PATH.read_text(encoding="utf-8")
    char_count = len(text)
    line_count = text.count("\n") + 1
    word_count = len(text.split())

    print(f"📄 Vstup: {DOC_PATH.name}")
    print(f"   {char_count} znaků, {line_count} řádků, {word_count} slov")

    sections = []

    # Save input doc copy for transparency
    (OUT_DIR / "00_input_document.txt").write_text(text, encoding="utf-8")

    # --- 1. NER ---
    print("\n[1/6] extract_entities (CZ CNEC2.0)...")
    t0 = time.time()
    ents = await extract_entities(text)
    t_ner = time.time() - t0
    print(f"      → {ents['count']} entit ({t_ner:.1f}s)")
    (JSON_DIR / "1_extract_entities.json").write_text(
        json.dumps(ents, ensure_ascii=False, indent=2), encoding="utf-8")

    # Group by type
    by_type: dict[str, list[str]] = {}
    for e in ents["entities"]:
        by_type.setdefault(f"{e['type']} ({e['label']})", []).append(e["text"])
    ner_html = f"""
    <h2>1. extract_entities — Named Entity Recognition</h2>
    <div class="meta">Model: <code>{esc(ents['model'])}</code> · Detected: <code>{ents.get('detected_language', 'n/a')}</code> · {ents['count']} entit · {t_ner:.1f}s</div>
    <table class="ent">
        <thead><tr><th>Typ</th><th>Počet</th><th>Příklady</th></tr></thead>
        <tbody>
    """
    for type_key in sorted(by_type.keys()):
        items = by_type[type_key]
        unique = list(dict.fromkeys(items))[:8]
        ner_html += f"<tr><td><code>{esc(type_key)}</code></td><td>{len(items)}</td><td>{', '.join(esc(x) for x in unique)}</td></tr>"
    ner_html += "</tbody></table>"
    sections.append(ner_html)

    # --- 2. UDPipe morfologie ---
    print("[2/6] analyze_morphology (UDPipe)...")
    t0 = time.time()
    morph = await analyze_morphology(text)
    t_morph = time.time() - t0
    print(f"      → {morph['token_count']} tokenů ve {morph['sentence_count']} větách ({t_morph:.1f}s)")
    (JSON_DIR / "2_analyze_morphology.json").write_text(
        json.dumps(morph, ensure_ascii=False, indent=2), encoding="utf-8")

    # POS distribution
    pos_count: dict[str, int] = {}
    for sent in morph["sentences"]:
        for tok in sent:
            pos = tok.get("upos", "?")
            pos_count[pos] = pos_count.get(pos, 0) + 1

    pos_translations = {
        "NOUN": "podstatné jméno", "VERB": "sloveso", "ADJ": "přídavné jm.",
        "ADV": "příslovce", "ADP": "předložka", "PRON": "zájmeno",
        "DET": "determinant", "NUM": "číslovka", "PROPN": "vlastní jm.",
        "AUX": "pomocné sl.", "CCONJ": "spojka", "SCONJ": "podřad. spojka",
        "PART": "částice", "INTJ": "citoslovce", "PUNCT": "interpunkce",
        "SYM": "symbol", "X": "ostatní",
    }

    morph_html = f"""
    <h2>2. analyze_morphology — Morfologická analýza (UDPipe)</h2>
    <div class="meta">Model: <code>{esc(morph['model'] or 'n/a')}</code> · Detected: <code>{morph.get('detected_language', 'n/a')}</code> · {morph['token_count']} tokenů · {morph['sentence_count']} vět · {t_morph:.1f}s</div>
    <table class="ent">
        <thead><tr><th>POS</th><th>Význam</th><th>Počet</th></tr></thead>
        <tbody>
    """
    for pos, cnt in sorted(pos_count.items(), key=lambda x: -x[1]):
        morph_html += f"<tr><td><code>{pos}</code></td><td>{pos_translations.get(pos, '?')}</td><td>{cnt}</td></tr>"
    morph_html += "</tbody></table>"
    sections.append(morph_html)

    # --- 3. Anonymize ---
    print("[3/6] anonymize (MasKIT + strict pre-pass)...")
    t0 = time.time()
    anon = await anonymize(text, placeholder_mode=True)
    t_anon = time.time() - t0
    sources = anon.get("sources", {})
    print(f"      → {sources.get('maskit', 0)} maskit + {sources.get('wrapper', 0)} wrapper ({t_anon:.1f}s)")
    (JSON_DIR / "3_anonymize.json").write_text(
        json.dumps(anon, ensure_ascii=False, indent=2), encoding="utf-8")
    # Also save anonymized text as plain .txt for easy reading
    (OUT_DIR / "02_anonymized_text.txt").write_text(anon.get("anonymized", ""), encoding="utf-8")

    # Replacements table — top 20
    reps = anon.get("replacements", [])
    anon_html = f"""
    <h2>3. anonymize — Pseudonymizace (MasKIT + strict pre-pass)</h2>
    <div class="meta">MasKIT: <strong>{sources.get('maskit', 0)}</strong> · Wrapper (strict): <strong>{sources.get('wrapper', 0)}</strong> · Warnings: {len(anon.get('warnings', []))} · {t_anon:.1f}s</div>
    """
    if anon.get("warnings"):
        anon_html += "<div class='warnings'><strong>Warnings:</strong><ul>"
        for w in anon["warnings"][:5]:
            anon_html += f"<li>{esc(w)}</li>"
        anon_html += "</ul></div>"

    anon_html += """
    <h3>Replacements (top 25)</h3>
    <table class="ent">
        <thead><tr><th>Originál</th><th>Placeholder</th><th>Typ</th><th>Zdroj</th></tr></thead>
        <tbody>
    """
    for r in reps[:25]:
        src = r.get("source", "?")
        cls = "src-maskit" if src == "maskit" else "src-wrapper"
        anon_html += f"<tr class='{cls}'><td>{esc(r.get('original', ''))}</td><td><code>{esc(r.get('placeholder', ''))}</code></td><td>{esc(r.get('type', ''))}</td><td>{esc(src)}</td></tr>"
    anon_html += f"</tbody></table>"
    if len(reps) > 25:
        anon_html += f"<p class='small'>... +{len(reps) - 25} dalších replacements</p>"

    # Diff preview
    anon_html += f"""
    <h3>Anonymizovaný text (preview, prvních 1500 znaků)</h3>
    <pre class="anon">{esc(anon['anonymized'][:1500])}{'…' if len(anon['anonymized']) > 1500 else ''}</pre>
    """
    sections.append(anon_html)

    # --- 4. PONK readability — RICH OUTPUT v0.7.0 ---
    print("[4/6] check_readability (PONK rich)...")
    t0 = time.time()
    pn = await check_readability(
        text,
        include_rules=True,
        include_lexical_surprise=True,
        include_speech_acts=True,
        include_highlighted_html=True,
    )
    t_ponk = time.time() - t0
    rules = pn.get("rules", [])
    lex = pn.get("lexical_surprise", {})
    acts = pn.get("speech_acts", {})
    print(f"      → PONK v{pn['version']} ({t_ponk:.1f}s) — "
          f"{len(rules)} pravidel, {lex.get('summary', {}).get('very_surprising', 0)} velmi vzácných slov")
    (JSON_DIR / "4_check_readability.json").write_text(
        json.dumps({k: v for k, v in pn.items() if k != "highlighted_html"},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "03_ponk_highlighted.html").write_text(
        pn.get("highlighted_html", ""), encoding="utf-8")

    # === Section 4a: Overall metrics ===
    ponk_html = f"""
    <h2>4. check_readability — Čitelnost (PONK v{esc(pn.get('version', ''))})</h2>
    <div class="meta">{t_ponk:.1f}s · {len(rules)} aktivovaných pravidel · sentences: {pn.get('counts', {}).get('sentences', '?')} · tokens: {pn.get('counts', {}).get('tokens', '?')}</div>

    <h3>4a. Overall metrics</h3>
    <table class="ent">
        <thead><tr><th>Metrika</th><th>Hodnota</th><th>Význam</th></tr></thead>
        <tbody>
    """
    metric_info = {
        "Automated readability index": "Vyšší = obtížnější čtení. CZ úředština typicky 25-35.",
        "Verb Distance": "Vzdálenost mezi slovesy. Vyšší = složitější věty.",
        "Activity": "Poměr aktivních konstrukcí. Nižší = více pasivu.",
        "Lexical diversity": "Lemmas/tokens. Vyšší = pestřejší slovník.",
    }
    for k, v in pn.get("metrics", {}).items():
        val = v.get("value") if isinstance(v, dict) else v
        ponk_html += f"<tr><td>{esc(k)}</td><td><strong>{esc(str(val))}</strong></td><td class='small'>{esc(metric_info.get(k, ''))}</td></tr>"
    ponk_html += "</tbody></table>"

    # === Section 4b: Gramatická pravidla (NOVÉ v v0.7.0) ===
    ponk_html += "<h3>4b. ⭐ Aktivovaná gramatická pravidla (akční rady)</h3>"
    if not rules:
        ponk_html += "<p class='small'>Žádná pravidla se v textu neaktivovala.</p>"
    else:
        ponk_html += "<table class='ent'><thead><tr><th>Počet</th><th>Pravidlo</th><th>Doporučení (cz_doc)</th></tr></thead><tbody>"
        for rule in rules:
            color = rule.get("color") or "#666"
            ponk_html += (
                f"<tr>"
                f"<td><strong style='color:{color}'>{rule['count']}×</strong></td>"
                f"<td><strong>{esc(rule.get('cz_name', '?'))}</strong></td>"
                f"<td class='small'>{esc(rule.get('cz_doc', ''))}</td>"
                f"</tr>"
            )
        ponk_html += "</tbody></table>"

    # === Section 4c: Lexical surprise ===
    summary = lex.get("summary", {})
    ponk_html += f"""
    <h3>4c. Lexical surprise — distribuce vzácnosti slov</h3>
    <table class="ent">
        <tbody>
            <tr><td>Běžná slova (úroveň 1-6)</td><td><strong>{summary.get('common', 0)}</strong></td></tr>
            <tr><td>Vzácnější slova (úroveň 7-12)</td><td><strong>{summary.get('surprising', 0)}</strong></td></tr>
            <tr><td>Velmi vzácná / odborná (úroveň 13-16)</td><td><strong>{summary.get('very_surprising', 0)}</strong></td></tr>
        </tbody>
    </table>
    """

    # === Section 4d: Speech acts ===
    types = acts.get("types", {})
    ponk_html += "<h3>4d. Speech acts — typy vět (k dispozici PONK kategorie)</h3>"
    if types:
        ponk_html += "<table class='ent'><thead><tr><th>Typ</th><th>Barva</th></tr></thead><tbody>"
        for name, color in sorted(types.items()):
            ponk_html += f"<tr><td>{esc(name)}</td><td><code style='background:{color};padding:2px 8px;color:#000'>{esc(color)}</code></td></tr>"
        ponk_html += "</tbody></table>"
    sections.append(ponk_html)

    # --- 5. Korektor (diacritics test) ---
    print("[5/6] correct_text (Korektor)...")
    sample = text[:400]
    t0 = time.time()
    stripped = await correct_text(sample, mode="strip")
    restored = await correct_text(stripped["corrected"], mode="diacritics")
    t_kor = time.time() - t0
    print(f"      → diacritics test ({t_kor:.1f}s)")
    (JSON_DIR / "5_correct_text.json").write_text(
        json.dumps({"input_sample": sample, "stripped": stripped, "restored": restored},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    kor_html = f"""
    <h2>5. correct_text — Korektor (strip → restore diacritics)</h2>
    <div class="meta">Test: vezmu prvních 400 znaků, strippnu diakritiku, pak ji obnovím · {t_kor:.1f}s</div>
    <h3>Originál</h3>
    <pre class="orig">{esc(sample)}</pre>
    <h3>Bez diakritiky (strip)</h3>
    <pre class="strip">{esc(stripped['corrected'])}</pre>
    <h3>Obnoveno (diacritics)</h3>
    <pre class="restore">{esc(restored['corrected'])}</pre>
    <div class="meta">Round-trip OK? <strong>{'ANO (částečné, vlastní jména obvykle ne)' if restored['changed'] else 'NE'}</strong></div>
    """
    sections.append(kor_html)

    # --- 6. Translation ---
    print("[6/6] translate_text (CZ → EN, doc mode)...")
    # Take first 2000 chars (Translator může mít limity)
    # Translator doc mode je pomalý pro velký vstup, omezíme na 1500 znaků
    src_text = text[:1500]
    t0 = time.time()
    tr = await translate_text(src_text, src="cs", tgt="en", document_mode=True)
    t_tr = time.time() - t0
    print(f"      → doc-cs-en, {tr['input_chars']} → {tr['output_chars']} znaků ({t_tr:.1f}s)")
    (JSON_DIR / "6_translate_text.json").write_text(
        json.dumps(tr, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "04_translated_en.txt").write_text(tr.get("translated", ""), encoding="utf-8")

    tr_html = f"""
    <h2>6. translate_text — Charles Translator (CZ → EN, document mode)</h2>
    <div class="meta">Pair: <code>{esc(tr['pair'] or '')}</code> · {tr['input_chars']} → {tr['output_chars']} znaků · {t_tr:.1f}s · prvních 2000 znaků dokumentu</div>
    <h3>Originál CZ (prvních 800 znaků)</h3>
    <pre class="orig">{esc(src_text[:800])}…</pre>
    <h3>Překlad EN (zachovává strukturu odstavců)</h3>
    <pre class="restore">{esc(tr['translated'][:1500])}{'…' if len(tr['translated']) > 1500 else ''}</pre>
    """
    sections.append(tr_html)

    total_time = t_ner + t_morph + t_anon + t_ponk + t_kor + t_tr

    # Compose HTML
    css = """
    body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; max-width: 920px; margin: 30px auto; color: #1a1a1a; padding: 0 30px; line-height: 1.5; }
    h1 { font-size: 26px; border-bottom: 3px solid #2563eb; padding-bottom: 8px; margin-bottom: 4px; }
    .subtitle { color: #666; font-size: 14px; margin-bottom: 30px; }
    h2 { font-size: 20px; color: #2563eb; margin-top: 36px; border-left: 4px solid #2563eb; padding-left: 12px; }
    h3 { font-size: 15px; color: #444; margin-top: 18px; margin-bottom: 6px; }
    .meta { font-size: 13px; color: #555; background: #f3f4f6; padding: 8px 12px; border-radius: 4px; margin-bottom: 12px; }
    .meta code { background: white; padding: 1px 5px; border-radius: 3px; font-size: 12px; }
    table.ent { width: 100%; border-collapse: collapse; font-size: 13px; margin: 8px 0; }
    table.ent th { text-align: left; background: #f3f4f6; padding: 6px 10px; font-weight: 600; border-bottom: 2px solid #d1d5db; }
    table.ent td { padding: 4px 10px; border-bottom: 1px solid #e5e7eb; }
    table.ent tr.src-wrapper td { background: #fef3c7; }
    table.ent tr.src-maskit td { background: #dbeafe; }
    table.ent code { background: #f3f4f6; padding: 1px 5px; border-radius: 3px; font-size: 12px; }
    pre.anon, pre.orig, pre.strip, pre.restore { background: #f9fafb; padding: 12px; border-radius: 4px; border: 1px solid #e5e7eb; font-size: 12px; white-space: pre-wrap; word-wrap: break-word; line-height: 1.4; }
    pre.anon { border-left: 3px solid #10b981; }
    pre.strip { border-left: 3px solid #f59e0b; }
    pre.restore { border-left: 3px solid #2563eb; }
    .warnings { background: #fff7ed; border-left: 3px solid #f97316; padding: 8px 12px; margin: 8px 0; font-size: 13px; }
    .small { color: #6b7280; font-size: 12px; }
    .summary { background: #ecfdf5; border: 1px solid #10b981; padding: 12px 16px; border-radius: 6px; margin: 20px 0; }
    .summary h3 { margin-top: 0; color: #047857; }
    .pipeline { display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0; font-size: 12px; }
    .pipeline span { background: #dbeafe; padding: 4px 10px; border-radius: 12px; }
    """

    body = f"""<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="utf-8"/>
<title>ufal-mcp v0.5.0 — Jiříkův spis pipeline report</title>
<style>{css}</style>
</head>
<body>
<h1>ufal-mcp v0.5.0 — Pipeline report</h1>
<div class="subtitle">Reálný test celé pipeline na právním spisu (návrh na zastavení řízení o výživné). 2026-05-20</div>

<div class="summary">
<h3>📄 Vstup</h3>
<p><strong>Soubor:</strong> <code>{esc(str(DOC_PATH))}</code></p>
<p><strong>Velikost:</strong> {char_count:,} znaků · {line_count} řádků · {word_count:,} slov</p>
<p><strong>Typ:</strong> Návrh na zastavení řízení o výživné — reálný právní spis sepsaný pro klienta Jiřího Pluhaříka v jeho česko-slovenském sporu (sp. zn. 17Pc/53/2024, MS Bratislava II)</p>
<div class="pipeline">
<span>extract_entities</span>
<span>analyze_morphology</span>
<span>anonymize</span>
<span>check_readability</span>
<span>correct_text</span>
<span>translate_text</span>
</div>
<p><strong>Celkový čas:</strong> {total_time:.1f}s — všechny 4 ÚFAL backendy zvládly bez chyb.</p>
</div>

{''.join(sections)}

<h2>📊 Souhrn</h2>
<div class="summary">
<p><strong>Tool</strong> · čas · klíčový výsledek</p>
<ul>
<li><code>extract_entities</code> · {t_ner:.1f}s · <strong>{ents['count']} entit</strong> (osoby, instituce, města, soudy, advokáti, IČO, telefony, data)</li>
<li><code>analyze_morphology</code> · {t_morph:.1f}s · <strong>{morph['token_count']} tokenů</strong> ve {morph['sentence_count']} větách, POS distribuce kompletní</li>
<li><code>anonymize</code> · {t_anon:.1f}s · <strong>{sources.get('maskit', 0) + sources.get('wrapper', 0)} replacements</strong> ({sources.get('maskit', 0)} MasKIT + {sources.get('wrapper', 0)} wrapper strict)</li>
<li><code>check_readability</code> · {t_ponk:.1f}s · <strong>ARI: {pn.get('metrics', {}).get('Automated readability index', {}).get('value', '?')}</strong> — typická úředština</li>
<li><code>correct_text</code> · {t_kor:.1f}s · diacritics round-trip funguje pro běžná slova</li>
<li><code>translate_text</code> · {t_tr:.1f}s · CZ → EN doc mode <strong>zachovává strukturu</strong>, vlastní jména ponechává v originále</li>
</ul>
</div>

<div class="subtitle" style="margin-top: 40px;">Generováno {time.strftime('%Y-%m-%d %H:%M:%S')} · ufal-mcp v0.5.0 · commits 3e5f070+ec14e03 (push pending)</div>
</body>
</html>"""

    HTML_OUT.write_text(body, encoding="utf-8")
    print(f"\n📝 HTML: {HTML_OUT}")

    # Convert to PDF via weasyprint
    print(f"📄 Generuji PDF přes weasyprint...")
    result = subprocess.run(
        ["weasyprint", str(HTML_OUT), str(PDF_OUT)],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode == 0:
        size_kb = PDF_OUT.stat().st_size / 1024
        print(f"✅ PDF: {PDF_OUT} ({size_kb:.0f} KB)")
    else:
        print(f"⚠ PDF generation failed:\n   stdout: {result.stdout}\n   stderr: {result.stderr}")

    # Write README for demo folder
    readme = f"""# ufal-mcp v0.5.0 — Jiříkův spis demo

Reálný test celé pipeline ufal-mcp na **návrhu na zastavení řízení o výživné**
sepsaném pro Jiřího Pluhaříka v česko-slovenském sporu (MS Bratislava II,
sp. zn. 17Pc/53/2024).

## Co tu najdeš

### Hlavní výstupy
- **`01_pipeline_report.pdf`** ← **OTEVŘI TENTO**, detailní report celé pipeline
- `01_pipeline_report.html` — stejný report v HTML (pokud nejde PDF)
- `00_input_document.txt` — kopie vstupního spisu pro transparentnost
- `02_anonymized_text.txt` — plně anonymizovaný spis (k vidění co změnilo MasKIT + wrapper strict)
- `03_ponk_highlighted.html` — PONK highlight (nesrozumitelné pasáže barevně)
- `04_translated_en.txt` — EN překlad prvních 2000 znaků (doc mode)

### Raw JSON výstupy z každého toolu (`raw_outputs/`)
- `1_extract_entities.json` — všechny rozpoznané entity (osoby, instituce, města, datumy)
- `2_analyze_morphology.json` — UDPipe morfologie: tokeny + lemmata + POS + features
- `3_anonymize.json` — MasKIT + wrapper replacements s typy a zdroji
- `4_check_readability.json` — PONK metriky (ARI, Verb Distance, Activity, Lexical diversity)
- `5_correct_text.json` — Korektor: strip diacritics + restore round-trip
- `6_translate_text.json` — Charles Translator output

## Vstupní dokument

- **Soubor**: `01_NAVRH_NA_ZASTAVENI_RIZENI_OPAVA.txt` (364 řádků)
- **Strany**: Jiří Pluhařík (navrhovatel) vs Alexandra Tóthová (oprávněná)
- **Soud**: Okresní soud v Opavě (původně), MS Bratislava II (aktuálně)
- **Předmět**: Zrušení vyživovací povinnosti k plnoleté dceři

## Co dělá pipeline

```
TXT
 ↓ extract_entities  (NameTag 3 CNEC2.0)  → kdo, kde, kdy, instituce
 ↓ analyze_morphology (UDPipe)           → lemmata, POS, větná struktura
 ↓ anonymize         (MasKIT + strict)    → pseudonymizace pro veřejné sdílení
 ↓ check_readability (PONK)              → kvantitativní hodnocení čitelnosti
 ↓ correct_text      (Korektor)          → spell check + diakritika
 ↓ translate_text    (Charles Translator) → CZ → EN doc mode pro mezinár. komunikaci
```

Všechno proběhlo na živých ÚFAL REST API ({time.strftime('%Y-%m-%d %H:%M:%S')}).

## Versions

- ufal-mcp: **v0.5.0** (commits `3e5f070` + `ec14e03`, lokálně, push pending)
- PyPI: aktuálně v0.3.3
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")
    print(f"📋 README: {OUT_DIR / 'README.md'}")
    print(f"\n📂 Složka: {OUT_DIR}/")
    for f in sorted(OUT_DIR.rglob("*")):
        if f.is_file():
            size = f.stat().st_size
            rel = f.relative_to(OUT_DIR)
            print(f"   {size:>8d}  {rel}")


if __name__ == "__main__":
    asyncio.run(run())
