# Multilingual test — ÚFAL MCP

**Datum**: 2026-05-21 20:35
**Languages tested**: 11

## Per-language summary

| Lang | Bytes | Entities | Lang detected | Tokens | UDPipe model | Translate (cs) |
|---|---:|---:|---|---:|---|---|
| sk | 1244 | 70 | slovak (using cz-cnec for better coverage) | 225 | `slovak-snk-ud-2.17-251125` | — |
| en | 1079 | 21 | english | 212 | `english-ewt-ud-2.17-251125` | 1.28s / 1002 chars |
| de | 1192 | 20 | german | 217 | `german-gsd-ud-2.17-251125` | 3.17s / 1098 chars |
| pl | 1254 | 24 | polish | 238 | `polish-pdb-ud-2.17-251125` | 3.86s / 1088 chars |
| uk | 1779 | 22 | ukrainian | 233 | `ukrainian-iu-ud-2.17-251125` | 6.07s / 1053 chars |
| ru | 1939 | 22 | russian | 260 | `russian-syntagrus-ud-2.17-251125` | 7.04s / 1312 chars |
| fr | 1261 | 21 | french | 216 | `french-gsd-ud-2.17-251125` | 2.82s / 1118 chars |
| hi | 2284 | 20 | hindi | 210 | `hindi-hdtb-ud-2.17-251125` | 0.0s / ? chars |
| es | 1300 | 19 | spanish | 235 | `spanish-ancora-ud-2.17-251125` | — |
| it | 1202 | 21 | italian | 225 | `italian-isdt-ud-2.17-251125` | — |
| ar | 1802 | 24 | arabic | 246 | `arabic-padt-ud-2.17-251125` | — |

## Per-language detail

### sk — slovak

- **extract_entities**: 70 entities, model `nametag3-czech-cnec2.0-240830`, detected `slovak (using cz-cnec for better coverage)`
  - Top types: n_=10, město/obec=7, osoba=6, příjmení=6, křestní jméno=5
  - Sample entities:
    - `KRAJSKÝ SÚD V` (úřad/instituce)
    - `BRATISLAVE` (město/obec)
    - `Záhradnícka` (ulice/náměstí)
    - `10` (hodnota)
    - `813 66` (PSČ)
- **analyze_morphology**: 225 tokens, 22 sentences, model `slovak-snk-ud-2.17-251125`
  - First-sentence sample tokens:
    - `KRAJSKÝ` → lemma `krajský` (ADJ)
    - `SÚD` → lemma `súd` (PROPN)
    - `V` → lemma `v` (ADP)
    - `BRATISLAVE` → lemma `bratislava` (PROPN)
- **translate_text**: skipped — not supported by Charles Translator
- **anonymize** (CZ-only, degradation test on first 1000B): ok=True, 48 replacements

### en — english

- **extract_entities**: 21 entities, model `nametag3-multilingual-uner-250203`, detected `english`
  - Top types: lokace/místo=11, osoba=6, organizace=4
  - Sample entities:
    - `DISTRICT COURT` (organizace)
    - `DISTRICT` (lokace/místo)
    - `NEW` (organizace)
    - `YORK` (lokace/místo)
    - `Brooklyn` (lokace/místo)
- **analyze_morphology**: 212 tokens, 13 sentences, model `english-ewt-ud-2.17-251125`
  - First-sentence sample tokens:
    - `DISTRICT` → lemma `District` (PROPN)
    - `COURT` → lemma `Court` (PROPN)
    - `FOR` → lemma `for` (ADP)
    - `THE` → lemma `the` (DET)
    - `EASTERN` → lemma `Eastern` (ADJ)
- **translate_text** (en→cs): 1002 chars in 1.28s, pair `en-cs`
  - Translated excerpt: *OKRESNÍ SOUD PRO VÝCHODNÍ DISTRIKT NEW YORK 225 Cadman Plaza East, Brooklyn, NY 11201 Tel.: +1 (718) 613-2000, Email: clerk@nyed.uscourts.gov  ROZSUDEK  Případ č. 1:24-cv-04521-JMA Filed: April 15, 20...*
- **anonymize** (CZ-only, degradation test on first 1000B): ok=True, 29 replacements

### de — german

- **extract_entities**: 20 entities, model `nametag3-multilingual-uner-250203`, detected `german`
  - Top types: lokace/místo=10, osoba=6, organizace=4
  - Sample entities:
    - `LANDGERICHT MÜNCHEN` (organizace)
    - `Prielmayerstraße` (lokace/místo)
    - `München` (lokace/místo)
    - `Anna Weber` (osoba)
    - `Klaus Müller` (osoba)
- **analyze_morphology**: 217 tokens, 17 sentences, model `german-gsd-ud-2.17-251125`
  - First-sentence sample tokens:
    - `LANDGERICHT` → lemma `Landgericht` (PROPN)
    - `MÜNCHEN` → lemma `MÜNCHEN` (PROPN)
    - `I` → lemma `I` (PROPN)
    - `Prielmayerstraße` → lemma `Prielmayerstrasse` (PROPN)
    - `7` → lemma `7` (PROPN)
- **translate_text** (de→cs): 1098 chars in 3.17s, pair `de->en->cs`
  - Translated excerpt: *MNICHOVÝ SOUD Prielmayerstraße 7, 80335 Mnichov Tel: +49 89 5597-01, Email: poststelle@lg-m1.bayern.de  ROZSUDEK Ve jménu lidu  Referenční číslo: 14 O 4521/24 Oznámeno 18. dubna 2024 předsedkyní senát...*
- **anonymize** (CZ-only, degradation test on first 1000B): ok=True, 38 replacements

### pl — polish

- **extract_entities**: 24 entities, model `nametag3-multilingual-uner-250203`, detected `polish`
  - Top types: lokace/místo=12, organizace=6, osoba=6
  - Sample entities:
    - `SĄD OKRĘGOWY W WARSZAWIE` (organizace)
    - `al. Solidarności` (lokace/místo)
    - `Warszawa` (lokace/místo)
    - `Rzeczypospolitej Polskiej` (lokace/místo)
    - `SSO` (organizace)
- **analyze_morphology**: 238 tokens, 14 sentences, model `polish-pdb-ud-2.17-251125`
  - First-sentence sample tokens:
    - `SĄD` → lemma `sąd` (NOUN)
    - `OKRĘGOWY` → lemma `okręgowy` (ADJ)
    - `W` → lemma `w` (ADP)
    - `WARSZAWIE` → lemma `Warszawa` (PROPN)
    - `al` → lemma `aleja` (NOUN)
- **translate_text** (pl→cs): 1088 chars in 3.86s, pair `pl->en->cs`
  - Translated excerpt: *ROUND COURT IN WARSAW 127 Solidarności Avenue, 00-898 Varšava Tel.: +48 22 440 80 00, e-mail: biuro.podawcze@warszawa.so.gov.pl  ROUND Za Polskou republiku  Podepsaný akt: XXV C 1487/24 Zveřejněno dne...*
- **anonymize** (CZ-only, degradation test on first 1000B): ok=True, 49 replacements

### uk — ukrainian

- **extract_entities**: 22 entities, model `nametag3-multilingual-uner-250203`, detected `ukrainian`
  - Top types: lokace/místo=11, osoba=7, organizace=4
  - Sample entities:
    - `КИЇВСЬКИЙ АПЕЛЯЦІЙНИЙ СУД` (organizace)
    - `вул. Володимирська` (lokace/místo)
    - `Київ` (lokace/místo)
    - `Олександрою Петренко` (osoba)
    - `Андрій Шевченко` (osoba)
- **analyze_morphology**: 233 tokens, 11 sentences, model `ukrainian-iu-ud-2.17-251125`
  - First-sentence sample tokens:
    - `КИЇВСЬКИЙ` → lemma `київський` (ADJ)
    - `АПЕЛЯЦІЙНИЙ` → lemma `апеляційний` (ADJ)
    - `СУД` → lemma `СУД` (NOUN)
    - `вул` → lemma `вул.` (NOUN)
    - `.` → lemma `.` (PUNCT)
- **translate_text** (uk→cs): 1053 chars in 6.07s, pair `uk-cs`
  - Translated excerpt: *KYJEV – africký soudní dvůr Hořava st. Vladimirská 15, 01601 Kyjev tel.: +380 44 254 1000, e-mail: pidatelna@court.gov.ua  ŘEŠENÍ Jménem Ukrajiny  Případ č. 824/4521/24 Rozhodnuto 25. dubna 2024 soudk...*
- **anonymize** (CZ-only, degradation test on first 1000B): ok=True, 12 replacements

### ru — russian

- **extract_entities**: 22 entities, model `nametag3-multilingual-uner-250203`, detected `russian`
  - Top types: lokace/místo=12, osoba=6, organizace=4
  - Sample entities:
    - `МОСКОВСКИЙ ГОРОДСКОЙ СУД` (organizace)
    - `ул. Богородский Вал, 8` (lokace/místo)
    - `Москва` (lokace/místo)
    - `Российской Федерации` (lokace/místo)
    - `Натальей Сергеевной Ивановой` (osoba)
- **analyze_morphology**: 260 tokens, 13 sentences, model `russian-syntagrus-ud-2.17-251125`
  - First-sentence sample tokens:
    - `МОСКОВСКИЙ` → lemma `московский` (ADJ)
    - `ГОРОДСКОЙ` → lemma `городской` (ADJ)
    - `СУД` → lemma `суд` (NOUN)
    - `ул.` → lemma `улица` (NOUN)
    - `Богородский` → lemma `богородский` (ADJ)
- **translate_text** (ru→cs): 1312 chars in 7.04s, pair `ru-cs`
  - Translated excerpt: *Moskevský městský soud Bogorodskij Val, 8, 107076 Moskva [.m] masterhost - ���������������� ������� ����� centra.ru ������ ���� � ������ ������ ��������� � ����������� ���������.  ŘEŠENÍ Jménem Ruské ...*
- **anonymize** (CZ-only, degradation test on first 1000B): ok=True, 10 replacements

### fr — french

- **extract_entities**: 21 entities, model `nametag3-multilingual-uner-250203`, detected `french`
  - Top types: lokace/místo=11, osoba=6, organizace=4
  - Sample entities:
    - `TRIBUNAL JUDICIAIRE DE PARIS` (organizace)
    - `de Paris` (lokace/místo)
    - `Paris` (lokace/místo)
    - `Catherine Dubois` (osoba)
    - `Pierre Martin` (osoba)
- **analyze_morphology**: 216 tokens, 12 sentences, model `french-gsd-ud-2.17-251125`
  - First-sentence sample tokens:
    - `TRIBUNAL` → lemma `tribunal` (NOUN)
    - `JUDICIAIRE` → lemma `judiciaire` (ADJ)
    - `DE` → lemma `de` (ADP)
    - `PARIS` → lemma `PARIS` (PROPN)
    - `Parvis` → lemma `Parvis` (PROPN)
- **translate_text** (fr→cs): 1118 chars in 2.82s, pair `fr->en->cs`
  - Translated excerpt: *SOUDNÍ SOUD PAŘÍŽ Parvis z Pařížského dvora, 75017 Paris Tel: +33 1 44 32 51 51, e-mail: greffe@tj-paris.justice.fr  ROZSUDEK Jménem francouzského lidu  RG č. 24/04521 Doručeno dne 30. dubna 2024 paní...*
- **anonymize** (CZ-only, degradation test on first 1000B): ok=True, 24 replacements

### hi — hindi

- **extract_entities**: 20 entities, model `nametag3-multilingual-uner-250203`, detected `hindi`
  - Top types: lokace/místo=11, osoba=6, organizace=3
  - Sample entities:
    - `दिल्ली उच्च न्यायालय` (organizace)
    - `शेरशाह रोड` (lokace/místo)
    - `नई दिल्ली` (lokace/místo)
    - `भारत` (lokace/místo)
    - `सुनीता शर्मा` (osoba)
- **analyze_morphology**: 210 tokens, 10 sentences, model `hindi-hdtb-ud-2.17-251125`
  - First-sentence sample tokens:
    - `दिल्ली` → lemma `दिल्ली` (PROPN)
    - `उच्च` → lemma `उच्च` (PROPN)
    - `न्यायालय` → lemma `न्यायालय` (PROPN)
    - `शेरशाह` → lemma `शेरशाह` (PROPN)
    - `रोड` → lemma `रोड` (PROPN)
- **translate_text** (hi→cs): ? chars in 0.0s, pair `?`
- **anonymize** (CZ-only, degradation test on first 1000B): ok=True, 9 replacements

### es — spanish

- **extract_entities**: 19 entities, model `nametag3-multilingual-uner-250203`, detected `spanish`
  - Top types: lokace/místo=10, osoba=6, organizace=3
  - Sample entities:
    - `MADRID` (lokace/místo)
    - `Calle Capitán Haya` (lokace/místo)
    - `Madrid` (lokace/místo)
    - `Carmen Fernández` (osoba)
    - `D. Carlos Ramírez García` (osoba)
- **analyze_morphology**: 235 tokens, 12 sentences, model `spanish-ancora-ud-2.17-251125`
  - First-sentence sample tokens:
    - `JUZGADO` → lemma `juzgado` (PROPN)
    - `DE` → lemma `de` (ADP)
    - `PRIMERA` → lemma `Primera` (PROPN)
    - `INSTANCIA` → lemma `INSTANCIA` (PROPN)
    - `N.º` → lemma `N.º` (PROPN)
- **translate_text**: skipped — not supported by Charles Translator
- **anonymize** (CZ-only, degradation test on first 1000B): ok=True, 32 replacements

### it — italian

- **extract_entities**: 21 entities, model `nametag3-multilingual-uner-250203`, detected `italian`
  - Top types: lokace/místo=11, osoba=6, organizace=4
  - Sample entities:
    - `TRIBUNALE DI MILANO` (organizace)
    - `Via Carlo Freguglia` (lokace/místo)
    - `Milano` (lokace/místo)
    - `Giulia Romano` (osoba)
    - `Marco Bianchi` (osoba)
- **analyze_morphology**: 225 tokens, 18 sentences, model `italian-isdt-ud-2.17-251125`
  - First-sentence sample tokens:
    - `TRIBUNALE` → lemma `tribunale` (NOUN)
    - `DI` → lemma `di` (ADP)
    - `MILANO` → lemma `Milano` (PROPN)
    - `Via` → lemma `Via` (PROPN)
    - `Carlo` → lemma `Carlo` (PROPN)
- **translate_text**: skipped — not supported by Charles Translator
- **anonymize** (CZ-only, degradation test on first 1000B): ok=True, 36 replacements

### ar — arabic

- **extract_entities**: 24 entities, model `nametag3-multilingual-uner-250203`, detected `arabic`
  - Top types: lokace/místo=12, osoba=7, organizace=5
  - Sample entities:
    - `المحكمة الابتدائية بالدار البيضاء` (organizace)
    - `شارع 2 مارس،` (lokace/místo)
    - `الدار البيضاء` (lokace/místo)
    - `المغرب` (lokace/místo)
    - `محمد العلوي.` (osoba)
- **analyze_morphology**: 246 tokens, 9 sentences, model `arabic-padt-ud-2.17-251125`
  - First-sentence sample tokens:
    - `المحكمة` → lemma `مَحكَمَة` (NOUN)
    - `الابتدائية` → lemma `اِبتِدَائِيّ` (ADJ)
    - `بالدار` → lemma `بالدار` (NOUN)
    - `البيضاء` → lemma `أَبيَض` (NOUN)
    - `شارع` → lemma `شَارِع` (NOUN)
- **translate_text**: skipped — not supported by Charles Translator
- **anonymize** (CZ-only, degradation test on first 1000B): ok=True, 6 replacements
