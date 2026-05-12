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

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

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
    for desc, lo, hi in items:
        qty = rng.randint(1, 3)
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
    for desc, lo, hi in items:
        qty = rng.randint(2, 24) if "hours" in desc else rng.randint(1, 3)
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
    items = pick_items("office_supplies", rng.randint(3, 7), rng)
    line_items = []
    for desc, lo, hi in items:
        qty = rng.randint(1, 12)
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


def _draw_line_item_table(c: canvas.Canvas, data: dict, y_start: float, lang: str) -> float:
    """Render the line-item table starting at y_start, return the y-coordinate after it."""
    headers = (
        ("Pos.", "Beschreibung", "Menge", "Einzelpreis", "Summe")
        if lang == "de"
        else ("#", "Description", "Qty", "Unit price", "Total")
    )
    cols = [20 * mm, 32 * mm, 115 * mm, 138 * mm, 165 * mm]

    c.setFont("Helvetica-Bold", 10)
    for x, h in zip(cols, headers):
        c.drawString(x, y_start, h)
    c.line(20 * mm, y_start - 1.5 * mm, 195 * mm, y_start - 1.5 * mm)

    c.setFont("Helvetica", 10)
    y = y_start - 6 * mm
    for idx, item in enumerate(data["line_items"], start=1):
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

    c.setFont("Helvetica-Bold", 18)
    c.drawString(20 * mm, h - 25 * mm, vendor.name)
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, h - 31 * mm, vendor.address)
    c.drawString(20 * mm, h - 36 * mm, f"USt-IdNr.: {vendor.vat_id}")

    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, h - 55 * mm, "Rechnungsempfänger:")
    c.drawString(20 * mm, h - 61 * mm, data["customer_name"])
    c.drawString(20 * mm, h - 66 * mm, data["customer_address"][:60])

    c.drawString(125 * mm, h - 55 * mm, f"Rechnungs-Nr: {data['invoice_no']}")
    c.drawString(125 * mm, h - 61 * mm, f"Datum: {data['invoice_date'].strftime('%d.%m.%Y')}")
    c.drawString(125 * mm, h - 66 * mm, f"Fällig bis: {data['due_date'].strftime('%d.%m.%Y')}")

    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, h - 85 * mm, data["title"])

    y = _draw_line_item_table(c, data, h - 100 * mm, "de")
    _draw_totals(c, data, y)

    c.setFont("Helvetica", 8)
    c.drawString(20 * mm, 28 * mm, f"Bitte überweisen Sie auf IBAN: {vendor.iban}")
    c.drawString(20 * mm, 22 * mm, data["footer_note"])

    c.showPage()
    c.save()


def _render_consulting_clean(data: dict, output_path: Path) -> None:
    vendor: Vendor = data["vendor"]
    c = canvas.Canvas(str(output_path), pagesize=A4)
    _, h = A4
    lang = data["language"]

    # Right-aligned company block (more "professional" look)
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(195 * mm, h - 22 * mm, vendor.name.upper())
    c.setFont("Helvetica", 9)
    c.drawRightString(195 * mm, h - 28 * mm, vendor.address)
    c.drawRightString(195 * mm, h - 33 * mm, vendor.vat_id)

    # Bill to
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, h - 55 * mm, "BILL TO" if lang == "en" else "Rechnungsempfänger")
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, h - 62 * mm, data["customer_name"])
    c.drawString(20 * mm, h - 67 * mm, data["customer_address"][:60])

    # Meta block
    c.setFont("Helvetica", 9)
    meta_pairs = [
        ("Invoice No." if lang == "en" else "Rechnungs-Nr.", data["invoice_no"]),
        ("Date" if lang == "en" else "Datum", data["invoice_date"].strftime("%d.%m.%Y")),
        ("Due Date" if lang == "en" else "Fällig", data["due_date"].strftime("%d.%m.%Y")),
        ("PO", data.get("po_number", "")),
        ("Terms" if lang == "en" else "Zahlungsziel", data.get("payment_terms", "")),
    ]
    y_meta = h - 55 * mm
    for label, value in meta_pairs:
        c.drawString(125 * mm, y_meta, f"{label}:")
        c.drawString(155 * mm, y_meta, str(value))
        y_meta -= 5 * mm

    c.setFont("Helvetica-Bold", 18)
    c.drawString(20 * mm, h - 95 * mm, data["title"].upper())

    y = _draw_line_item_table(c, data, h - 110 * mm, lang)
    _draw_totals(c, data, y)

    c.setFont("Helvetica", 8)
    c.drawString(20 * mm, 28 * mm, f"Wire / IBAN: {vendor.iban}")
    c.drawString(20 * mm, 22 * mm, data["footer_note"])

    c.showPage()
    c.save()


def _render_office_supplies_clean(data: dict, output_path: Path) -> None:
    vendor: Vendor = data["vendor"]
    c = canvas.Canvas(str(output_path), pagesize=A4)
    _, h = A4

    # Utilitarian header
    c.setFont("Helvetica-Bold", 13)
    c.drawString(20 * mm, h - 22 * mm, vendor.name)
    c.setFont("Helvetica", 8)
    c.drawString(20 * mm, h - 27 * mm, f"{vendor.address} · USt-IdNr.: {vendor.vat_id}")
    c.line(20 * mm, h - 30 * mm, 195 * mm, h - 30 * mm)

    # Meta as a strip
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, h - 38 * mm, f"Rechnungs-Nr.: {data['invoice_no']}")
    c.drawString(80 * mm, h - 38 * mm, f"Datum: {data['invoice_date'].strftime('%d.%m.%Y')}")
    c.drawString(125 * mm, h - 38 * mm, f"Fällig: {data['due_date'].strftime('%d.%m.%Y')}")
    c.drawString(165 * mm, h - 38 * mm, data.get("order_reference", "")[:25])

    # Bill-to
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, h - 55 * mm, "Rechnungsempfänger:")
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, h - 61 * mm, data["customer_name"])
    c.drawString(20 * mm, h - 66 * mm, data["customer_address"][:65])

    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, h - 82 * mm, data["title"])

    y = _draw_line_item_table(c, data, h - 95 * mm, "de")
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
