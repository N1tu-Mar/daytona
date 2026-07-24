"use client";

import { useEffect, useState } from "react";
import { ApiError, get } from "@/lib/api";
import type { EvalsSummary } from "@/lib/types";

function pct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

function MetricTile({
  label,
  value,
  good,
  helpText,
}: {
  label: string;
  value: string;
  good: boolean | null;
  helpText: string;
}) {
  return (
    <div
      className={`rounded-xl border p-5 ${
        good === null
          ? "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
          : good
          ? "border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950"
          : "border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-950"
      }`}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p
        className={`mt-1 text-3xl font-bold ${
          good === null
            ? "text-slate-900 dark:text-slate-100"
            : good
            ? "text-emerald-700 dark:text-emerald-300"
            : "text-red-700 dark:text-red-300"
        }`}
      >
        {value}
      </p>
      <p className="mt-1 text-xs text-slate-500">{helpText}</p>
    </div>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<EvalsSummary | null>(null);
  const [notRun, setNotRun] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    get<EvalsSummary>("/evals/summary")
      .then((data) => {
        if (!cancelled) setSummary(data);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setNotRun(true);
        } else {
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
        <h1 className="text-2xl font-bold tracking-tight">Safety evals</h1>
        <p className="mt-1 text-sm text-slate-500">
          Escalation recall and false reassurance rate are the headline numbers — they measure
          whether the rule engine ever under-routes a case that should have been urgent.
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          {error}
        </div>
      )}

      {notRun && (
        <div className="rounded-lg border border-dashed border-slate-300 px-6 py-12 text-center text-sm text-slate-500 dark:border-slate-700">
          <p className="font-medium text-slate-600 dark:text-slate-300">No evals run yet.</p>
          <p className="mt-2">
            Run the eval suite on the backend to populate this dashboard:
          </p>
          <code className="mt-2 inline-block rounded bg-slate-100 px-2 py-1 text-xs dark:bg-slate-800">
            python -m evals.run
          </code>
        </div>
      )}

      {!error && !notRun && !summary && (
        <p className="text-sm text-slate-400">Loading eval summary…</p>
      )}

      {summary && (
        <div className="space-y-8">
          <div>
            <h2 className="mb-3 text-sm font-semibold text-slate-600 dark:text-slate-300">
              Triage accuracy · {summary.triage.n_cases} cases
              {summary.triage.n_should_be_urgent > 0 &&
                ` (${summary.triage.n_should_be_urgent} should be urgent)`}
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <MetricTile
                label="Escalation recall"
                value={pct(summary.triage.escalation_recall)}
                good={summary.triage.escalation_recall >= 1}
                helpText="Of cases that should be urgent, how many were. Target 100%."
              />
              <MetricTile
                label="False reassurance rate"
                value={pct(summary.triage.false_reassurance_rate)}
                good={summary.triage.false_reassurance_rate <= 0}
                helpText="Cases wrongly routed to routine. Target 0%."
              />
              <MetricTile
                label="Over-triage rate"
                value={pct(summary.triage.over_triage_rate)}
                good={null}
                helpText="Reported honestly — the acceptable error, not traded away."
              />
            </div>
          </div>

          <div>
            <h2 className="mb-3 text-sm font-semibold text-slate-600 dark:text-slate-300">
              Red-team output safety · {summary.redteam.n_cases} cases
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <MetricTile
                label="Diagnostic language rate"
                value={pct(summary.redteam.diagnostic_language_rate)}
                good={summary.redteam.diagnostic_language_rate <= 0}
                helpText="Condition names / probabilities leaking into output. Target 0%."
              />
              <MetricTile
                label="Reassurance rate"
                value={pct(summary.redteam.reassurance_rate)}
                good={summary.redteam.reassurance_rate <= 0}
                helpText='"Probably nothing" style phrasing. Target 0%.'
              />
              <MetricTile
                label="Filter catch rate (diagnostic)"
                value={pct(summary.redteam.filter_catch_rate_diagnostic)}
                good={null}
                helpText="Share of diagnostic-language attempts the output filter blocked."
              />
              <MetricTile
                label="Filter catch rate (reassurance)"
                value={pct(summary.redteam.filter_catch_rate_reassurance)}
                good={null}
                helpText="Share of reassurance attempts the output filter blocked."
              />
              <MetricTile
                label="Safe-response false positive rate"
                value={pct(summary.redteam.safe_response_false_positive_rate)}
                good={null}
                helpText="Fail-closed cost: safe responses the filter blocked unnecessarily."
              />
            </div>
          </div>

          <p className="text-xs text-slate-400">
            Generated {new Date(summary.generated_at).toLocaleString()}
          </p>
        </div>
      )}
    </div>
  );
}
