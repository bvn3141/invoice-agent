"""Scan-look invoice rendering.

We draw the invoice content directly onto a PIL image (no text layer), apply
distortions that mimic a scan (rotation, gaussian noise, JPEG re-compression,
slight contrast loss), and embed the resulting image into a one-page PDF.

This is deliberately not a PDF-to-image-back-to-PDF pipeline — that would force
us to ship a system-dependency rasterizer (poppler or similar). Going
PIL-only keeps the install trivial.

Outcome for the agent: a `read_pdf` extraction returns no text layer, so the
agent's vision tool is the only way to read the content. This is precisely the
demo edge case we want.
"""

from __future__ import annotations

import io
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

# Render at higher resolution then downscale — gives crisper-looking text
# before we add scan distortion on top.
PAGE_W_PX, PAGE_H_PX = 1240, 1754  # ~150 dpi for A4


def _load_font(size: int) -> ImageFont.ImageFont:
    """Try a few system fonts; fall back to PIL default."""
    for path in (
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_invoice_image(data: dict) -> Image.Image:
    img = Image.new("RGB", (PAGE_W_PX, PAGE_H_PX), color=(252, 250, 245))  # off-white scan tint
    draw = ImageDraw.Draw(img)

    f_huge = _load_font(36)
    f_big = _load_font(28)
    f_med = _load_font(20)
    f_small = _load_font(16)

    vendor = data["vendor"]
    lang = data["language"]
    cur = data["currency"]

    # Header
    draw.text((80, 70), vendor.name, font=f_huge, fill=(10, 10, 10))
    draw.text((80, 130), vendor.address, font=f_small, fill=(40, 40, 40))
    vat_label = "USt-IdNr.: " if lang == "de" else "Tax ID: "
    draw.text((80, 155), f"{vat_label}{vendor.vat_id}", font=f_small, fill=(40, 40, 40))

    # Title
    title_y = 250
    draw.text((80, title_y), data["title"], font=f_big, fill=(0, 0, 0))

    # Meta block
    meta_x = 700
    meta_y = title_y
    meta_pairs = (
        [
            ("Rechnungs-Nr.:", data["invoice_no"]),
            ("Datum:", data["invoice_date"].strftime("%d.%m.%Y")),
            ("Fällig bis:", data["due_date"].strftime("%d.%m.%Y")),
        ]
        if lang == "de"
        else [
            ("Invoice No.:", data["invoice_no"]),
            ("Date:", data["invoice_date"].strftime("%d.%m.%Y")),
            ("Due:", data["due_date"].strftime("%d.%m.%Y")),
        ]
    )
    for label, value in meta_pairs:
        draw.text((meta_x, meta_y), label, font=f_small, fill=(20, 20, 20))
        draw.text((meta_x + 170, meta_y), str(value), font=f_small, fill=(20, 20, 20))
        meta_y += 28

    # Bill-to
    billto_y = 360
    draw.text((80, billto_y), "Rechnungsempfänger:" if lang == "de" else "Bill to:", font=f_med, fill=(20, 20, 20))
    draw.text((80, billto_y + 30), data["customer_name"], font=f_small, fill=(20, 20, 20))
    draw.text((80, billto_y + 55), data["customer_address"][:80], font=f_small, fill=(20, 20, 20))

    # Table header
    y = 480
    cols_x = (80, 140, 700, 850, 1050)
    headers = (
        ("Pos.", "Beschreibung", "Menge", "Preis", "Summe")
        if lang == "de"
        else ("#", "Description", "Qty", "Unit price", "Total")
    )
    for x, h in zip(cols_x, headers):
        draw.text((x, y), h, font=f_small, fill=(0, 0, 0))
    draw.line([(80, y + 26), (1160, y + 26)], fill=(0, 0, 0), width=1)
    y += 36

    for idx, item in enumerate(data["line_items"], start=1):
        draw.text((cols_x[0], y), str(idx), font=f_small, fill=(20, 20, 20))
        draw.text((cols_x[1], y), item["description"][:42], font=f_small, fill=(20, 20, 20))
        draw.text((cols_x[2], y), str(item["qty"]), font=f_small, fill=(20, 20, 20))
        draw.text((cols_x[3], y), f"{item['unit_price']:.2f} {cur}", font=f_small, fill=(20, 20, 20))
        draw.text((cols_x[4], y), f"{item['line_total']:.2f} {cur}", font=f_small, fill=(20, 20, 20))
        y += 30

    # Totals
    y += 20
    draw.line([(800, y), (1160, y)], fill=(0, 0, 0), width=1)
    y += 15
    netto_label = "Netto:" if lang == "de" else "Subtotal:"
    draw.text((800, y), netto_label, font=f_small, fill=(0, 0, 0))
    draw.text((1050, y), f"{data['netto']:.2f} {cur}", font=f_small, fill=(0, 0, 0))
    if data["ust_rate"] > 0:
        y += 28
        ust_label = (
            f"USt ({int(data['ust_rate']*100)}%):" if lang == "de" else f"VAT ({int(data['ust_rate']*100)}%):"
        )
        draw.text((800, y), ust_label, font=f_small, fill=(0, 0, 0))
        draw.text((1050, y), f"{data['ust']:.2f} {cur}", font=f_small, fill=(0, 0, 0))
    y += 32
    total_label = "Gesamt:" if lang == "de" else "Total due:"
    draw.text((800, y), total_label, font=f_med, fill=(0, 0, 0))
    draw.text((1050, y), f"{data['brutto']:.2f} {cur}", font=f_med, fill=(0, 0, 0))

    # Footer
    draw.text((80, PAGE_H_PX - 150), f"IBAN: {vendor.iban}", font=f_small, fill=(40, 40, 40))
    draw.text((80, PAGE_H_PX - 120), data["footer_note"], font=f_small, fill=(40, 40, 40))

    return img


def _apply_scan_distortion(img: Image.Image, rng: random.Random) -> Image.Image:
    # Slight rotation
    angle = rng.uniform(-2.2, 2.2)
    img = img.rotate(angle, resample=Image.BICUBIC, fillcolor=(252, 250, 245), expand=False)

    # Light blur (scanner optics)
    img = img.filter(ImageFilter.GaussianBlur(radius=0.6))

    # Add subtle gaussian-style noise via PIL (cheap approximation)
    noise_layer = Image.effect_noise(img.size, rng.uniform(8, 16)).convert("L")
    noise_rgb = Image.merge("RGB", (noise_layer, noise_layer, noise_layer))
    img = Image.blend(img, noise_rgb, alpha=0.08)

    # JPEG round-trip at low-ish quality to introduce compression artefacts
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=rng.randint(58, 75))
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def render_scan(data: dict, output_path: Path, rng: random.Random) -> None:
    """Render `data` as a scan-look image-only PDF (no text layer)."""
    img = _draw_invoice_image(data)
    img = _apply_scan_distortion(img, rng)

    # Embed image into A4 PDF
    image_buf = io.BytesIO()
    img.save(image_buf, format="JPEG", quality=85)
    image_buf.seek(0)

    c = canvas.Canvas(str(output_path), pagesize=A4)
    page_w_mm, page_h_mm = 210 * mm, 297 * mm
    c.drawImage(
        # ReportLab supports `ImageReader` so we can hand it a BytesIO
        # by writing it temporarily, but for portability use a Reader.
        _BytesIOImageReader(image_buf),
        0,
        0,
        width=page_w_mm,
        height=page_h_mm,
    )
    c.showPage()
    c.save()


class _BytesIOImageReader:
    """Tiny ImageReader-shim so we don't import reportlab.lib.utils.ImageReader directly."""

    def __init__(self, buf: io.BytesIO) -> None:
        self._buf = buf

    def __getattr__(self, name):  # pragma: no cover — delegation
        from reportlab.lib.utils import ImageReader

        reader = ImageReader(self._buf)
        return getattr(reader, name)
