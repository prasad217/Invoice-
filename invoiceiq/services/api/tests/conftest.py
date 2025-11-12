import os
import pathlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

# Use a per-test sqlite database to avoid requiring MySQL for unit tests.
TEST_DB_PATH = pathlib.Path(__file__).with_suffix(".sqlite")
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{TEST_DB_PATH}"

from app import main  # noqa: E402  # env vars must be set before this import


def _bootstrap_sqlite() -> None:
    with main.engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    supplier_name TEXT,
                    supplier_gstin TEXT,
                    invoice_no TEXT NOT NULL,
                    invoice_date DATE,
                    subtotal REAL,
                    tax REAL,
                    total REAL,
                    status TEXT DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS invoice_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id INTEGER NOT NULL,
                    sku TEXT,
                    description TEXT,
                    qty REAL,
                    unit_price REAL,
                    tax_rate REAL,
                    line_total REAL,
                    FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
                )
                """
            )
        )


_bootstrap_sqlite()


@pytest.fixture(autouse=True)
def clean_tables():
    with main.engine.begin() as conn:
        conn.execute(text("DELETE FROM invoice_items"))
        conn.execute(text("DELETE FROM invoices"))
    yield


@pytest.fixture()
def client():
    return TestClient(main.app)
