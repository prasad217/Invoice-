"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

type InvoiceItem = {
  sku?: string | null;
  description?: string | null;
  qty: number;
  unit_price: number;
  tax_rate: number;
  line_total: number;
};

type InvoiceDetail = {
  id: number;
  supplier_name?: string | null;
  supplier_gstin?: string | null;
  invoice_no: string;
  invoice_date?: string | null;
  subtotal: number;
  tax: number;
  total: number;
  status: "PENDING" | "APPROVED";
  items: InvoiceItem[];
};

export default function InvoiceReviewPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [invoice, setInvoice] = useState<InvoiceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const invoiceId = params?.id;

  useEffect(() => {
    const fetchInvoice = async () => {
      if (!invoiceId) return;
      try {
        const res = await fetch(`${API}/invoices/${invoiceId}`);
        if (!res.ok) throw new Error("Invoice not found");
        const data = await res.json();
        setInvoice(data);
      } catch (err: any) {
        setError(err.message || "Failed to load invoice");
      } finally {
        setLoading(false);
      }
    };
    fetchInvoice();
  }, [invoiceId]);

  const handleFieldChange = (field: keyof InvoiceDetail, value: string) => {
    if (!invoice) return;
    setInvoice({ ...invoice, [field]: value });
  };

  const handleNumberChange = (field: keyof InvoiceDetail, value: string) => {
    if (!invoice) return;
    setInvoice({ ...invoice, [field]: parseFloat(value) || 0 });
  };

  const updateItem = (index: number, field: keyof InvoiceItem, value: string) => {
    if (!invoice) return;
    const copy = [...invoice.items];
    if (field === "qty" || field === "unit_price" || field === "tax_rate" || field === "line_total") {
      copy[index] = { ...copy[index], [field]: parseFloat(value) || 0 };
    } else {
      copy[index] = { ...copy[index], [field]: value };
    }
    setInvoice({ ...invoice, items: copy });
  };

  const addItem = () => {
    if (!invoice) return;
    setInvoice({
      ...invoice,
      items: [
        ...invoice.items,
        { sku: "", description: "", qty: 1, unit_price: 0, tax_rate: 0, line_total: 0 },
      ],
    });
  };

  const removeItem = (index: number) => {
    if (!invoice) return;
    if (invoice.items.length === 1) return;
    setInvoice({
      ...invoice,
      items: invoice.items.filter((_, idx) => idx !== index),
    });
  };

  const recalcTotals = () => {
    if (!invoice) return;
    const subtotal = invoice.items.reduce((sum, item) => sum + item.qty * item.unit_price, 0);
    const tax = invoice.items.reduce(
      (sum, item) => sum + item.qty * item.unit_price * (item.tax_rate / 100),
      0
    );
    const total = subtotal + tax;
    setInvoice({ ...invoice, subtotal, tax, total });
  };

  const saveInvoice = async () => {
    if (!invoice) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const payload = {
        ...invoice,
        invoice_date: invoice.invoice_date
          ? new Date(invoice.invoice_date).toISOString().slice(0, 10)
          : null,
      };
      const res = await fetch(`${API}/invoices/${invoice.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to save invoice");
      }
      const data = await res.json();
      setInvoice(data);
      setSuccess("Invoice updated successfully");
    } catch (err: any) {
      setError(err.message || "Failed to save invoice");
    } finally {
      setSaving(false);
    }
  };

  const statusOptions: Array<InvoiceDetail["status"]> = ["PENDING", "APPROVED"];

  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center text-gray-600">
        Loading invoice…
      </main>
    );
  }

  if (!invoice) {
    return (
      <main className="min-h-screen bg-gray-50 flex flex-col items-center justify-center gap-4 text-gray-600">
        <p>{error || "Invoice not found"}</p>
        <Link href="/" className="text-blue-600 hover:underline">
          Back to dashboard
        </Link>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500">Invoice #{invoice.id}</p>
            <h1 className="text-3xl font-bold text-gray-900">{invoice.invoice_no}</h1>
          </div>
          <div className="flex gap-3">
            <button
              onClick={recalcTotals}
              className="px-4 py-2 rounded-lg border border-indigo-200 text-indigo-700 font-medium hover:bg-white"
            >
              Recalculate totals
            </button>
            <button
              onClick={saveInvoice}
              disabled={saving}
              className="px-5 py-2 rounded-lg bg-indigo-600 text-white font-semibold disabled:bg-gray-400"
            >
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </div>

        {(error || success) && (
          <div
            className={`p-3 rounded-lg text-sm font-medium ${
              error
                ? "bg-red-50 text-red-800 border border-red-200"
                : "bg-green-50 text-green-800 border border-green-200"
            }`}
          >
            {error || success}
          </div>
        )}

        <div className="bg-white rounded-lg shadow p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="text-sm text-gray-700">
              Supplier name
              <input
                className="mt-1 w-full rounded-md border border-gray-200 px-3 py-2"
                value={invoice.supplier_name || ""}
                onChange={(e) => handleFieldChange("supplier_name", e.target.value)}
              />
            </label>
            <label className="text-sm text-gray-700">
              Supplier GSTIN
              <input
                className="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 uppercase"
                value={invoice.supplier_gstin || ""}
                onChange={(e) => handleFieldChange("supplier_gstin", e.target.value.toUpperCase())}
              />
            </label>
            <label className="text-sm text-gray-700">
              Invoice number
              <input
                className="mt-1 w-full rounded-md border border-gray-200 px-3 py-2"
                value={invoice.invoice_no}
                onChange={(e) => handleFieldChange("invoice_no", e.target.value)}
              />
            </label>
            <label className="text-sm text-gray-700">
              Invoice date
              <input
                type="date"
                className="mt-1 w-full rounded-md border border-gray-200 px-3 py-2"
                value={invoice.invoice_date ? invoice.invoice_date.slice(0, 10) : ""}
                onChange={(e) => handleFieldChange("invoice_date", e.target.value)}
              />
            </label>
            <label className="text-sm text-gray-700">
              Status
              <select
                className="mt-1 w-full rounded-md border border-gray-200 px-3 py-2"
                value={invoice.status}
                onChange={(e) => handleFieldChange("status", e.target.value)}
              >
                {statusOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <label className="text-sm text-gray-700">
              Subtotal
              <input
                type="number"
                step="0.01"
                className="mt-1 w-full rounded-md border border-gray-200 px-3 py-2"
                value={invoice.subtotal}
                onChange={(e) => handleNumberChange("subtotal", e.target.value)}
              />
            </label>
            <label className="text-sm text-gray-700">
              Tax
              <input
                type="number"
                step="0.01"
                className="mt-1 w-full rounded-md border border-gray-200 px-3 py-2"
                value={invoice.tax}
                onChange={(e) => handleNumberChange("tax", e.target.value)}
              />
            </label>
            <label className="text-sm text-gray-700">
              Total
              <input
                type="number"
                step="0.01"
                className="mt-1 w-full rounded-md border border-gray-200 px-3 py-2"
                value={invoice.total}
                onChange={(e) => handleNumberChange("total", e.target.value)}
              />
            </label>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">Line items</h2>
            <button
              onClick={addItem}
              className="px-3 py-1.5 rounded-md border border-dashed border-gray-300 text-sm text-gray-700 hover:bg-gray-50"
            >
              + Add item
            </button>
          </div>
          <div className="space-y-4">
            {invoice.items.map((item, index) => (
              <div key={`item-${index}`} className="border border-gray-100 rounded-lg p-4 grid grid-cols-1 md:grid-cols-6 gap-3">
                <div className="md:col-span-2">
                  <label className="text-sm text-gray-700">
                    Description
                    <input
                      className="mt-1 w-full rounded-md border border-gray-200 px-3 py-2"
                      value={item.description || ""}
                      onChange={(e) => updateItem(index, "description", e.target.value)}
                    />
                  </label>
                </div>
                <label className="text-sm text-gray-700">
                  SKU
                  <input
                    className="mt-1 w-full rounded-md border border-gray-200 px-3 py-2"
                    value={item.sku || ""}
                    onChange={(e) => updateItem(index, "sku", e.target.value)}
                  />
                </label>
                <label className="text-sm text-gray-700">
                  Qty
                  <input
                    type="number"
                    step="0.01"
                    className="mt-1 w-full rounded-md border border-gray-200 px-3 py-2"
                    value={item.qty}
                    onChange={(e) => updateItem(index, "qty", e.target.value)}
                  />
                </label>
                <label className="text-sm text-gray-700">
                  Unit price
                  <input
                    type="number"
                    step="0.01"
                    className="mt-1 w-full rounded-md border border-gray-200 px-3 py-2"
                    value={item.unit_price}
                    onChange={(e) => updateItem(index, "unit_price", e.target.value)}
                  />
                </label>
                <label className="text-sm text-gray-700">
                  Tax %
                  <input
                    type="number"
                    step="0.01"
                    className="mt-1 w-full rounded-md border border-gray-200 px-3 py-2"
                    value={item.tax_rate}
                    onChange={(e) => updateItem(index, "tax_rate", e.target.value)}
                  />
                </label>
                <label className="text-sm text-gray-700">
                  Line total
                  <input
                    type="number"
                    step="0.01"
                    className="mt-1 w-full rounded-md border border-gray-200 px-3 py-2"
                    value={item.line_total}
                    onChange={(e) => updateItem(index, "line_total", e.target.value)}
                  />
                </label>
                <div className="md:col-span-6 flex justify-end">
                  <button
                    onClick={() => removeItem(index)}
                    className="text-sm text-red-600 hover:underline disabled:text-gray-400"
                    disabled={invoice.items.length === 1}
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="flex justify-between text-sm text-gray-600">
          <Link href="/" className="hover:underline">
            ← Back to dashboard
          </Link>
          <button onClick={() => router.refresh()} className="hover:underline">
            Refresh data
          </button>
        </div>
      </div>
    </main>
  );
}
