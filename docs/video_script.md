# Demo Video — Drehbuch

Ziel: 60–90 Sekunden, das einem Recruiter ohne KI-Hintergrund in einem Take zeigt, dass dieses Projekt mehr ist als ein ChatGPT-Wrapper. Aufnahme via OBS oder Windows-Screen-Recorder. Zwei Bildschirmregionen sind relevant: ein File-Explorer (links) und ein Terminal (rechts). Keine Stimme — nur kurzer Text als Overlay, weil das in Webseiten-Embeds besser funktioniert (autoplay-stumm ist auf den meisten Browsern Default).

---

## Vorbereitung (vor der Aufnahme)

1. Repo frisch geclont oder `output/` und `demo_inputs/` gelöscht.
2. Frischer Generator-Lauf: `python -m uv run python -m data_generator.generate --n 30`.
   (NICHT vor der Aufnahme den Agent laufen lassen — die Excel soll im Take "wachsen".)
3. Zwei Fenster offen:
   - File Explorer auf `demo_inputs/inbox/` mit Detail-Ansicht (zeigt die 30 PDFs).
   - Terminal in der Repo-Wurzel, schon mit dem Befehl getippt aber NICHT abgesendet:
     `python -m uv run python -m invoice_agent --fresh --verbose`
4. Excel von `output/processed.xlsx` schließen falls offen.
5. Bildschirmauflösung mindestens 1920×1080. Terminal-Font groß genug zum Lesen im Webvideo (15pt+).

## Sequenz (Sekunden ungefähr)

**00:00 – 00:08 — Eröffnung.**
Statisch: Datei-Explorer mit 30 PDFs. Overlay-Text:
> "30 Eingangsrechnungen. Manuelle Verarbeitung: 3–8 Min pro Rechnung."

Mit der Maus eine zufällige PDF doppelklicken → 1 Sekunde sichtbar → wieder schließen. Eine Scan-Variante (z.B. `invoice_001.pdf`) öffnen, kurz zeigen "ist nur ein Bild, kein kopierbarer Text" → schließen.

**00:08 – 00:18 — Setup.**
Wechsel ins Terminal. Overlay:
> "Der Agent: Python + Claude Agent SDK. Sechs typsichere Tools. Keine separate API-Rechnung."

Enter drücken. Erste Zeilen scrollen rein.

**00:18 – 00:55 — Der Agent arbeitet.**
Verbose-Stream zeigt pro Rechnung:
- `> Read(...)` — Datei wird gelesen
- `> mcp__invoice__lookup_vendor(...)` — Vendor-Match
- `> mcp__invoice__verify_math(...)` — Mathematik geprüft
- `> mcp__invoice__check_duplicate(...)` — Duplikate
- `> mcp__invoice__categorize_expense(...)` — Kategorie
- `> mcp__invoice__append_to_excel(...)` — Excel-Eintrag

Bei einer Review-Entscheidung (z.B. das Duplikat):
- `> mcp__invoice__flag_for_review(...)` — und der Begründungstext.

Idealer Moment: Wenn das Duplikat auf invoice_006 erkannt wird, einen Beat länger pausieren, Overlay:
> "Zweite Rechnung mit gleicher Nummer. Agent erkennt: Duplikat. Begründet die Entscheidung."

**00:55 – 01:10 — Ergebnis.**
Wenn der Run fertig ist, die "Run summary"-Zeilen kurz hervorheben:
```
total invoices:      30
processed:           27
flagged for review:  3
elapsed:             ~25 min  (entsprechend reduziert für die Aufnahme: erstes Drittel zeigen reicht)
```

> Hinweis: Für das Video reicht es, die ersten ~5 Rechnungen vollständig zu zeigen und dann mit einem Cut bzw. einer "Time-Lapse-Sektion" (4× speed-up) zum Run-Summary zu springen.

**01:10 – 01:25 — Output sichtbar.**
File-Explorer öffnet `output/processed.xlsx` in Excel. Tabelle mit ~27 Zeilen sichtbar. Spalten lesbar.
Daneben: `output/review/` mit 3 JSON-Dateien — eine davon öffnen (das Duplikat) und die `reason.explanation`-Zeile hervorheben.

Overlay:
> "Strukturierte Daten. Begründete Ausnahmen. Audit-fertig."

**01:25 – 01:30 — Outro.**
Schwarzer Hintergrund, Text:
> "Code, Architektur und 6 weitere Use-Case-Ideen → vennen.dev"

## Aufnahme-Tipps

- Maus-Bewegungen langsam und gerade. Schnelle Cursor-Sprünge sehen amateurhaft aus.
- Terminal-Hintergrund schwarz, gut-kontrastiertes Foreground-Theme (z.B. Solarized Dark oder ähnlich).
- Wenn der erste Agent-Lauf zu lang ist: zwei Takes machen, einen für die ersten ~5 Rechnungen mit "echter" Geschwindigkeit, dann einen für das Run-Summary nach komplettem Lauf. Im Schnitt zusammensetzen.
- Speed-Ramp (1× → 4× → 1×) in der Mitte ist erlaubt und wirkt nicht "betrogen", solange das Run-Summary echt ist.
- Keine Voice-over. Overlay-Text in 2–3 Sekunden ablesbar.
- Final-Export: MP4 H.264, ~5 MB Größenbudget für 90s @ 720p reicht.

## Backup-Plan

Falls der 30er-Lauf während der Aufnahme einen SDK-Quirk-Crash zeigt (siehe PROGRESS.md → Probleme & Lösungen), den Retry abwarten oder den Lauf am betroffenen Index neu starten. Im finalen Video keine Fehlerstellen behalten — schlechtes Signal an Recruiter, auch wenn der Retry funktioniert hat. Lieber kurz aussetzen und sauber zusammenschneiden.
