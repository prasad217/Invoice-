import datetime as dt
import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.ocr import InvoiceExtractor


def _build_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "invoiceiq")
    user = os.getenv("DB_USER", "invoice")
    password = os.getenv("DB_PASSWORD", "invoice")
    return f"mysql://{user}:{password}@{host}:{port}/{name}"


DATABASE_URL = _build_database_url()
engine: Engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
ocr_service = InvoiceExtractor()

app = FastAPI(title="InvoiceIQ API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)


def _to_iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    return str(value)


class InvoiceItemPayload(BaseModel):
    sku: Optional[str] = None
    description: Optional[str] = None
    qty: float = Field(ge=0)
    unit_price: float = Field(ge=0)
    tax_rate: float = Field(ge=0)
    line_total: float = Field(ge=0)


class ExtractionResult(BaseModel):
    supplier_name: Optional[str]
    supplier_gstin: Optional[str]
    invoice_no: str
    invoice_date: str
    subtotal: float
    tax: float
    total: float
    items: List[InvoiceItemPayload] = Field(min_length=1)


class InvoiceDetail(BaseModel):
    id: int
    supplier_name: Optional[str]
    supplier_gstin: Optional[str]
    invoice_no: str
    invoice_date: Optional[str]
    subtotal: float
    tax: float
    total: float
    status: str
    created_at: Optional[str]
    items: List[InvoiceItemPayload]


class InvoiceUpdatePayload(BaseModel):
    supplier_name: Optional[str] = None
    supplier_gstin: Optional[str] = None
    invoice_no: str
    invoice_date: Optional[dt.date] = None
    subtotal: float
    tax: float
    total: float
    status: str = Field(default="PENDING")
    items: List[InvoiceItemPayload] = Field(min_length=1)

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        if not value:
            return "PENDING"
        upper = value.upper()
        if upper not in {"PENDING", "APPROVED"}:
            raise ValueError("status must be PENDING or APPROVED")
        return upper


class InvoiceSummary(BaseModel):
    id: int
    supplier_name: Optional[str]
    invoice_no: str
    total: float
    status: str
    created_at: Optional[str]


class SeriesPoint(BaseModel):
    label: str
    value: float


class TaxBreakdownPoint(BaseModel):
    tax_rate: float
    tax_amount: float


class AnalyticsSummary(BaseModel):
    date_range: Dict[str, Optional[str]]
    monthly_totals: List[SeriesPoint]
    top_skus: List[Dict[str, Any]]
    tax_breakdown: List[TaxBreakdownPoint]


@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"ok": True}


@app.post("/extract", response_model=ExtractionResult)
async def extract(file: UploadFile = File(...)):
    contents = await file.read()
    result = ocr_service.extract(contents, file.content_type)

    with engine.begin() as conn:
        invoice_date_str = result.get("invoice_date") or dt.date.today().isoformat()
        try:
            invoice_date = dt.date.fromisoformat(invoice_date_str)
        except ValueError:
            invoice_date = dt.date.today()
        inv = conn.execute(
            text(
                """
                INSERT INTO invoices (
                    supplier_name, supplier_gstin, invoice_no, invoice_date,
                    subtotal, tax, total, status
                )
                VALUES (:supplier_name,:supplier_gstin,:invoice_no,:invoice_date,
                        :subtotal,:tax,:total,'PENDING')
                """
            ),
            {
                "supplier_name": result["supplier_name"],
                "supplier_gstin": result["supplier_gstin"],
                "invoice_no": result["invoice_no"],
                "invoice_date": invoice_date,
                "subtotal": result["subtotal"],
                "tax": result["tax"],
                "total": result["total"],
            },
        )
        invoice_id = inv.lastrowid

        for item in result["items"]:
            conn.execute(
                text(
                    """
                    INSERT INTO invoice_items (
                        invoice_id, sku, description, qty, unit_price, tax_rate, line_total
                    )
                    VALUES (:invoice_id,:sku,:description,:qty,:unit_price,:tax_rate,:line_total)
                    """
                ),
                {"invoice_id": invoice_id, **item},
            )

    return result


@app.get("/invoices", response_model=Dict[str, List[InvoiceSummary]])
def list_invoices():
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, supplier_name, invoice_no, total, status, created_at
                FROM invoices
                ORDER BY created_at DESC
                LIMIT 50
                """
            )
        ).mappings().all()

    invoices = [
        InvoiceSummary(
            id=row["id"],
            supplier_name=row["supplier_name"],
            invoice_no=row["invoice_no"],
            total=_to_float(row["total"]),
            status=row["status"],
            created_at=_to_iso(row["created_at"]),
        )
        for row in rows
    ]
    return {"invoices": invoices}


@app.get("/invoices/{invoice_id}", response_model=InvoiceDetail)
def get_invoice(invoice_id: int):
    with engine.connect() as conn:
        invoice = conn.execute(
            text(
                """
                SELECT id, supplier_name, supplier_gstin, invoice_no, invoice_date,
                       subtotal, tax, total, status, created_at
                FROM invoices
                WHERE id = :invoice_id
                """
            ),
            {"invoice_id": invoice_id},
        ).mappings().first()

        if not invoice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

        items = conn.execute(
            text(
                """
                SELECT id, sku, description, qty, unit_price, tax_rate, line_total
                FROM invoice_items
                WHERE invoice_id = :invoice_id
                ORDER BY id ASC
                """
            ),
            {"invoice_id": invoice_id},
        ).mappings().all()

    return InvoiceDetail(
        id=invoice["id"],
        supplier_name=invoice["supplier_name"],
        supplier_gstin=invoice["supplier_gstin"],
        invoice_no=invoice["invoice_no"],
        invoice_date=_to_iso(invoice["invoice_date"]),
        subtotal=_to_float(invoice["subtotal"]),
        tax=_to_float(invoice["tax"]),
        total=_to_float(invoice["total"]),
        status=invoice["status"],
        created_at=_to_iso(invoice["created_at"]),
        items=[
            InvoiceItemPayload(
                sku=item["sku"],
                description=item["description"],
                qty=_to_float(item["qty"]),
                unit_price=_to_float(item["unit_price"]),
                tax_rate=_to_float(item["tax_rate"]),
                line_total=_to_float(item["line_total"]),
            )
            for item in items
        ],
    )


@app.put("/invoices/{invoice_id}", response_model=InvoiceDetail)
def update_invoice(invoice_id: int, payload: InvoiceUpdatePayload):
    payload_items = payload.items

    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM invoices WHERE id = :invoice_id"),
            {"invoice_id": invoice_id},
        ).scalar()

        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

        status_value = payload.status

        conn.execute(
            text(
                """
                UPDATE invoices
                SET supplier_name=:supplier_name,
                    supplier_gstin=:supplier_gstin,
                    invoice_no=:invoice_no,
                    invoice_date=:invoice_date,
                    subtotal=:subtotal,
                    tax=:tax,
                    total=:total,
                    status=:status
                WHERE id=:invoice_id
                """
            ),
            {
                "invoice_id": invoice_id,
                "supplier_name": payload.supplier_name,
                "supplier_gstin": payload.supplier_gstin,
                "invoice_no": payload.invoice_no,
                "invoice_date": payload.invoice_date,
                "subtotal": payload.subtotal,
                "tax": payload.tax,
                "total": payload.total,
                "status": status_value,
            },
        )

        conn.execute(text("DELETE FROM invoice_items WHERE invoice_id=:invoice_id"), {"invoice_id": invoice_id})
        for item in payload_items:
            conn.execute(
                text(
                    """
                    INSERT INTO invoice_items (
                        invoice_id, sku, description, qty, unit_price, tax_rate, line_total
                    ) VALUES (
                        :invoice_id,:sku,:description,:qty,:unit_price,:tax_rate,:line_total
                    )
                    """
                ),
                {"invoice_id": invoice_id, **item.model_dump()},
            )

    return get_invoice(invoice_id)


def _month_bucket_expression() -> str:
    if engine.url.get_backend_name().startswith("sqlite"):
        return "strftime('%Y-%m', invoice_date)"
    return "DATE_FORMAT(invoice_date, '%Y-%m')"


@app.get("/analytics/summary", response_model=AnalyticsSummary)
def analytics_summary(from_date: Optional[dt.date] = None, to_date: Optional[dt.date] = None):
    clauses = []
    params: Dict[str, Any] = {}
    if from_date:
        clauses.append("invoice_date >= :from_date")
        params["from_date"] = from_date
    if to_date:
        clauses.append("invoice_date <= :to_date")
        params["to_date"] = to_date
    where = " AND ".join(clauses) if clauses else "1=1"

    month_bucket = _month_bucket_expression()

    with engine.connect() as conn:
        monthly_rows = conn.execute(
            text(
                f"""
                SELECT {month_bucket} AS bucket, SUM(total) AS total
                FROM invoices
                WHERE {where}
                GROUP BY bucket
                ORDER BY bucket
                """
            ),
            params,
        ).mappings().all()

        sku_rows = conn.execute(
            text(
                f"""
                SELECT ii.sku AS sku,
                       SUM(ii.qty) AS total_qty,
                       SUM(ii.line_total) AS revenue
                FROM invoice_items ii
                JOIN invoices i ON i.id = ii.invoice_id
                WHERE {where}
                GROUP BY ii.sku
                ORDER BY revenue DESC
                LIMIT 5
                """
            ),
            params,
        ).mappings().all()

        tax_rows = conn.execute(
            text(
                f"""
                SELECT COALESCE(ii.tax_rate, 0) AS tax_rate,
                       SUM(ii.qty * ii.unit_price * (COALESCE(ii.tax_rate, 0) / 100.0)) AS tax_amount
                FROM invoice_items ii
                JOIN invoices i ON i.id = ii.invoice_id
                WHERE {where}
                GROUP BY COALESCE(ii.tax_rate, 0)
                ORDER BY tax_rate
                """
            ),
            params,
        ).mappings().all()

    monthly = [SeriesPoint(label=row["bucket"], value=_to_float(row["total"])) for row in monthly_rows if row["bucket"]]
    top_skus = [
        {
            "sku": row["sku"] or "UNLABELED",
            "total_qty": _to_float(row["total_qty"]),
            "revenue": _to_float(row["revenue"]),
        }
        for row in sku_rows
    ]
    taxes = [
        TaxBreakdownPoint(tax_rate=_to_float(row["tax_rate"]), tax_amount=_to_float(row["tax_amount"]))
        for row in tax_rows
    ]

    return AnalyticsSummary(
        date_range={
            "from": from_date.isoformat() if from_date else None,
            "to": to_date.isoformat() if to_date else None,
        },
        monthly_totals=monthly,
        top_skus=top_skus,
        tax_breakdown=taxes,
    )
