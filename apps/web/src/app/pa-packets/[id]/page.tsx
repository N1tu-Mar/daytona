"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ApiError, get, post } from "@/lib/api";
import type { PaPacket } from "@/lib/types";

export default function PaPacketDetailPage() {
  const params = useParams<{ id: string }>();
  const packetId = params.id;
  const [packet, setPacket] = useState<PaPacket | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actor, setActor] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    get<PaPacket>(`/pa-packets/${packetId}`)
      .then((data) => {
        if (!cancelled) setPacket(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError && err.status === 404
              ? "Packet not found."
              : "Could not load this packet."
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [packetId]);

  async function handleApprove() {
    if (!actor.trim()) {
      setActionError("Enter the approving physician's name before approving.");
      return;
    }
    setBusy(true);
    setActionError(null);
    try {
      const res = await post<{ status: string; approval_hash: string }>(
        `/pa-packets/${packetId}/approve`,
        { actor: actor.trim() }
      );
      setPacket((prev) =>
        prev
          ? {
              ...prev,
              status: "approved",
              approved_by: actor.trim(),
              approved_at: new Date().toISOString(),
              approval_hash: res.approval_hash,
            }
          : prev
      );
    } catch (err) {
      setActionError(
        err instanceof ApiError && err.status === 409
          ? "This packet is already approved or not yet drafted."
          : err instanceof Error
          ? err.message
          : "Approval failed."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmit() {
    setBusy(true);
    setActionError(null);
    try {
      await post(`/pa-packets/${packetId}/submit`, {});
      setPacket((prev) => (prev ? { ...prev, status: "submitted" } : prev));
    } catch (err) {
      setActionError(
        err instanceof ApiError && err.status === 409
          ? "Packet must be physician-approved before submission."
          : err instanceof Error
          ? err.message
          : "Submission failed."
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <Link href="/pa-packets" className="text-sm text-slate-500 hover:underline">
        ← Back to PA packets
      </Link>

      {error && (
        <p className="mt-4 rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          {error}
        </p>
      )}

      {!error && !packet && <p className="mt-4 text-sm text-slate-400">Loading…</p>}

      {packet && (
        <div className="mt-4 space-y-6">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Packet {packet.id}</h1>
            <p className="mt-1 text-sm text-slate-500">
              referral {packet.referral_id} · verdict {packet.verdict_id} · status{" "}
              <span className="font-medium">{packet.status}</span>
            </p>
          </div>

          <div>
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Sentences
            </h2>
            {packet.sentences.length === 0 ? (
              <p className="text-sm text-slate-400">No sentences drafted yet.</p>
            ) : (
              <ul className="space-y-2">
                {packet.sentences.map((s, i) => (
                  <li
                    key={i}
                    className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm dark:border-slate-800 dark:bg-slate-900"
                  >
                    <p className="text-slate-800 dark:text-slate-200">{s.text}</p>
                    <p className="mt-1 text-xs text-slate-400">source: {s.source_ref}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {(packet.payer_status || packet.days_saved !== null) && (
            <div className="flex gap-6 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm dark:border-slate-800 dark:bg-slate-900">
              {packet.payer_status && (
                <div>
                  <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Payer status
                  </span>
                  <p>{packet.payer_status}</p>
                </div>
              )}
              {packet.days_saved !== null && (
                <div>
                  <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Days saved
                  </span>
                  <p>{packet.days_saved}</p>
                </div>
              )}
            </div>
          )}

          <div className="rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
            {packet.approved_by ? (
              <div className="rounded-md bg-emerald-50 px-4 py-3 text-sm dark:bg-emerald-950">
                <p className="font-semibold text-emerald-800 dark:text-emerald-300">
                  Approved by {packet.approved_by}
                </p>
                <p className="mt-1 text-emerald-900 dark:text-emerald-200">
                  {packet.approved_at ? new Date(packet.approved_at).toLocaleString() : ""}
                </p>
                {packet.approval_hash && (
                  <p className="mt-1 break-all font-mono text-xs text-emerald-900 dark:text-emerald-200">
                    {packet.approval_hash}
                  </p>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Approving physician (required)
                </label>
                <input
                  type="text"
                  value={actor}
                  onChange={(e) => setActor(e.target.value)}
                  placeholder="Full name"
                  className="w-full max-w-sm rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
                />
              </div>
            )}

            {actionError && (
              <p className="mt-3 text-sm text-red-600 dark:text-red-400">{actionError}</p>
            )}

            <div className="mt-4 flex gap-2">
              {!packet.approved_by && (
                <button
                  onClick={handleApprove}
                  disabled={busy || !actor.trim()}
                  className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {busy ? "Approving…" : "Approve"}
                </button>
              )}
              <button
                onClick={handleSubmit}
                disabled={busy || !packet.approved_by || packet.status === "submitted"}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {packet.status === "submitted" ? "Submitted" : busy ? "Submitting…" : "Submit"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
