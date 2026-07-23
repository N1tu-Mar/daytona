"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, get } from "@/lib/api";
import type { PaPacket } from "@/lib/types";

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  approved: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  submitted: "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
};

export default function PaPacketsPage() {
  const [packets, setPackets] = useState<PaPacket[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    get<PaPacket[]>("/pa-packets")
      .then((data) => {
        if (!cancelled) setPackets(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? `Backend returned ${err.status}: ${err.message}`
              : "Could not reach the backend."
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">Prior authorization packets</h1>
        <p className="mt-1 text-sm text-slate-500">
          Every sentence traces to a source. Physician approval is required before submission.
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          {error}
        </div>
      )}

      {!error && packets === null && (
        <p className="text-sm text-slate-400">Loading packets…</p>
      )}

      {packets !== null && packets.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 px-6 py-12 text-center text-sm text-slate-500 dark:border-slate-700">
          <p className="font-medium text-slate-600 dark:text-slate-300">No PA packets yet.</p>
          <p className="mt-1">
            Packets appear here once the prior-auth drafting service generates one for an
            approved verdict.
          </p>
        </div>
      )}

      {packets !== null && packets.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="bg-slate-100 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900 dark:text-slate-400">
              <tr>
                <th className="px-4 py-2 font-medium">Packet</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Payer status</th>
                <th className="px-4 py-2 font-medium">Days saved</th>
                <th className="px-4 py-2 font-medium">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              {packets.map((p) => (
                <tr
                  key={p.id}
                  className="bg-white hover:bg-slate-50 dark:bg-slate-950 dark:hover:bg-slate-900"
                >
                  <td className="px-4 py-3">
                    <Link
                      href={`/pa-packets/${p.id}`}
                      className="font-mono text-xs font-medium text-slate-900 hover:underline dark:text-slate-100"
                    >
                      {p.id}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                        STATUS_STYLES[p.status] || STATUS_STYLES.draft
                      }`}
                    >
                      {p.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-500">{p.payer_status || "—"}</td>
                  <td className="px-4 py-3 text-slate-500">{p.days_saved ?? "—"}</td>
                  <td className="px-4 py-3 text-slate-500">
                    {new Date(p.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
