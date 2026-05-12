"""Vendor master data, Faker setup, and product catalogues for synthetic invoices."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from faker import Faker

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
VENDORS_PATH = DATA_DIR / "vendors.json"


@dataclass(frozen=True)
class Vendor:
    id: str
    name: str
    country: str
    address: str
    vat_id: str
    iban: str
    default_category: str
    default_currency: str
    template: str


def load_vendors() -> list[Vendor]:
    payload = json.loads(VENDORS_PATH.read_text(encoding="utf-8"))
    return [Vendor(**v) for v in payload]


def vendors_by_template(vendors: list[Vendor]) -> dict[str, list[Vendor]]:
    out: dict[str, list[Vendor]] = {}
    for v in vendors:
        out.setdefault(v.template, []).append(v)
    return out


UNKNOWN_VENDORS: list[Vendor] = [
    Vendor(
        id="UNKNOWN-A",
        name="FremdAG Handelsgesellschaft mbH",
        country="DE",
        address="Industriestraße 99, 99999 Musterstadt",
        vat_id="DE999000111",
        iban="DE00 1111 2222 3333 4444 55",
        default_category="Sonstiges",
        default_currency="EUR",
        template="office_supplies",
    ),
    Vendor(
        id="UNKNOWN-B",
        name="Stranger & Co. Inc.",
        country="US",
        address="42 Unknown Lane, Springfield, IL 62701",
        vat_id="EIN 99-9999999",
        iban="US-ACH 999999999 | Acct 0000000001",
        default_category="Sonstiges",
        default_currency="USD",
        template="consulting",
    ),
    Vendor(
        id="UNKNOWN-C",
        name="Helvetia Bürobedarf AG",
        country="CH",
        address="Bahnhofstrasse 1, 8001 Zürich",
        vat_id="CHE-123.456.789 MWST",
        iban="CH56 0483 5012 3456 7800 9",
        default_category="Bürobedarf",
        default_currency="CHF",
        template="office_supplies",
    ),
]


def make_faker(locale: Literal["de_DE", "en_US"]) -> Faker:
    return Faker(locale)


# Product catalogues: per template, list of (description_local, min_price, max_price).
# Currency is determined by the vendor, not the catalogue.
PRODUCT_CATALOGS: dict[str, list[tuple[str, float, float]]] = {
    "webshop": [
        ("Bluetooth-Kopfhörer Modell X", 39.90, 129.00),
        ("USB-C Schnellladegerät 65W", 14.90, 29.90),
        ("Notizbuch A5, dotted", 6.50, 14.90),
        ("Premium Tee-Set, 4 Sorten", 24.90, 49.00),
        ("Bio-Kaffeebohnen 1kg", 12.90, 28.50),
        ("Tasse mit Logo, Keramik", 9.90, 18.00),
        ("Powerbank 20.000 mAh", 29.90, 79.90),
        ("Schreibtisch-Organizer Holz", 19.90, 44.90),
    ],
    "consulting": [
        ("Strategy consulting (hours)", 180.0, 350.0),
        ("Workshop facilitation (day)", 1800.0, 3200.0),
        ("Executive coaching session", 450.0, 950.0),
        ("Market study & report", 2500.0, 7500.0),
        ("Implementation oversight (day)", 1400.0, 2400.0),
    ],
    "office_supplies": [
        ("Druckerpapier A4, 500 Blatt", 4.90, 9.50),
        ("Tintenpatronen-Set HP 304", 39.00, 89.00),
        ("Locher Leitz NeXXt, Metall", 12.00, 22.00),
        ("Kugelschreiber, 10er-Pack blau", 7.50, 14.00),
        ("Aktenordner breit, schwarz", 3.50, 7.00),
        ("Klebeband transparent, 6er-Pack", 5.90, 11.50),
        ("Briefumschläge DIN lang, 100 Stk", 9.90, 18.00),
        ("Textmarker 4er-Pack sortiert", 6.50, 12.90),
        ("Schreibtischunterlage A2", 14.90, 28.00),
    ],
}


def random_invoice_number(rng: random.Random, year: int | None = None) -> str:
    y = year if year is not None else rng.randint(2024, 2026)
    return f"INV-{y}-{rng.randint(10000, 99999)}"


def pick_items(template: str, n: int, rng: random.Random) -> list[tuple[str, float, float]]:
    catalogue = PRODUCT_CATALOGS[template]
    return rng.sample(catalogue, k=min(n, len(catalogue)))
