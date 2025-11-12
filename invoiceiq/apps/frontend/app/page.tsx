"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

type Invoice = {
  id: number;
  supplier_name: string;
  invoice_no: string;
  total: number;
  status: string;
  created_at: string;
};

type MessageType = 'success' | 'error' | 'info';

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [msg, setMsg] = useState<string>('');
  const [msgType, setMsgType] = useState<MessageType>('info');

  // Fetch all invoices
  const refresh = async () => {
    try {
      const res = await fetch(`${API}/invoices`);
      if (!res.ok) throw new Error('Failed to fetch invoices');
      const data = await res.json();
      setInvoices(data.invoices || []);
    } catch (e: any) {
      setMsg('Failed to load invoices');
      setMsgType('error');
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const onUpload = async () => {
    if (!file) {
      setMsg('Please select a file');
      setMsgType('error');
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      setMsg('File size must be less than 5MB');
      setMsgType('error');
      return;
    }

    setBusy(true);
    setMsg('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API}/extract`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Upload failed');
      }

      const data = await res.json();
      setMsg(
        `✓ Extracted invoice ${data.invoice_no} • Total ₹${data.total.toFixed(2)}`
      );
      setMsgType('success');
      setFile(null);
      await refresh();
    } catch (e: any) {
      setMsg(e.message || 'An error occurred');
      setMsgType('error');
    } finally {
      setBusy(false);
    }
  };

  const statusBadge = (value: string) => {
    const normalized = value?.toUpperCase?.() || 'PENDING';
    const styles: Record<string, string> = {
      APPROVED: 'bg-green-100 text-green-800',
      PENDING: 'bg-yellow-100 text-yellow-800',
    };
    const style = styles[normalized] || 'bg-gray-100 text-gray-800';
    const label = normalized.charAt(0) + normalized.slice(1).toLowerCase();
    return <span className={`px-3 py-1 rounded-full text-xs font-medium ${style}`}>{label}</span>;
  };

  const formatDate = (value?: string) => {
    if (!value) return '—';
    return new Date(value).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-4xl font-bold text-gray-900">InvoiceIQ</h1>
            <p className="text-gray-600 mt-2">
              AI-powered invoice extraction & billing insights
            </p>
          </div>
          <div className="flex gap-3">
            <Link
              href="/analytics"
              className="px-4 py-2 rounded-lg border border-blue-200 text-blue-700 font-medium hover:bg-blue-50 transition"
            >
              View Analytics
            </Link>
          </div>
        </div>

        {/* Upload Section */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Upload Invoice
          </h2>
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Image or PDF
              </label>
              <input
                type="file"
                accept="image/*,application/pdf"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                disabled={busy}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
            </div>
            <button
              onClick={onUpload}
              disabled={!file || busy}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition"
            >
              {busy ? 'Uploading…' : 'Extract'}
            </button>
          </div>

          {/* Message Alert */}
          {msg && (
            <div
              className={`mt-4 p-3 rounded-lg text-sm font-medium ${
                msgType === 'success'
                  ? 'bg-green-50 text-green-800 border border-green-200'
                  : msgType === 'error'
                  ? 'bg-red-50 text-red-800 border border-red-200'
                  : 'bg-blue-50 text-blue-800 border border-blue-200'
              }`}
            >
              {msg}
            </div>
          )}
        </div>

        {/* Invoices Table */}
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <div className="p-6 border-b">
            <h2 className="text-lg font-semibold text-gray-900">
              Recent Invoices
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                    Supplier
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                    Invoice #
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-700 uppercase">
                    Total
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {invoices.length > 0 ? (
                  invoices.map((inv) => (
                    <tr key={inv.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm text-gray-900">
                        {inv.supplier_name}
                      </td>
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">
                        {inv.invoice_no}
                      </td>
                      <td className="px-6 py-4 text-sm text-right text-gray-900">
                        ₹{inv.total.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 text-sm">{statusBadge(inv.status)}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{formatDate(inv.created_at)}</td>
                      <td className="px-6 py-4 text-sm">
                        <Link
                          href={`/invoices/${inv.id}`}
                          className="text-blue-600 font-medium hover:underline"
                        >
                          Review
                        </Link>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                      No invoices yet. Upload your first invoice to get started.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </main>
  );
}
