"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, get } from "@/lib/api";
import type { ReferralWorklistItem } from "@/lib/types";
import { DispositionBadge, UrgencyBadge } from "@/components/badges";

export default function WorklistPage() {
  const [items, setItems] = useState<ReferralWorklistItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    get<ReferralWorklistItem[]>("/referrals")
      .then((data) => {
        if (!cancelled) setItems(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? `Backend returned ${err.status}: ${err.message}`
              : "Could not reach the backend. Is it running at " +
                (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") +
                "?"
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
        <h1 className="text-2xl font-bold tracking-tight">Nurse worklist</h1>
        <p className="mt-1 text-sm text-slate-500">
          Referrals awaiting review, newest first. Approving confirms the booking.
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          {error}
        </div>
      )}

      {!error && items === null && (
        <p className="text-sm text-slate-400">Loading referrals…</p>
      )}

      {items !== null && items.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 px-6 py-12 text-center text-sm text-slate-500 dark:border-slate-700">
          No referrals yet. Seed the backend (`python -m app.seed`) to populate the worklist.
        </div>
      )}

      {items !== null && items.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="bg-slate-100 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900 dark:text-slate-400">
              <tr>
                <th className="px-4 py-2 font-medium">Patient</th>
                <th className="px-4 py-2 font-medium">Source</th>
                <th className="px-4 py-2 font-medium">Urgency</th>
                <th className="px-4 py-2 font-medium">Disposition</th>
                <th className="px-4 py-2 font-medium">Received</th>
                <th className="px-4 py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              {items.map((item) => (
                <tr
                  key={item.referral_id}
                  className="cursor-pointer bg-white transition-colors hover:bg-slate-50 dark:bg-slate-950 dark:hover:bg-slate-900"
                >
                  <td className="px-4 py-3">
                    <Link
                      href={`/worklist/${item.referral_id}`}
                      className="font-medium text-slate-900 hover:underline dark:text-slate-100"
                    >
                      {item.patient_name || (
                        <span className="italic text-slate-400 dark:text-slate-500">
                          Unknown patient
                        </span>
                      )}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    <span className="inline-flex items-center gap-1.5">
                      {item.source}
                      {item.sandbox?.sandboxed && (
                        <span
                          title={`Decoded in Daytona sandbox ${item.sandbox.sandbox_id ?? ""}`}
                          className="text-emerald-600 dark:text-emerald-400"
                        >
                          🔒
                        </span>
                      )}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {item.verdict ? (
                      // A pipeline-failure ESCALATE (no rules fired) has no
                      // assessed urgency — "routine" is just the floor value.
                      // Showing ROUTINE would read as false reassurance.
                      item.verdict.disposition === "ESCALATE" &&
                      item.verdict.rules_fired.length === 0 ? (
                        <span
                          title="Not assessed — parsing/extraction did not complete; needs human review"
                          className="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide text-amber-800 ring-1 ring-inset ring-amber-300 dark:bg-amber-950 dark:text-amber-300 dark:ring-amber-700"
                        >
                          not assessed
                        </span>
                      ) : (
                        <UrgencyBadge urgency={item.verdict.urgency} />
                      )
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {item.verdict ? (
                      <DispositionBadge disposition={item.verdict.disposition} />
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {new Date(item.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    {item.verdict?.approved_by ? (
                      <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                        Approved
                      </span>
                    ) : (
                      <span className="text-xs font-semibold text-amber-600 dark:text-amber-400">
                        Needs review
                      </span>
                    )}
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
