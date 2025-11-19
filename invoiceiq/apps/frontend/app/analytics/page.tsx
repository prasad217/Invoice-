"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

type SeriesPoint = { label: string; value: number };
type TopSku = { sku: string; total_qty: number; revenue: number };
type TaxBreakdown = { tax_rate: number; tax_amount: number };

type AnalyticsResponse = {
  date_range: { from?: string | null; to?: string | null };
  monthly_totals: SeriesPoint[];
  top_skus: TopSku[];
  tax_breakdown: TaxBreakdown[];
};

const tooltipFormatter = (value: number) => `₹${value.toFixed(2)}`;

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const res = await fetch(`${API}/analytics/summary`);
        if (!res.ok) throw new Error("Failed to load analytics");
        setData(await res.json());
      } catch (err: any) {
        setError(err.message || "Failed to load analytics");
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-gray-50 text-gray-600">
        Loading analytics…
      </main>
    );
  }

  if (!data) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center bg-gray-50 gap-4 text-gray-600">
        <p>{error || "Analytics unavailable"}</p>
        <Link href="/" className="text-blue-600 hover:underline">
          Back to dashboard
        </Link>
      </main>
    );
  }

  const { monthly_totals, top_skus, tax_breakdown } = data;

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-600 uppercase tracking-wide">Insights</p>
            <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>
            <p className="text-gray-600 mt-1">
              Revenue, SKU velocity, and tax mix generated directly from your uploaded invoices.
            </p>
          </div>
          <Link
            href="/"
            className="px-4 py-2 rounded-lg border border-blue-200 text-blue-700 font-medium hover:bg-blue-50"
          >
            ← Back to dashboard
          </Link>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-50 text-red-800 border border-red-200 text-sm font-medium">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">Monthly totals</h2>
              <span className="text-sm text-gray-500">₹ value per month</span>
            </div>
            <div className="h-72">
              {monthly_totals.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={monthly_totals} margin={{ top: 10, left: 0, right: 10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="label" stroke="#6b7280" />
                    <YAxis stroke="#6b7280" tickFormatter={(value) => `₹${value / 1000}k`} />
                    <Tooltip formatter={(value: number) => tooltipFormatter(value)} />
                    <Line type="monotone" dataKey="value" stroke="#2563eb" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-gray-500 text-center mt-12">No monthly data yet</p>
              )}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">Tax breakdown</h2>
              <span className="text-sm text-gray-500">GST amounts by rate</span>
            </div>
            <div className="h-72">
              {tax_breakdown.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={tax_breakdown} margin={{ top: 10, left: 0, right: 10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="tax_rate" stroke="#6b7280" tickFormatter={(value) => `${value}%`} />
                    <YAxis stroke="#6b7280" tickFormatter={(value) => `₹${value / 1000}k`} />
                    <Tooltip formatter={(value: number) => tooltipFormatter(value)} />
                    <Bar dataKey="tax_amount" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-gray-500 text-center mt-12">No tax data yet</p>
              )}
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Top SKUs</h2>
            <span className="text-sm text-gray-500">Sorted by revenue</span>
          </div>
          {top_skus.length ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-600 uppercase">SKU</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-600 uppercase">
                      Quantity
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-600 uppercase">
                      Revenue
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {top_skus.map((sku) => (
                    <tr key={sku.sku}>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{sku.sku}</td>
                      <td className="px-4 py-3 text-sm text-gray-700">{sku.total_qty.toFixed(2)}</td>
                      <td className="px-4 py-3 text-sm text-gray-900">₹{sku.revenue.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">Upload invoices to populate SKU insights.</p>
          )}
        </div>
      </div>
    </main>
  );
}
