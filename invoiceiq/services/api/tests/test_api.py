import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy import text

from app import main


def _seed_invoice(
    supplier_name: str = "Seed Supplier",
    invoice_no: str = "INV-SEED-1",
    invoice_date: dt.date | None = None,
    subtotal: float = 100.0,
    tax: float = 18.0,
    total: float = 118.0,
):
    invoice_date = invoice_date or dt.date.today()
    with main.engine.begin() as conn:
        inv = conn.execute(
            text(
                """
                INSERT INTO invoices (supplier_name, supplier_gstin, invoice_no, invoice_date,
                                      subtotal, tax, total, status)
                VALUES (:supplier_name,:supplier_gstin,:invoice_no,:invoice_date,
                        :subtotal,:tax,:total,'PENDING')
                """
            ),
            {
                "supplier_name": supplier_name,
                "supplier_gstin": "29ABCDE1234F1Z5",
                "invoice_no": invoice_no,
                "invoice_date": invoice_date,
                "subtotal": subtotal,
                "tax": tax,
                "total": total,
            },
        )
        invoice_id = inv.lastrowid
        conn.execute(
            text(
                """
                INSERT INTO invoice_items (invoice_id, sku, description, qty, unit_price, tax_rate, line_total)
                VALUES (:invoice_id, :sku, :description, :qty, :unit_price, :tax_rate, :line_total)
                """
            ),
            {
                "invoice_id": invoice_id,
                "sku": "SKU-123",
                "description": "Seed item",
                "qty": 2,
                "unit_price": subtotal / 2,
                "tax_rate": 18.0,
                "line_total": total,
            },
        )
    return invoice_id


def test_extract_endpoint_inserts_invoice(monkeypatch, client: TestClient):
    fake_result = {
        "supplier_name": "OCR Supplier",
        "supplier_gstin": "22ABCDE1234F1Z5",
        "invoice_no": "AUTO-TEST-1",
        "invoice_date": dt.date.today().isoformat(),
        "subtotal": 200.0,
        "tax": 36.0,
        "total": 236.0,
        "items": [
            {
                "sku": "SKU-OCR",
                "description": "Detected item",
                "qty": 1,
                "unit_price": 200.0,
                "tax_rate": 18.0,
                "line_total": 236.0,
            }
        ],
    }

    class StubExtractor:
        def extract(self, *_args, **_kwargs):
            return fake_result

    monkeypatch.setattr(main, "ocr_service", StubExtractor())

    resp = client.post("/extract", files={"file": ("invoice.jpg", b"fake-bytes", "image/jpeg")})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["invoice_no"] == fake_result["invoice_no"]

    listing = client.get("/invoices").json()
    assert len(listing["invoices"]) == 1
    assert listing["invoices"][0]["invoice_no"] == fake_result["invoice_no"]


def test_invoice_update_and_retrieve_flow(client: TestClient):
    invoice_id = _seed_invoice()

    detail = client.get(f"/invoices/{invoice_id}")
    assert detail.status_code == 200
    assert detail.json()["invoice_no"] == "INV-SEED-1"

    updated_payload = {
        "supplier_name": "Updated Supplier",
        "supplier_gstin": "33ABCDE1234F1Z5",
        "invoice_no": "INV-UPDATED-99",
        "invoice_date": dt.date.today().isoformat(),
        "subtotal": 500.0,
        "tax": 90.0,
        "total": 590.0,
        "status": "APPROVED",
        "items": [
            {
                "sku": "SKU-UPDATED",
                "description": "Updated item",
                "qty": 5,
                "unit_price": 100.0,
                "tax_rate": 18.0,
                "line_total": 590.0,
            }
        ],
    }

    resp = client.put(f"/invoices/{invoice_id}", json=updated_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "APPROVED"
    assert data["invoice_no"] == "INV-UPDATED-99"
    assert data["items"][0]["sku"] == "SKU-UPDATED"


def test_analytics_summary_returns_metrics(client: TestClient):
    first_id = _seed_invoice(
        supplier_name="First Vendor",
        invoice_no="INV-AN-1",
        invoice_date=dt.date(2024, 1, 15),
        subtotal=1000.0,
        tax=180.0,
        total=1180.0,
    )
    second_id = _seed_invoice(
        supplier_name="Second Vendor",
        invoice_no="INV-AN-2",
        invoice_date=dt.date(2024, 2, 10),
        subtotal=2000.0,
        tax=360.0,
        total=2360.0,
    )
    assert first_id != second_id

    resp = client.get("/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["monthly_totals"]) >= 2
    assert data["top_skus"][0]["revenue"] > 0
    assert data["tax_breakdown"][0]["tax_amount"] > 0
