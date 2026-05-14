# Demo Video — Drehbuch (10er-Variante)

Ziel: 60–90 Sekunden, das einem Recruiter ohne KI-Hintergrund in einem Take zeigt, dass dieses Projekt mehr ist als ein ChatGPT-Wrapper. Drei Akte. Aufnahme via OBS oder Xbox Game Bar. Zwei Bildschirmregionen sind relevant: ein File-Explorer (links) und ein Terminal (rechts). Keine Stimme — nur kurzer Text als Overlay, weil das in Webseiten-Embeds besser funktioniert (autoplay-stumm ist auf den meisten Browsern Default).

Warum 10 statt 30: 10 Rechnungen lassen sich in einem Take in ~5–6 Minuten Realzeit prozessieren, alle vier Edge-Case-Typen sind sauber vertreten (1 Dup-Paar, 1 Math-Error, 1 Unknown-Vendor mit CHF, 2 Scans) und mit der HTML-Bestellbestätigung kommt ein zweites Dateiformat dazu. Der Zuschauer kann jede Tool-Call-Zeile noch lesen. Mit 30 würden Tempo und Aufmerksamkeit verloren gehen.

---

## Vorbereitung (vor der Aufnahme)

1. Repo frisch aufgeräumt: `output/` und `demo_inputs/` gelöscht (oder der Agent erledigt das gleich via `--fresh`).
2. Frischer Generator-Lauf: `python -m uv run python -m data_generator.generate --n 10 --seed 42`.
   (NICHT vor der Aufnahme den Agent laufen lassen — die Excel soll im Take "wachsen".)
3. Zwei Fenster offen:
   - File Explorer auf `demo_inputs/inbox/` mit Detail-Ansicht (zeigt 9 PDFs + 1 HTML: `invoice_000.pdf` … `invoice_009.pdf` mit einer `.html` dazwischen).
   - Terminal in der Repo-Wurzel, schon mit dem Befehl getippt aber NICHT abgesendet:
     `python -m uv run python -m invoice_agent --fresh --verbose`
4. Excel von `output/processed.xlsx` schließen falls offen.
5. Bildschirmauflösung mindestens 1920×1080. Terminal-Font groß genug zum Lesen im Webvideo (15pt+).
6. Datei-Übersicht (seed=42):
   - `invoice_000.pdf` — **Office-Supplies-Style** (schwarzer Header, Courier-Schrift, Eingangsstempel-Box, Zebra-Tabelle).
   - `invoice_001.pdf` — Scan + Math-Error (Webshop BuchBar).
   - `invoice_002.pdf` — Duplikat-Paar 1/2 (Webshop Pixelpunk).
   - `invoice_003.html` — **HTML-Bestellbestätigung** (KaffeeKönig, im Browser geöffnet).
   - `invoice_004.pdf` — Office-Supplies, sauber.
   - `invoice_005.pdf` — **Webshop-Style** (cyan Akzentleiste, Logo-Kreis, "Deine Bestellung").
   - `invoice_006.pdf` — **Consulting-Style** (Navy + Gold, Serif-Typografie, Premium-Look).
   - `invoice_007.pdf` — Scan + Helvetia CHF (Unknown-Vendor).
   - `invoice_008.pdf` — Webshop Pixelpunk, sauber.
   - `invoice_009.pdf` — Duplikat-Paar 2/2 (wird vom Agent geflaggt).

---

## Akt 1 — Eröffnung (0:00 – 0:22)

**Statisch:** Datei-Explorer zeigt 9 PDF-Thumbnails + 1 HTML. Erstes Overlay:

> "10 Eingangsrechnungen. Zwei Währungen, drei Formate, eine gescannt, eine mit USt-Fehler."

Vier Dateien kurz aufmachen, jede ~2.5–3 s, dazwischen schließen — die Reihenfolge zeigt visuelle Diversität:

1. **`invoice_006.pdf`** (Consulting Schmidt Strategy) — Navy-Streifen links, "RECHNUNG" in Serif, goldener Akzent. Premium-Look.
2. **`invoice_000.pdf`** (Office Supplies Müller Bürobedarf) — schwarzer Courier-Header, Eingangsstempel-Box, Zebra-Tabelle. Klassischer B2B-Buchhalter-Look.
3. **`invoice_003.html`** (KaffeeKönig HTML-Bestellbestätigung) — öffnet im Default-Browser, sieht aus wie eine Webshop-E-Mail mit cyan Header, Logo-Kreis "K", Tabelle. **Wichtig: das ist keine PDF.** Overlay-Einblendung in der Sekunde:
   > "Manche Webshops liefern HTML statt PDF — der Agent kann beides."
4. **`invoice_007.pdf`** (Scan Helvetia CHF) — leicht schräges Bild, sichtbar gescannt. Overlay-Einblendung:
   > "Diese hier ist ein Scan. Kein kopierbarer Text — der Agent muss das Bild lesen."

Zweites Overlay direkt vorm Cut:

> "Manuelle Verarbeitung: 3–8 Min pro Rechnung."

---

## Akt 2 — Der Agent arbeitet (0:22 – 0:58)

Wechsel ins Terminal. Drittes Overlay:

> "Python + Claude Agent SDK. Sechs typsichere Tools. Keine separate API-Rechnung."

`Enter` drücken. Verbose-Stream zeigt pro Rechnung:

- `> Read(...)` — Datei wird gelesen
- `> mcp__invoice__lookup_vendor(...)` — Vendor-Match
- `> mcp__invoice__verify_math(...)` — Mathematik geprüft
- `> mcp__invoice__check_duplicate(...)` — Duplikate
- `> mcp__invoice__categorize_expense(...)` — Kategorie
- `> mcp__invoice__append_to_excel(...)` — Excel-Eintrag

**Pause-Moment 1 — bei der zweiten Hälfte des Duplikat-Paars:**

> "Zweite Rechnung mit gleicher Nummer. Agent erkennt: Duplikat. Begründet die Entscheidung."

**Pause-Moment 2 — bei der Unknown-Vendor-CHF-Rechnung:**

> "Unbekannter Lieferant, fremde Währung. Statt zu raten: Markierung für Review."

Speed-Ramp erlaubt: 1× für die ersten ~4 Rechnungen, dann 2–4× für den Mittelteil, am Ende wieder 1× für die Run-Summary. Im Schnitt natürlich überblenden.

---

## Akt 3 — Ergebnis (0:58 – 1:20)

Der eigentliche Wow-Moment: der **deutschsprachige Abschluss-Bericht** im Terminal — gegliedert in "Sauber durchgelaufen" + "Bitte ansehen", mit voller Begründung pro Edge-Case.

1. **Bericht hervorheben** (~5–6s Standzeit):
   - Mit dem Cursor langsam von "OK Sauber durchgelaufen" nach unten zu "Bitte ansehen — NICHT in der Excel" wandern.
   - Bei einer Review-Begründung kurz mit der Maus umkreisen (z.B. die `Mathematik-Fehler`-Zeile oder die `Neuer Lieferant (nicht in Stammdaten)`-Zeile).

2. **Excel öffnen** (`output/processed.xlsx`): 7 Zeilen sichtbar. Mit der Maus die **Category**-Spalte highlighten — verschiedene Kategorien beweisen, dass der Agent kontextuell entscheidet (z.B. Webshop-Vendor mit Default "Fachliteratur" wird bei tatsächlichen Office-Items zu "Bürobedarf" überschrieben).

3. *(Optional)* File-Explorer öffnet `output/review/` — 3 JSON-Dateien **sichtbar im Ordner, aber nicht öffnen**. Signalisiert "strukturierte Daten dahinter" ohne den JSON-Inhalt zu zeigen. JSON aufmachen wäre für KI-Laien zu kryptisch — der deutsche Terminal-Bericht hat das schon erklärt.

Viertes Overlay:

> "Strukturierte Daten. Begründete Ausnahmen. Audit-fertig."

---

## Outro (1:20 – 1:25)

Schwarzer Hintergrund, fünftes Overlay:

> "Code, Architektur und 6 weitere Use-Case-Ideen → vennen.dev"

---

## Aufnahme-Tipps

- Maus-Bewegungen langsam und gerade. Schnelle Cursor-Sprünge sehen amateurhaft aus.
- Terminal-Hintergrund schwarz, gut-kontrastiertes Foreground-Theme (z.B. Solarized Dark oder Windows Terminal Default).
- Wenn der Lauf zu lang oder zu kurz wird: zwei Takes machen — einen für die ersten ~4 Rechnungen mit "echter" Geschwindigkeit, dann einen für das Run-Summary nach komplettem Lauf. Im Schnitt zusammensetzen.
- Speed-Ramp (1× → 4× → 1×) in der Mitte ist erlaubt und wirkt nicht "betrogen", solange das Run-Summary echt ist.
- Keine Voice-over. Overlay-Text in 2–3 Sekunden ablesbar.
- Final-Export: MP4 H.264, ~5 MB Größenbudget für 90s @ 720p reicht.

## Backup-Plan

Falls der 10er-Lauf während der Aufnahme einen SDK-Quirk-Crash zeigt (siehe PROGRESS.md → Probleme & Lösungen), den Retry abwarten oder den Lauf neu starten. Im finalen Video keine Fehlerstellen behalten — schlechtes Signal an Recruiter, auch wenn der Retry funktioniert hat. Lieber kurz aussetzen und sauber zusammenschneiden.
