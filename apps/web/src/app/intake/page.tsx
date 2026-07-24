"use client";

// Patient intake line — demo path step 1. Simulates the phone call the
// ElevenLabs voice line handles in production: the fixed-order red-flag
// script runs against the answers below, the rule engine sets urgency, and
// a slot is booked in the same call. The transcript comes back voiced
// (agent and patient in distinct voices) and plays like a real call.
//
// Prefilled with THE demo case: the 42-year-old with rectal bleeding whose
// referral says "probable hemorrhoids". Every answer is editable so judges
// can change one answer live and watch the verdict change deterministically.

import { useState } from "react";
import { post } from "@/lib/api";
import type { IntakeCallResponse } from "@/lib/types";
import CallPlayback from "@/components/CallPlayback";
import { UrgencyBadge } from "@/components/badges";

// Mirrors services/intake/questions.py QUESTION_SCRIPT (wire shape, on
// purpose — drift is easy to spot in review).
const QUESTIONS: { field: string; prompt: string }[] = [
  { field: "age", prompt: "Can you tell me your age?" },
  { field: "rectal_bleeding", prompt: "Have you noticed any rectal bleeding?" },
  { field: "bleeding_duration_weeks", prompt: "About how many weeks has that been going on?" },
  {
    field: "change_in_bowel_habit",
    prompt: "Have you had any change in your bowel habits, like new diarrhea or constipation?",
  },
  { field: "bowel_habit_duration_weeks", prompt: "About how many weeks has that been going on?" },
  { field: "unintentional_weight_loss", prompt: "Have you lost weight recently without trying to?" },
  { field: "abdominal_pain", prompt: "Have you had any abdominal pain?" },
  {
    field: "iron_deficiency_anemia",
    prompt: "Has a doctor told you that you have iron deficiency anemia, or low iron?",
  },
  {
    field: "fit_result",
    prompt: "Have you had a FIT or fecal occult blood test, and if so was it positive or negative?",
  },
  {
    field: "family_history_crc",
    prompt: "Does anyone in your immediate family have a history of colorectal cancer?",
  },
  {
    field: "abdominal_or_rectal_mass",
    prompt: "Has a doctor ever felt a lump or mass in your abdomen or during a rectal exam?",
  },
];

const DEMO_ANSWERS: Record<string, string> = {
  age: "I'm 42",
  rectal_bleeding: "yes",
  bleeding_duration_weeks: "about 3 weeks",
  change_in_bowel_habit: "yes",
  bowel_habit_duration_weeks: "3 weeks",
  unintentional_weight_loss: "no",
  abdominal_pain: "no",
  iron_deficiency_anemia: "no",
  fit_result: "haven't had one",
  family_history_crc: "none that I know of",
  abdominal_or_rectal_mass: "no",
};

export default function IntakePage() {
  const [patientName, setPatientName] = useState("Alex Rivera");
  const [answers, setAnswers] = useState<Record<string, string>>(DEMO_ANSWERS);
  const [result, setResult] = useState<IntakeCallResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function placeCall() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await post<IntakeCallResponse>("/intake/call", {
        patient_answers: answers,
        patient_name: patientName,
        voice: true,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Call failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Patient intake line</h1>
      <p className="mt-1 max-w-3xl text-sm text-slate-500">
        The fixed-order red-flag script, exactly as the voice line runs it: answers are
        parsed deterministically, the rule engine sets urgency, and a slot is booked in
        the same call. The agent never states a condition — every spoken line passes the
        output filter before it reaches the synthesizer.
      </p>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Caller&apos;s answers (editable)
          </h2>
          <label className="block text-xs font-medium text-slate-500">Patient name</label>
          <input
            type="text"
            value={patientName}
            onChange={(e) => setPatientName(e.target.value)}
            className="mt-1 mb-4 w-full max-w-sm rounded-md border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-950"
          />
          <div className="space-y-3">
            {QUESTIONS.map((q) => (
              <div key={q.field}>
                <label className="block text-xs text-slate-500">{q.prompt}</label>
                <input
                  type="text"
                  value={answers[q.field] ?? ""}
                  onChange={(e) => setAnswers((prev) => ({ ...prev, [q.field]: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-950"
                />
              </div>
            ))}
          </div>
          <button
            onClick={placeCall}
            disabled={busy}
            className="mt-5 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? "On the call…" : "📞 Place call"}
          </button>
          {error && <p className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p>}
        </div>

        <div className="space-y-4">
          {result && (
            <>
              <div className="rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Call outcome
                </h2>
                <div className="flex flex-wrap items-center gap-3 text-sm">
                  <UrgencyBadge urgency={result.urgency} />
                  <span className="text-slate-300 dark:text-slate-600">·</span>
                  <span className="font-medium">{result.disposition}</span>
                </div>
                {result.booked_slot ? (
                  <p className="mt-3 rounded-md bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                    Booked: {result.booked_slot}
                  </p>
                ) : (
                  <p className="mt-3 rounded-md bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                    Routed to a nurse callback — no booking without a clear, complete picture.
                  </p>
                )}
                <p className="mt-2 text-xs text-slate-400">
                  referral {result.referral_id} — now on the{" "}
                  <a href="/worklist" className="underline">
                    nurse worklist
                  </a>{" "}
                  for sign-off
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  The call
                </h2>
                <CallPlayback turns={result.transcript} />
              </div>
            </>
          )}
          {!result && (
            <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-400 dark:border-slate-700">
              Place the call to hear the intake line run the script and book a slot.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
