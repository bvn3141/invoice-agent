"""Invoice templates: build invoice data + render as clean PDF via ReportLab.

Each public template function (`webshop_de`, `consulting_en`, `office_supplies_de`)
returns a structured `dict` of ground-truth data alongside the rendered PDF. The
dict feeds both (a) the manifest written by `generate.py` and (b) the scan
renderer in `distortions.py` when the same invoice should be rendered as an
image-only scanned variant.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

# Visual identity per template — distinct accent colors picked to keep the three
# templates instantly recognizable as different vendors at thumbnail size.
WEBSHOP_ACCENT = colors.HexColor("#00A0B0")      # cyan / e-commerce
CONSULTING_ACCENT = colors.HexColor("#1A2E5C")   # dark navy / premium
CONSULTING_GOLD = colors.HexColor("#B89968")     # subtle gold underline
OFFICE_ZEBRA = colors.HexColor("#F0F0F0")        # light grey row band
MUTED_TEXT = colors.HexColor("#666666")

from data_generator.fixtures import (
    PRODUCT_CATALOGS,
    Vendor,
    make_faker,
    pick_items,
    random_invoice_number,
)

USt_RATE = 0.19


# ─── Data builders ────────────────────────────────────────────────────────────


def _build_webshop_data(vendor: Vendor, rng: random.Random) -> dict:
    faker = make_faker("de_DE")
    faker.seed_instance(rng.randint(0, 1_000_000))
    items = pick_items("webshop", rng.randint(1, 3), rng)
    line_items = []
    for desc, lo, hi, max_qty in items:
        qty = rng.randint(1, max_qty)
        unit_price = round(rng.uniform(lo, hi), 2)
        line_items.append(
            {
                "description": desc,
                "qty": qty,
                "unit_price": unit_price,
                "line_total": round(qty * unit_price, 2),
            }
        )
    netto = round(sum(li["line_total"] for li in line_items), 2)
    ust = round(netto * USt_RATE, 2)
    brutto = round(netto + ust, 2)
    invoice_date = faker.date_between(start_date="-60d", end_date="today")
    return {
        "template": "webshop_de",
        "language": "de",
        "vendor": vendor,
        "invoice_no": random_invoice_number(rng, invoice_date.year),
        "invoice_date": invoice_date,
        "due_date": invoice_date + timedelta(days=14),
        "customer_name": faker.name(),
        "customer_address": faker.address().replace("\n", ", "),
        "currency": vendor.default_currency,
        "line_items": line_items,
        "netto": netto,
        "ust": ust,
        "brutto": brutto,
        "ust_rate": USt_RATE,
        "footer_note": "Vielen Dank für Ihren Einkauf!",
        "title": "Rechnung",
    }


def _build_consulting_data(vendor: Vendor, rng: random.Random) -> dict:
    locale = "en_US" if vendor.country == "US" else "de_DE"
    faker = make_faker(locale)
    faker.seed_instance(rng.randint(0, 1_000_000))
    items = pick_items("consulting", rng.randint(1, 2), rng)
    line_items = []
    for desc, lo, hi, max_qty in items:
        qty = rng.randint(2, max_qty) if "hours" in desc else rng.randint(1, max_qty)
        unit_price = round(rng.uniform(lo, hi), 2)
        line_items.append(
            {
                "description": desc,
                "qty": qty,
                "unit_price": unit_price,
                "line_total": round(qty * unit_price, 2),
            }
        )
    netto = round(sum(li["line_total"] for li in line_items), 2)
    is_us = vendor.country == "US"
    ust_rate = 0.0 if is_us else USt_RATE
    ust = round(netto * ust_rate, 2)
    brutto = round(netto + ust, 2)
    invoice_date = faker.date_between(start_date="-90d", end_date="today")
    return {
        "template": "consulting_en",
        "language": "en" if is_us else "de",
        "vendor": vendor,
        "invoice_no": random_invoice_number(rng, invoice_date.year),
        "invoice_date": invoice_date,
        "due_date": invoice_date + timedelta(days=30),
        "customer_name": faker.company(),
        "customer_address": faker.address().replace("\n", ", "),
        "currency": vendor.default_currency,
        "line_items": line_items,
        "netto": netto,
        "ust": ust,
        "brutto": brutto,
        "ust_rate": ust_rate,
        "po_number": f"PO-{rng.randint(100000, 999999)}",
        "payment_terms": "Net 30 days",
        "footer_note": "Payment due within 30 days of invoice date.",
        "title": "Invoice" if is_us else "Rechnung",
    }


def _build_office_supplies_data(vendor: Vendor, rng: random.Random) -> dict:
    faker = make_faker("de_DE")
    faker.seed_instance(rng.randint(0, 1_000_000))
    items = pick_items("office_supplies", rng.randint(3, 6), rng)
    line_items = []
    for desc, lo, hi, max_qty in items:
        qty = rng.randint(1, max_qty)
        unit_price = round(rng.uniform(lo, hi), 2)
        line_items.append(
            {
                "description": desc,
                "qty": qty,
                "unit_price": unit_price,
                "line_total": round(qty * unit_price, 2),
            }
        )
    netto = round(sum(li["line_total"] for li in line_items), 2)
    ust = round(netto * USt_RATE, 2)
    brutto = round(netto + ust, 2)
    invoice_date = faker.date_between(start_date="-45d", end_date="today")
    return {
        "template": "office_supplies_de",
        "language": "de",
        "vendor": vendor,
        "invoice_no": random_invoice_number(rng, invoice_date.year),
        "invoice_date": invoice_date,
        "due_date": invoice_date + timedelta(days=21),
        "customer_name": faker.company(),
        "customer_address": faker.address().replace("\n", ", "),
        "currency": vendor.default_currency,
        "line_items": line_items,
        "netto": netto,
        "ust": ust,
        "brutto": brutto,
        "ust_rate": USt_RATE,
        "order_reference": f"Bestellung-Nr. {rng.randint(10000, 99999)}",
        "footer_note": "Zahlbar innerhalb von 21 Tagen ohne Abzug.",
        "title": "Rechnung",
    }


_BUILDERS: dict[str, Callable[[Vendor, random.Random], dict]] = {
    "webshop": _build_webshop_data,
    "consulting": _build_consulting_data,
    "office_supplies": _build_office_supplies_data,
}


def build_data(vendor: Vendor, rng: random.Random) -> dict:
    """Pick the right data builder based on the vendor's `template` field."""
    return _BUILDERS[vendor.template](vendor, rng)


# ─── Clean PDF renderers (one per template, for visual variety) ───────────────


def _draw_line_item_table(
    c: canvas.Canvas,
    data: dict,
    y_start: float,
    lang: str,
    *,
    zebra: bool = False,
    header_bg: colors.Color | None = None,
) -> float:
    """Render the line-item table starting at y_start, return the y-coordinate after it."""
    headers = (
        ("Pos.", "Beschreibung", "Menge", "Einzelpreis", "Summe")
        if lang == "de"
        else ("#", "Description", "Qty", "Unit price", "Total")
    )
    cols = [20 * mm, 32 * mm, 115 * mm, 138 * mm, 165 * mm]

    if header_bg is not None:
        c.setFillColor(header_bg)
        c.rect(20 * mm, y_start - 2 * mm, 175 * mm, 6 * mm, fill=1, stroke=0)
        c.setFillColor(colors.white)
    else:
        c.setFillColor(colors.black)

    c.setFont("Helvetica-Bold", 10)
    for x, h in zip(cols, headers):
        c.drawString(x, y_start, h)

    c.setFillColor(colors.black)
    if header_bg is None:
        c.line(20 * mm, y_start - 1.5 * mm, 195 * mm, y_start - 1.5 * mm)

    c.setFont("Helvetica", 10)
    y = y_start - 6 * mm
    for idx, item in enumerate(data["line_items"], start=1):
        if zebra and idx % 2 == 0:
            c.setFillColor(OFFICE_ZEBRA)
            c.rect(20 * mm, y - 1.5 * mm, 175 * mm, 5 * mm, fill=1, stroke=0)
            c.setFillColor(colors.black)
        c.drawString(cols[0], y, str(idx))
        c.drawString(cols[1], y, item["description"][:42])
        c.drawString(cols[2], y, str(item["qty"]))
        c.drawString(cols[3], y, f"{item['unit_price']:.2f} {data['currency']}")
        c.drawString(cols[4], y, f"{item['line_total']:.2f} {data['currency']}")
        y -= 5.5 * mm
    return y


def _draw_totals(c: canvas.Canvas, data: dict, y: float) -> float:
    lang = data["language"]
    y -= 4 * mm
    c.line(130 * mm, y, 195 * mm, y)
    y -= 5 * mm
    c.setFont("Helvetica", 10)
    netto_label = "Netto:" if lang == "de" else "Subtotal:"
    c.drawString(130 * mm, y, netto_label)
    c.drawString(165 * mm, y, f"{data['netto']:.2f} {data['currency']}")
    if data["ust_rate"] > 0:
        y -= 5 * mm
        ust_label = f"USt ({int(data['ust_rate']*100)}%):" if lang == "de" else f"VAT ({int(data['ust_rate']*100)}%):"
        c.drawString(130 * mm, y, ust_label)
        c.drawString(165 * mm, y, f"{data['ust']:.2f} {data['currency']}")
    y -= 6 * mm
    c.setFont("Helvetica-Bold", 11)
    total_label = "Gesamt:" if lang == "de" else "Total due:"
    c.drawString(130 * mm, y, total_label)
    c.drawString(165 * mm, y, f"{data['brutto']:.2f} {data['currency']}")
    return y


def _render_webshop_clean(data: dict, output_path: Path) -> None:
    vendor: Vendor = data["vendor"]
    c = canvas.Canvas(str(output_path), pagesize=A4)
    _, h = A4

    # Top cyan accent band — instantly readable e-commerce signal
    c.setFillColor(WEBSHOP_ACCENT)
    c.rect(0, h - 12 * mm, 210 * mm, 12 * mm, fill=1, stroke=0)

    # Logo bubble — circle with vendor initial
    c.setFillColor(WEBSHOP_ACCENT)
    c.circle(28 * mm, h - 29 * mm, 7 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(28 * mm, h - 31.5 * mm, vendor.name[0])

    # Vendor block next to logo
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40 * mm, h - 27 * mm, vendor.name)
    c.setFillColor(MUTED_TEXT)
    c.setFont("Helvetica", 9)
    c.drawString(40 * mm, h - 32 * mm, vendor.address)
    c.drawString(40 * mm, h - 36.5 * mm, f"USt-IdNr.: {vendor.vat_id}")
    c.setFillColor(colors.black)

    # Recipient + meta
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, h - 55 * mm, "Rechnungsempfänger")
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, h - 61 * mm, data["customer_name"])
    c.drawString(20 * mm, h - 66 * mm, data["customer_address"][:60])

    c.setFillColor(WEBSHOP_ACCENT)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(125 * mm, h - 55 * mm, "RECHNUNG")
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawString(125 * mm, h - 61 * mm, f"Nr: {data['invoice_no']}")
    c.drawString(125 * mm, h - 66 * mm, f"Datum: {data['invoice_date'].strftime('%d.%m.%Y')}")
    c.drawString(125 * mm, h - 71 * mm, f"Fällig: {data['due_date'].strftime('%d.%m.%Y')}")

    # Section divider
    c.setStrokeColor(WEBSHOP_ACCENT)
    c.setLineWidth(0.5)
    c.line(20 * mm, h - 85 * mm, 195 * mm, h - 85 * mm)
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)

    c.setFont("Helvetica-Bold", 13)
    c.drawString(20 * mm, h - 92 * mm, "Deine Bestellung")

    y = _draw_line_item_table(c, data, h - 105 * mm, "de", header_bg=WEBSHOP_ACCENT)
    _draw_totals(c, data, y)

    c.setFillColor(WEBSHOP_ACCENT)
    c.rect(0, 0, 210 * mm, 8 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(20 * mm, 3 * mm, data["footer_note"])
    c.drawRightString(195 * mm, 3 * mm, f"IBAN: {vendor.iban}")

    c.showPage()
    c.save()


def _render_consulting_clean(data: dict, output_path: Path) -> None:
    vendor: Vendor = data["vendor"]
    c = canvas.Canvas(str(output_path), pagesize=A4)
    _, h = A4
    lang = data["language"]

    # Vertical navy accent stripe on the left — institutional/premium signal
    c.setFillColor(CONSULTING_ACCENT)
    c.rect(0, 0, 8 * mm, h, fill=1, stroke=0)

    # Vendor name in serif on the right — high-end professional services
    c.setFillColor(colors.black)
    c.setFont("Times-Bold", 20)
    c.drawRightString(195 * mm, h - 24 * mm, vendor.name)
    c.setFont("Times-Roman", 9)
    c.setFillColor(MUTED_TEXT)
    c.drawRightString(195 * mm, h - 30 * mm, vendor.address)
    c.drawRightString(195 * mm, h - 35 * mm, vendor.vat_id)

    # Gold underline under the company name (subtle premium accent)
    c.setStrokeColor(CONSULTING_GOLD)
    c.setLineWidth(1.5)
    c.line(140 * mm, h - 40 * mm, 195 * mm, h - 40 * mm)
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)

    # Invoice title in serif, left-aligned (big and confident)
    c.setFillColor(CONSULTING_ACCENT)
    c.setFont("Times-Bold", 28)
    c.drawString(20 * mm, h - 60 * mm, data["title"].upper())
    c.setFillColor(colors.black)

    # Bill to
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(MUTED_TEXT)
    c.drawString(20 * mm, h - 75 * mm, ("BILL TO" if lang == "en" else "RECHNUNGSEMPFÄNGER"))
    c.setFillColor(colors.black)
    c.setFont("Times-Roman", 11)
    c.drawString(20 * mm, h - 81 * mm, data["customer_name"])
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, h - 86 * mm, data["customer_address"][:60])

    # Meta block
    c.setFont("Helvetica", 9)
    meta_pairs = [
        ("Invoice No." if lang == "en" else "Rechnungs-Nr.", data["invoice_no"]),
        ("Date" if lang == "en" else "Datum", data["invoice_date"].strftime("%d.%m.%Y")),
        ("Due Date" if lang == "en" else "Fällig", data["due_date"].strftime("%d.%m.%Y")),
        ("PO", data.get("po_number", "")),
        ("Terms" if lang == "en" else "Zahlungsziel", data.get("payment_terms", "")),
    ]
    y_meta = h - 75 * mm
    for label, value in meta_pairs:
        c.setFillColor(MUTED_TEXT)
        c.drawString(125 * mm, y_meta, f"{label}:")
        c.setFillColor(colors.black)
        c.drawString(155 * mm, y_meta, str(value))
        y_meta -= 5 * mm

    y = _draw_line_item_table(c, data, h - 110 * mm, lang)
    _draw_totals(c, data, y)

    # Footer with gold accent line
    c.setStrokeColor(CONSULTING_GOLD)
    c.setLineWidth(1)
    c.line(20 * mm, 32 * mm, 195 * mm, 32 * mm)
    c.setStrokeColor(colors.black)
    c.setFont("Helvetica", 8)
    c.drawString(20 * mm, 26 * mm, f"Wire / IBAN: {vendor.iban}")
    c.setFillColor(MUTED_TEXT)
    c.drawString(20 * mm, 20 * mm, data["footer_note"])
    c.setFillColor(colors.black)

    c.showPage()
    c.save()


def _render_office_supplies_clean(data: dict, output_path: Path) -> None:
    vendor: Vendor = data["vendor"]
    c = canvas.Canvas(str(output_path), pagesize=A4)
    _, h = A4

    # Black header bar — old-school B2B office supplier look
    c.setFillColor(colors.black)
    c.rect(20 * mm, h - 30 * mm, 175 * mm, 18 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Courier-Bold", 14)
    c.drawString(25 * mm, h - 22 * mm, vendor.name.upper())
    c.setFont("Courier", 8)
    c.drawString(25 * mm, h - 27 * mm, f"{vendor.address}  |  USt-IdNr.: {vendor.vat_id}")
    c.setFillColor(colors.black)

    # Meta strip in monospace — feels like a printed business form
    c.setFont("Courier", 9)
    c.drawString(20 * mm, h - 40 * mm, f"Rechnungs-Nr.: {data['invoice_no']}")
    c.drawString(80 * mm, h - 40 * mm, f"Datum: {data['invoice_date'].strftime('%d.%m.%Y')}")
    c.drawString(125 * mm, h - 40 * mm, f"Fällig: {data['due_date'].strftime('%d.%m.%Y')}")
    c.drawString(165 * mm, h - 40 * mm, data.get("order_reference", "")[:25])

    # Bill-to
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, h - 57 * mm, "RECHNUNGSEMPFÄNGER")
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, h - 63 * mm, data["customer_name"])
    c.drawString(20 * mm, h - 68 * mm, data["customer_address"][:65])

    # Eingangsstempel box (top-right corner) — classic B2B accounting cue
    c.setStrokeColor(MUTED_TEXT)
    c.setDash(2, 2)
    c.rect(140 * mm, h - 73 * mm, 55 * mm, 22 * mm, fill=0, stroke=1)
    c.setDash()
    c.setFillColor(MUTED_TEXT)
    c.setFont("Helvetica", 7)
    c.drawString(142 * mm, h - 55 * mm, "EINGANGSSTEMPEL")
    c.drawString(142 * mm, h - 70 * mm, "Geprüft / Kontiert / Datum")
    c.setFillColor(colors.black)
    c.setStrokeColor(colors.black)

    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, h - 84 * mm, data["title"])

    y = _draw_line_item_table(c, data, h - 97 * mm, "de", zebra=True)
    _draw_totals(c, data, y)

    c.setFont("Helvetica", 8)
    c.drawString(20 * mm, 28 * mm, f"Bankverbindung: IBAN {vendor.iban}")
    c.drawString(20 * mm, 22 * mm, data["footer_note"])

    c.showPage()
    c.save()


_CLEAN_RENDERERS: dict[str, Callable[[dict, Path], None]] = {
    "webshop_de": _render_webshop_clean,
    "consulting_en": _render_consulting_clean,
    "office_supplies_de": _render_office_supplies_clean,
}


def render_clean(data: dict, output_path: Path) -> None:
    """Render the invoice as a normal text-layer PDF."""
    _CLEAN_RENDERERS[data["template"]](data, output_path)


# ─── HTML order confirmation (webshop e-mail style) ───────────────────────────


def render_html_order(data: dict, output_path: Path) -> None:
    """Render a webshop order confirmation as a standalone HTML document.

    Stylistically mimics the kind of HTML order-confirmation e-mail that real
    webshops (Amazon, Otto, etc.) send instead of a PDF invoice. Tests the
    agent's ability to handle non-PDF inputs.
    """
    vendor: Vendor = data["vendor"]
    items_html = "\n".join(
        f"""        <tr>
          <td>{item['description']}</td>
          <td style="text-align:center">{item['qty']}</td>
          <td style="text-align:right">{item['unit_price']:.2f} {data['currency']}</td>
          <td style="text-align:right"><strong>{item['line_total']:.2f} {data['currency']}</strong></td>
        </tr>"""
        for item in data["line_items"]
    )

    ust_row = ""
    if data["ust_rate"] > 0:
        ust_row = f"""<tr>
          <td colspan="3" style="text-align:right">USt ({int(data['ust_rate']*100)}%):</td>
          <td style="text-align:right">{data['ust']:.2f} {data['currency']}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>Bestellbestätigung - {vendor.name}</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #222;
    background: #f5f7f8;
    margin: 0;
    padding: 24px;
  }}
  .container {{
    max-width: 640px;
    margin: 0 auto;
    background: #ffffff;
    border-radius: 6px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  }}
  .header {{
    background: #00A0B0;
    color: #ffffff;
    padding: 24px 28px;
    display: flex;
    align-items: center;
  }}
  .logo {{
    width: 44px;
    height: 44px;
    background: #ffffff;
    color: #00A0B0;
    border-radius: 50%;
    text-align: center;
    line-height: 44px;
    font-weight: 700;
    font-size: 22px;
    margin-right: 14px;
  }}
  .header h1 {{
    margin: 0;
    font-size: 18px;
    font-weight: 600;
  }}
  .header .tag {{
    margin: 2px 0 0 0;
    font-size: 12px;
    opacity: 0.85;
  }}
  .content {{
    padding: 28px;
  }}
  .content h2 {{
    margin: 0 0 6px 0;
    font-size: 22px;
  }}
  .content p {{
    margin: 6px 0;
    line-height: 1.5;
    color: #444;
  }}
  .meta {{
    background: #f5fafb;
    border-left: 3px solid #00A0B0;
    padding: 14px 16px;
    margin: 20px 0;
    font-size: 14px;
  }}
  .meta div {{ margin: 4px 0; }}
  .meta strong {{ color: #00A0B0; }}
  table.items {{
    width: 100%;
    border-collapse: collapse;
    margin: 18px 0;
    font-size: 14px;
  }}
  table.items th {{
    background: #00A0B0;
    color: #fff;
    padding: 10px;
    text-align: left;
    font-weight: 600;
  }}
  table.items th.right {{ text-align: right; }}
  table.items th.center {{ text-align: center; }}
  table.items td {{
    padding: 10px;
    border-bottom: 1px solid #eee;
  }}
  table.items tr:last-child td {{ border-bottom: none; }}
  table.totals {{
    width: 100%;
    margin-top: 6px;
    font-size: 14px;
  }}
  table.totals td {{
    padding: 4px 10px;
  }}
  table.totals tr.grand td {{
    border-top: 2px solid #00A0B0;
    font-size: 16px;
    font-weight: 700;
    padding-top: 10px;
  }}
  .footer {{
    background: #00A0B0;
    color: #fff;
    padding: 14px 28px;
    font-size: 12px;
    display: flex;
    justify-content: space-between;
  }}
  .footer .iban {{ font-family: 'Courier New', monospace; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="logo">{vendor.name[0]}</div>
    <div>
      <h1>{vendor.name}</h1>
      <p class="tag">{vendor.address}</p>
    </div>
  </div>
  <div class="content">
    <h2>Vielen Dank für deine Bestellung!</h2>
    <p>Hallo {data['customer_name']},</p>
    <p>deine Bestellung ist eingegangen. Anbei findest du die Rechnung als HTML-Übersicht. Diese E-Mail ist deine offizielle Rechnung im Sinne des UStG &sect; 14.</p>

    <div class="meta">
      <div><strong>Rechnungs-Nr.:</strong> {data['invoice_no']}</div>
      <div><strong>Datum:</strong> {data['invoice_date'].strftime('%d.%m.%Y')}</div>
      <div><strong>Fällig bis:</strong> {data['due_date'].strftime('%d.%m.%Y')}</div>
      <div><strong>USt-IdNr. (Verkäufer):</strong> {vendor.vat_id}</div>
    </div>

    <table class="items">
      <thead>
        <tr>
          <th>Beschreibung</th>
          <th class="center">Menge</th>
          <th class="right">Einzelpreis</th>
          <th class="right">Summe</th>
        </tr>
      </thead>
      <tbody>
{items_html}
      </tbody>
    </table>

    <table class="totals">
      <tr>
        <td colspan="3" style="text-align:right">Netto:</td>
        <td style="text-align:right">{data['netto']:.2f} {data['currency']}</td>
      </tr>
      {ust_row}
      <tr class="grand">
        <td colspan="3" style="text-align:right">Gesamtbetrag:</td>
        <td style="text-align:right">{data['brutto']:.2f} {data['currency']}</td>
      </tr>
    </table>

    <p style="margin-top:24px;font-size:13px;color:#666;">
      {data['footer_note']} Bitte überweise den Gesamtbetrag innerhalb der Zahlungsfrist auf das unten genannte Konto.
    </p>
  </div>
  <div class="footer">
    <span>{vendor.name}</span>
    <span class="iban">IBAN: {vendor.iban}</span>
  </div>
</div>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
