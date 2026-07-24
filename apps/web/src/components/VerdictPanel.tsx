"use client";

import { useState } from "react";
import { ApiError, post } from "@/lib/api";
import { RULE_EVIDENCE, RULE_RATIONALE } from "@/lib/ruleRationale";
import type { ApproveResponse, TriageVerdict } from "@/lib/types";
import { DispositionBadge, UrgencyBadge } from "@/components/badges";

const MISSING_FEATURE_LABELS: Record<string, string> = {
  age: "age",
  rectal_bleeding: "rectal bleeding",
  fit_result: "FIT result",
  iron_deficiency_anemia: "iron deficiency anemia",
  change_in_bowel_habit: "change in bowel habit",
  unintentional_weight_loss: "unintentional weight loss",
  abdominal_pain: "abdominal pain",
  abdominal_or_rectal_mass: "abdominal or rectal mass",
  family_history_crc: "family history of colorectal cancer",
};

export default function VerdictPanel({
  referralId,
  verdict,
  onUpdated,
}: {
  referralId: string;
  verdict: TriageVerdict;
  onUpdated: (v: TriageVerdict) => void;
}) {
  const alreadyApproved = Boolean(verdict.approved_by);

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex flex-wrap items-center gap-3">
        <UrgencyBadge urgency={verdict.urgency} />
        <DispositionBadge disposition={verdict.disposition} />
        <span className="text-xs text-slate-400">rule set {verdict.rule_version}</span>
      </div>

      <div className="mt-4">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Rules fired
        </h3>
        {verdict.rules_fired.length === 0 ? (
          <p className="mt-1 text-sm text-slate-400">No rules fired.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {verdict.rules_fired.map((ruleId) => (
              <li
                key={ruleId}
                className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm dark:border-slate-800 dark:bg-slate-950"
              >
                <code className="font-mono text-xs font-semibold text-slate-700 dark:text-slate-300">
                  {ruleId}
                </code>
                {RULE_RATIONALE[ruleId] && (
                  <p className="mt-1 text-slate-600 dark:text-slate-400">{RULE_RATIONALE[ruleId]}</p>
                )}
                {RULE_EVIDENCE[ruleId] && (
                  <p className="mt-1.5 text-xs text-slate-500">
                    <span className="font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-400">
                      Evidence:
                    </span>{" "}
                    {RULE_EVIDENCE[ruleId].finding}{" "}
                    <a
                      href={RULE_EVIDENCE[ruleId].url}
                      target="_blank"
                      rel="noreferrer"
                      className="underline decoration-slate-300 underline-offset-2 hover:text-slate-700 dark:hover:text-slate-300"
                    >
                      {RULE_EVIDENCE[ruleId].source}
                    </a>
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {verdict.missing_features.length > 0 && (
        <div className="mt-4 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 dark:border-amber-800 dark:bg-amber-950">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-amber-800 dark:text-amber-300">
            Missing features
          </h3>
          <p className="mt-1 text-sm text-amber-900 dark:text-amber-200">
            {verdict.missing_features
              .map((f) => MISSING_FEATURE_LABELS[f] || f)
              .join(", ")}{" "}
            — not extracted from the source document. Confirm before approving.
          </p>
        </div>
      )}

      <div className="mt-5 border-t border-slate-200 pt-4 dark:border-slate-800">
        {alreadyApproved ? (
          <ApprovedSummary verdict={verdict} />
        ) : (
          <ApproveEscalateForms
            referralId={referralId}
            verdict={verdict}
            onUpdated={onUpdated}
          />
        )}
      </div>
    </section>
  );
}

function ApprovedSummary({ verdict }: { verdict: TriageVerdict }) {
  return (
    <div className="rounded-md bg-emerald-50 px-4 py-3 text-sm dark:bg-emerald-950">
      <p className="font-semibold text-emerald-800 dark:text-emerald-300">
        Approved — booking confirmed
      </p>
      <dl className="mt-2 grid grid-cols-1 gap-x-6 gap-y-1 text-emerald-900 dark:text-emerald-200 sm:grid-cols-2">
        <div>
          <dt className="text-xs uppercase tracking-wide text-emerald-700 dark:text-emerald-400">
            Approved by
          </dt>
          <dd>{verdict.approved_by}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-emerald-700 dark:text-emerald-400">
            Approved at
          </dt>
          <dd>{verdict.approved_at ? new Date(verdict.approved_at).toLocaleString() : "—"}</dd>
        </div>
        {verdict.booked_slot && (
          <div>
            <dt className="text-xs uppercase tracking-wide text-emerald-700 dark:text-emerald-400">
              Booked slot
            </dt>
            <dd>{verdict.booked_slot}</dd>
          </div>
        )}
        <div className="sm:col-span-2">
          <dt className="text-xs uppercase tracking-wide text-emerald-700 dark:text-emerald-400">
            Approval hash
          </dt>
          <dd className="break-all font-mono text-xs">{verdict.approval_hash}</dd>
        </div>
      </dl>
    </div>
  );
}

function ApproveEscalateForms({
  referralId,
  verdict,
  onUpdated,
}: {
  referralId: string;
  verdict: TriageVerdict;
  onUpdated: (v: TriageVerdict) => void;
}) {
  const [mode, setMode] = useState<"approve" | "escalate" | null>(null);
  const [actor, setActor] = useState("");
  const [slot, setSlot] = useState("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submitApprove(e: React.FormEvent) {
    e.preventDefault();
    if (!actor.trim()) {
      setError("Enter the approving nurse's name before approving.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const res = await post<ApproveResponse>(
        `/referrals/${referralId}/verdicts/${verdict.id}/approve`,
        { actor: actor.trim(), slot: slot.trim() || undefined }
      );
      onUpdated({
        ...verdict,
        approved_by: actor.trim(),
        approved_at: res.approved_at,
        approval_hash: res.approval_hash,
        booked_slot: slot.trim() || verdict.booked_slot,
      });
      setMode(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("This verdict was already approved (by someone else, just now). Reload to see it.");
      } else {
        setError(err instanceof Error ? err.message : "Approval failed.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function submitEscalate(e: React.FormEvent) {
    e.preventDefault();
    if (!actor.trim()) {
      setError("Enter your name before escalating.");
      return;
    }
    if (!reason.trim()) {
      setError("A reason is required to escalate.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await post(`/referrals/${referralId}/verdicts/${verdict.id}/escalate`, {
        actor: actor.trim(),
        reason: reason.trim(),
      });
      setMode(null);
      setReason("");
      alert("Sent back for human review.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Escalation failed.");
    } finally {
      setSubmitting(false);
    }
  }

  if (mode === null) {
    return (
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setMode("approve")}
          className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
        >
          Approve
        </button>
        <button
          onClick={() => setMode("escalate")}
          className="rounded-md border border-amber-400 px-4 py-2 text-sm font-semibold text-amber-700 hover:bg-amber-50 dark:text-amber-300 dark:hover:bg-amber-950"
        >
          Escalate
        </button>
      </div>
    );
  }

  if (mode === "approve") {
    return (
      <form onSubmit={submitApprove} className="space-y-3">
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
            Approving nurse (required)
          </label>
          <input
            type="text"
            required
            value={actor}
            onChange={(e) => setActor(e.target.value)}
            placeholder="Full name"
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
            Slot (optional)
          </label>
          <input
            type="text"
            value={slot}
            onChange={(e) => setSlot(e.target.value)}
            placeholder="e.g. 2026-07-28T09:00 urgent clinic"
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
          />
        </div>
        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={submitting || !actor.trim()}
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? "Approving…" : "Confirm approval"}
          </button>
          <button
            type="button"
            onClick={() => {
              setMode(null);
              setError(null);
            }}
            className="rounded-md px-4 py-2 text-sm font-medium text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            Cancel
          </button>
        </div>
      </form>
    );
  }

  return (
    <form onSubmit={submitEscalate} className="space-y-3">
      <div>
        <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
          Your name (required)
        </label>
        <input
          type="text"
          required
          value={actor}
          onChange={(e) => setActor(e.target.value)}
          placeholder="Full name"
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
        />
      </div>
      <div>
        <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
          Reason (required)
        </label>
        <textarea
          required
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={3}
          placeholder="Why does this need another look?"
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
        />
      </div>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting || !actor.trim() || !reason.trim()}
          className="rounded-md bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? "Sending…" : "Send back for review"}
        </button>
        <button
          type="button"
          onClick={() => {
            setMode(null);
            setError(null);
          }}
          className="rounded-md px-4 py-2 text-sm font-medium text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
