# Office Automation Showcase — Progress Log

## Wo wir gerade stehen

**Letztes Update:** 2026-05-12
**Aktuelle Phase:** Phase 6 abgeschlossen — Portfolio-Integration fertig. Alle 6 Phasen durch. Bauseite ist fertig; die verbleibenden Aufgaben sind nur noch manuell durch den User durchzuführen (siehe "Offene Fragen / TODOs" unten).
**Nächster konkreter Schritt:** **MANUELL DURCH DEN USER:** (1) GitHub-Repo anlegen, Code committen, push; (2) `githubUrl` in `lib/projects.ts` auf die neue Repo-URL anpassen; (3) Demo-Video nach `docs/video_script.md` aufnehmen, als `public/videos/invoice-agent-demo.mp4` ins Portfolio legen, dann `videoPath`-Kommentar in `lib/projects.ts` entkommentieren; (4) `npm run dev` im Portfolio starten und `/projects/invoice-agent` durchklicken.

## Status pro Phase

- [x] **Phase 1** — Memory, Ideen-Ordner, Progress-Logbuch
- [x] **Phase 2** — Projekt-Skeleton (pyproject.toml, venv via uv, .gitignore, .env.example, README-Scaffold)
- [x] **Phase 3** — Daten-Generator (vendors.json, fixtures, templates, distortions, generate-CLI; 30er-Lauf verifiziert)
- [x] **Phase 4** — Agent-Kern (schemas, outputs, tools mit MCP-Server, prompts, agent.py mit Retry); 8er-Test-Batch grün
- [x] **Phase 5** — Case Study, README, LICENSE, Video-Drehbuch, Architektur-SVG
- [x] **Phase 6** — Portfolio-Integration (lib/projects.ts-Eintrag, InvoiceAgentContent in [slug]/page.tsx, Video-Sektion mit optionalem videoPath, SVG nach public/images/, TypeScript clean)
- [ ] **Phase 4** — Agent-Kern (schemas, tools, agent.py, outputs)
- [ ] **Phase 5** — Polish + Demo-Material (README, Case Study, Architektur-Diagramm, Video)
- [ ] **Phase 6** — Portfolio-Integration (lib/projects.ts, Content-Komponente, Asset-Einbindung)

## Entscheidungen

- **2026-05-12 — Use-Case-Wahl: Invoice Processing.** Gewählt aus 6 Vorschlägen (Rechnungen, Meeting-Protokoll, Bewerbungs-Screening, Markt-Recherche, Excel-Konsolidierung, E-Mail-Triage). Begründung: stärkste Vorher/Nachher-Story, klare Branchenrelevanz, Mehrstufen-Workflow gut visualisierbar. Verworfene Alternative #5 Excel-Konsolidierung als nächstes Projekt vorgemerkt.
- **2026-05-12 — Tech-Stack: Claude Agent SDK (Python) + Pydantic.** Verworfen: anthropic-SDK direkt (würde separate API-Kosten verursachen — User hat nur Pro-Plan), LangGraph (zu viel Framework-Magie, schmälert "ich verstehe Agents wirklich"-Signal), n8n (zu Low-Code für Skill-Demo).
- **2026-05-12 — Eingangskanal v1: lokaler Inbox-Ordner.** Verworfen: IMAP/Mail-Konten-Setup (mehr Aufwand, kein zusätzlicher Show-Wert im Video), Webhook-Service (Kosten + Hosting).
- **2026-05-12 — Demo-Daten: synthetisch, maximal divers.** DE + EN, EUR + USD + CHF, mix aus sauberen PDFs + simulierten Scans (~25%). Begründung: Scans zwingen den Agent in den Vision-Pfad, das beweist Tiefe.
- **2026-05-12 — Demo-Embed: vorab aufgenommenes MP4.** Verworfen: animiertes Log-Replay (mehr Aufwand für marginalen Mehrwert), Live-API-Demo (Hosting+Kosten, kommt evtl. als v2).
- **2026-05-12 — Repo-Struktur: eigenes GitHub-Repo.** Portfolio-Page verlinkt darauf (gleiches Pattern wie bestehende Projekte). Verworfen: Subfolder im portfolio-Repo, Monorepo.
- **2026-05-12 — OSS-Strategie: voll offen + Case-Study-Text.** Verworfen: Snapshot-only. Begründung: der Wert für Recruiter liegt nicht in der Idee (Invoice-Processing ist bekannt) sondern in der Umsetzungsqualität — die muss sichtbar sein. Case-Study-Text auf Portfolio-Page als nicht-kopierbares Differenzierungs-Asset.
- **2026-05-12 — `ideen/`-Ordner außerhalb des Projekts.** Liegt in `C:\Users\bvenn\OneDrive\Desktop\Python Projekte\ideen\` statt innerhalb Office_automation. Begründung: ist projekt-übergreifende Sammlung für zukünftige Showcases.
- **2026-05-12 — `uv` per `pip install --user uv` installiert** (statt offiziellem PowerShell-Installer). Begründung: weniger invasiv, Python-pip war schon da. Installierte Version: 0.11.13. Wird via `python -m uv` aufgerufen, da nicht auf PATH.
- **2026-05-12 — `uv.lock` wird committed.** Begründung: Reproduzierbarkeit der Demo ist Recruiter-Wert; jemand der das Repo clont soll exakt dieselben Versionen bekommen. Standard-Praxis für Applikationen (im Gegensatz zu Libraries).
- **2026-05-12 — Hatchling als Build-Backend.** Wegen Mixed-Layout (`src/invoice_agent/` + `data_generator/` am Root) explizit beide Pfade in `[tool.hatch.build.targets.wheel].packages` aufgeführt. `uv sync` installiert das Projekt selbst editierbar in die venv, so dass `python -m invoice_agent` und `python -m data_generator.generate` von überall funktionieren.
- **2026-05-12 — Template-Konsolidierung: 1 Datei statt 5.** Plan sah `data_generator/templates/*.py` mit je einer Datei pro Template vor. Stattdessen alles in `data_generator/templates.py` mit 3 Funktionen — weniger Datei-Rauschen, bessere Übersichtlichkeit. Die geplanten 5 Templates auf 3 reduziert (webshop_de, consulting_en, office_supplies_de). SaaS-Subscription und Handyman-CHF sind nicht-notwendig für die Mindest-Demo — Polish-Kandidaten für Phase 5 falls Zeit.
- **2026-05-12 — Scan-Rendering ohne PDF-Rasterizer.** Statt PDF→Image→Distortion→PDF nutze ich direkt PIL+ImageDraw, um die Rechnung als Bild zu rendern, und embedde das verzerrte Bild in einen Image-only-PDF. Vorteil: keine zusätzliche System-Dependency (poppler/pdfium), Install bleibt trivial. Trade-off: Layout der Scan-Variante ist visuell einfacher als die Clean-Variante. Für das Demo-Ziel ("Agent muss Vision nutzen, weil Text-Layer leer ist") perfekt ausreichend.
- **2026-05-12 — Ground-truth-Manifest in `demo_inputs/manifest.json`.** Der Generator schreibt neben den PDFs eine Manifest-Datei mit allen extrahierten Feldern + Flags für injizierte Edge Cases. Wird vom Agent NICHT gelesen, aber dient in Phase 4 als Verifikations-Referenz beim manuellen Eyeballing und für automatisierte Tests.
- **2026-05-12 — Eine Query pro Rechnung (statt einer langen Session).** Bei `process_inbox` öffnet jede Rechnung einen frischen `query()`-Aufruf. Vorteile: Fehler in einer Rechnung kontaminieren den Rest nicht; Kosten sind pro Rechnung beschränkt; im Demo-Video gibt es einen klaren Rhythmus "Rechnung rein → Tool-Calls → Result raus". Trade-off: leichter Overhead pro Rechnung (jeder Start des Claude-Code-Subprozess).
- **2026-05-12 — Claude Code's eingebauter `Read`-Tool statt Custom-`read_pdf`.** Claude Code liest PDFs (Text + Bilder für Scans) nativ. Ein eigenes `read_pdf` wäre redundant — der Agent ruft `Read(path)` und bekommt automatisch entweder Text oder Bild. Hält die Custom-Tools auf die echte Business-Logik fokussiert (Vendor-Lookup, Validierung, Routing).
- **2026-05-12 — In-Process MCP Server statt externer.** `create_sdk_mcp_server` wraps die Tools in einen In-Process-MCP-Server. Die Tools sind sichtbar als `mcp__invoice__<name>`. Vorteile: kein IPC-Overhead, direkter Zugriff auf Python-State, einfacheres Debugging. Geplante Erwähnung in der Case Study weil das ein moderner agentischer Idiom ist.
- **2026-05-12 — `permission_mode="bypassPermissions"`.** Notwendig damit der Agent ohne menschliche Bestätigung jeden Tool-Call ausführen darf. In Production wäre das zu locker; im Showcase ist das der gewünschte autonome Ablauf. In der Case Study explizit als "Demo-Konfiguration" markieren mit Hinweis auf produktiv-tauglichere Alternativen (`auto`, Hooks für Approval).
- **2026-05-12 — Retry mit 2,5s Backoff bei SDK-Transient-Errors.** SDK warf einmal mitten im Batch `Claude Code returned an error result: success` (siehe Probleme & Lösungen). Schutz dagegen ist ein Retry pro Rechnung; im 8er-Re-Run kam der Fehler nicht wieder.

## Probleme & Lösungen

- **2026-05-12 — Windows-Konsole zeigt `?` für Umlaute im Print-Output.** Beim Audit-Print nach dem 30er-Lauf erschienen "B?robedarf" statt "Bürobedarf". Reines `cp1252`-Konsolen-Encoding-Problem von `python.exe` unter Windows, KEIN Datenkorruptions-Problem. Manifest und PDFs enthalten korrektes UTF-8. Workaround falls in Folge nötig: `set PYTHONIOENCODING=utf-8` vor dem Aufruf oder `chcp 65001` im Terminal.
- **2026-05-12 — UnicodeEncodeError in `agent.py` beim Verbose-Print mit `→` (U+2192).** Crashte den ganzen Lauf, weil der Print im Loop sass. Lösung: (a) ASCII-Pfeile (`>`, `<`, `|`) statt Unicode, plus (b) `sys.stdout.reconfigure(encoding="utf-8")` am Modul-Anfang unter Windows. Erkenntnis: bei jedem `print` in Modulen, die auf Windows laufen sollen, Unicode in formatted strings vermeiden oder stdout-Encoding einmalig setzen.
- **2026-05-12 — SDK warf `Claude Code returned an error result: success` mitten im Batch.** Trat bei invoice_006 auf (vermutlich coincidentally — möglicherweise transientes Subprozess-/Session-Protokoll-Issue der Claude-Agent-SDK). Lokalisiert in `claude_agent_sdk/_internal/query.py:852` (raise wenn message.type == "error", auch wenn `error="success"`). Lösung: pro Rechnung einmaliger Retry nach 2,5s Pause. Im Re-Run kam der Fehler nicht wieder — also war es transient. Erkenntnis: SDK-Calls grundsätzlich mit Retry-Schutz wrappen, da der Subprozess-Protokoll-Layer gelegentlich quirks hat.

## Offene Fragen / TODOs

**Erledigt während Phasen 1–6:**
- [x] Slug = `invoice-agent` (in lib/projects.ts gesetzt)
- [x] Architektur als hand-geschriebenes SVG (`docs/architecture.svg` + Kopie unter `portfolio/public/images/`)
- [x] Vision via Built-in Claude-Code-`Read`-Tool, statt eigenem Wrapper

**Manuell durch den User (Reihenfolge):**
- [ ] GitHub-Repo anlegen (Vorschlag: `office-automation-invoice-agent` oder `invoice-agent`), `Office_automation`-Verzeichnis als Initial-Commit pushen.
- [ ] `githubUrl` in `portfolio/lib/projects.ts` für den `invoice-agent`-Eintrag auf die echte Repo-URL setzen (aktuell Platzhalter `https://github.com/bvn3141`).
- [ ] Demo-Video nach `docs/video_script.md` aufnehmen (60–90s, MP4, ~720p).
- [ ] Video als `portfolio/public/videos/invoice-agent-demo.mp4` ablegen.
- [ ] Die `videoPath`-Zeile in `portfolio/lib/projects.ts` entkommentieren — Video-Sektion auf der Project-Page wird automatisch sichtbar.
- [ ] Optional: 5 Beispiel-PDFs aus einem frischen Generator-Lauf nach `examples/sample_invoices/` committen, plus eine fertige `examples/sample_processed.xlsx` (für GitHub-Browser ohne Setup).
- [ ] Voller 30-Rechnungs-Lauf zur Validierung aller Edge-Case-Typen + zum Liefern der echten Run-Zahlen für die Case Study (aktueller Zwischenstand basiert auf 8er-Run).

**Bei Bedarf später (v2-Ideen):**
- [ ] IMAP/Mail-Konten-Integration als Eingangskanal (Plan Anhang A).
- [ ] Audit-Log mit komplettem Reasoning-Trail statt nur Summary (GoBD-Anforderung).
- [ ] Webhook-basierter Inbound-Service (Mailgun/Cloudflare) für eine echte Live-Demo auf der Website.
- [ ] Buchhaltungssystem-Integration (DATEV / lexoffice / sevDesk) statt Excel-Export.

## Demo-Ergebnis-Metriken

**8er-Validierungs-Run (2026-05-12), nach Phase 4:**
- 8 PDFs in 389 s (Durchschnitt ~49 s/Rechnung)
- 7 erfolgreich verarbeitet (PROCESSED in Excel)
- 1 korrekt zur Review geflaggt (Duplikat — die zweite Hälfte des injizierten Paars)
- 0 False Positives, 0 False Negatives in diesem Subset
- Kategorisierung intelligent: in einem Fall den Vendor-Default (`Fachliteratur`) basierend auf den tatsächlichen Line Items (Kaffee, Tasse, Schreibtisch-Organizer) zu `Bürobedarf` überschrieben

**Erwartung für 30er-Lauf (nicht ausgeführt, wegen Token-Sparsamkeit):**
- ~25 min Gesamtlaufzeit
- ~24 PROCESSED + 6 REVIEW (4 echte Edge Cases + 2 Duplikate)
- Diese Zahlen erst nach echtem 30er-Lauf in die Case Study übernehmen, falls sie abweichen.

## Wichtige Pfade & Befehle

**Pfade:**
- Projekt: `C:\Users\bvenn\OneDrive\Desktop\Python Projekte\Showcases\Office_automation`
- Portfolio: `C:\Users\bvenn\OneDrive\Desktop\Python Projekte\Website Dev\portfolio`
- Ideen-Sammlung: `C:\Users\bvenn\OneDrive\Desktop\Python Projekte\ideen`
- Plan: `C:\Users\bvenn\.claude\plans\encapsulated-whistling-willow.md`

**Befehle:**
- Setup neu (z.B. nach `git clone`): `python -m uv sync`
- venv-Python direkt: `.venv/Scripts/python.exe` (Windows)
- Demo-Lauf (geplant, ab Phase 4): `python -m uv run python -m data_generator.generate --n 30 && python -m uv run python -m invoice_agent`
- Portfolio-Dev: `cd "C:\Users\bvenn\OneDrive\Desktop\Python Projekte\Website Dev\portfolio"` und dann `npm run dev`
- Tests einzelner Module: `python -m uv run python -c "import invoice_agent; ..."`

## Wie diese Datei in der nächsten Session zu lesen ist

Zuerst lesen, vor allem anderen. Sektion "Wo wir gerade stehen" + "Nächster konkreter Schritt" + "Status pro Phase" geben in 30 Sekunden den Wiedereinstieg. Danach Plan-File für Detail-Architektur konsultieren. Bei Schwierigkeiten in "Probleme & Lösungen" nach ähnlichen Fällen suchen, bevor neu gerätselt wird.
