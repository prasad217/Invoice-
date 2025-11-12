import datetime as dt
import io
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:  # Optional heavy dependencies
    from pdf2image import convert_from_bytes
except Exception:  # pragma: no cover - optional dependency
    convert_from_bytes = None

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency
    Image = None  # type: ignore

try:
    from paddleocr import PaddleOCR
    import numpy as np
except Exception:  # pragma: no cover - optional dependency
    PaddleOCR = None  # type: ignore
    np = None  # type: ignore

logger = logging.getLogger(__name__)

GSTIN_RE = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]\dZ\d\b")
INVOICE_RE = re.compile(r"(?:invoice\s*(?:no\.?|number)?[:\s]*)([A-Z0-9\-\/]+)", re.IGNORECASE)
DATE_RE = re.compile(r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})")
CURRENCY_RE = re.compile(r"(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)")


@dataclass
class ParsedInvoice:
    supplier_name: Optional[str]
    supplier_gstin: Optional[str]
    invoice_no: str
    invoice_date: str
    subtotal: float
    tax: float
    total: float
    items: List[Dict[str, Any]]


class PaddleEngine:
    """Thin wrapper so we only instantiate PaddleOCR when the dependency is available."""

    def __init__(self) -> None:
        self._ocr = None
        if PaddleOCR and np is not None:
            try:
                self._ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
                logger.info("PaddleOCR initialized for invoice extraction")
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed to initialize PaddleOCR: %s", exc)
                self._ocr = None

    @property
    def ready(self) -> bool:
        return self._ocr is not None

    def extract_text(self, image) -> str:
        if not self._ocr or np is None:
            return ""
        try:
            result = self._ocr.ocr(np.array(image), cls=True)
        except Exception as exc:  # pragma: no cover - paddle runtime issues
            logger.warning("PaddleOCR inference failed: %s", exc)
            return ""
        lines = [line[1][0] for line in result[0]] if result and result[0] else []
        return "\n".join(lines)


class InvoiceExtractor:
    """
    Provides a single interface the API can call. If OCR deps are missing, we
    gracefully fall back to a deterministic stub so local development keeps working.
    """

    def __init__(self) -> None:
        self._paddle = PaddleEngine()

    def extract(self, file_bytes: bytes, content_type: Optional[str]) -> Dict[str, Any]:
        image = self._load_image(file_bytes, content_type)
        text = self._paddle.extract_text(image) if image is not None else ""

        if text.strip():
            parsed = self._parse_text(text)
        else:
            parsed = self._fallback_result()

        return {
            "supplier_name": parsed.supplier_name,
            "supplier_gstin": parsed.supplier_gstin,
            "invoice_no": parsed.invoice_no,
            "invoice_date": parsed.invoice_date,
            "subtotal": parsed.subtotal,
            "tax": parsed.tax,
            "total": parsed.total,
            "items": parsed.items,
        }

    def _load_image(self, file_bytes: bytes, content_type: Optional[str]):
        if Image is None:
            logger.debug("Pillow not available, skipping OCR")
            return None

        try:
            if content_type and "pdf" in content_type:
                if convert_from_bytes is None:
                    logger.debug("pdf2image is not available, cannot parse PDF file")
                    return None
                pages = convert_from_bytes(file_bytes, first_page=1, last_page=1)
                return pages[0].convert("RGB") if pages else None
            return Image.open(io.BytesIO(file_bytes)).convert("RGB")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to load file for OCR: %s", exc)
            return None

    def _parse_text(self, text: str) -> ParsedInvoice:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        supplier_name = self._guess_supplier(lines)
        supplier_gstin = self._search_regex(GSTIN_RE, text)
        invoice_no = self._search_regex(INVOICE_RE, text, group=1)
        invoice_date = self._search_regex(DATE_RE, text)
        subtotal = self._find_amount(lines, re.compile(r"sub\s*total", re.IGNORECASE))
        tax = self._find_amount(lines, re.compile(r"(tax|gst)", re.IGNORECASE))
        total = self._find_amount(lines, re.compile(r"total|amount\s+due", re.IGNORECASE))

        now = dt.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        invoice_no = invoice_no or f"AUTO-{now}"
        invoice_date = self._normalize_date(invoice_date) or dt.date.today().isoformat()
        subtotal = subtotal or 0.0
        tax = tax or 0.0
        total = total or max(subtotal + tax, 0.0)

        items = [{
            "sku": "OCR-DETECTED",
            "description": "Line items pending structured extraction",
            "qty": 1,
            "unit_price": subtotal or total,
            "tax_rate": 0 if total == subtotal else round((tax / max(subtotal, 1)) * 100, 2),
            "line_total": total,
        }]

        return ParsedInvoice(
            supplier_name=supplier_name,
            supplier_gstin=supplier_gstin,
            invoice_no=invoice_no,
            invoice_date=invoice_date,
            subtotal=round(subtotal, 2),
            tax=round(tax, 2),
            total=round(total, 2),
            items=items,
        )

    def _fallback_result(self) -> ParsedInvoice:
        today = dt.date.today().isoformat()
        total = 1180.0
        subtotal = 1000.0
        tax = 180.0
        return ParsedInvoice(
            supplier_name="Acme Supplies",
            supplier_gstin="29ABCDE1234F1Z5",
            invoice_no="AUTO-" + dt.datetime.utcnow().strftime("%Y%m%d%H%M%S"),
            invoice_date=today,
            subtotal=subtotal,
            tax=tax,
            total=total,
            items=[{
                "sku": "SKU-DEMO",
                "description": "Demo Item",
                "qty": 10,
                "unit_price": 100.0,
                "tax_rate": 18.0,
                "line_total": total,
            }],
        )

    def _search_regex(self, regex: re.Pattern, text: str, group: int = 0) -> Optional[str]:
        match = regex.search(text)
        if not match:
            return None
        return match.group(group)

    def _find_amount(self, lines: List[str], label_regex: re.Pattern) -> Optional[float]:
        for line in lines:
            if label_regex.search(line):
                match = CURRENCY_RE.search(line)
                if match:
                    return self._parse_amount(match.group(1))
        return None

    def _parse_amount(self, value: str) -> float:
        normalized = value.replace(",", "")
        try:
            return float(normalized)
        except ValueError:
            return 0.0

    def _normalize_date(self, date_str: Optional[str]) -> Optional[str]:
        if not date_str:
            return None
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%Y-%m-%d"):
            try:
                return dt.datetime.strptime(date_str, fmt).date().isoformat()
            except ValueError:
                continue
        return None

    def _guess_supplier(self, lines: List[str]) -> Optional[str]:
        for line in lines[:5]:
            if "invoice" in line.lower():
                continue
            if any(ch.isalpha() for ch in line):
                return line
        return None
