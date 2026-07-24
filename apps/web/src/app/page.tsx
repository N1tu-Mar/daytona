import Image from "next/image";
import Link from "next/link";

// Landing page. Server-rendered, no client JS — the product pages carry the
// interactivity; this page carries the argument. Copy rules: short
// sentences, numbers over adjectives, and no claim that isn't enforced in
// code somewhere in this repo.

const PROBLEM_STATS = [
  {
    value: "91% vs 15%",
    label: "five-year survival for colorectal cancer caught early vs late",
  },
  {
    value: "3 in 4",
    label: "cases in under-50s are caught at an advanced stage",
  },
  {
    value: "98.5%",
    label: "of pediatric oncology prior auths get approved anyway — the harm is the delay",
  },
];

const STEPS = [
  {
    title: "A patient calls, or a fax arrives",
    body: "The voice line asks eleven fixed questions. The fax is opened inside an isolated, network-blocked Daytona sandbox that is destroyed seconds later — untrusted documents never touch our process.",
  },
  {
    title: "A model reads. It never decides.",
    body: "Fireworks extracts structured facts: age, bleeding, duration, weight loss. Perception only. If extraction is uncertain, the case goes to a human — the model cannot lower a priority or clear a patient.",
  },
  {
    title: "Versioned rules set the urgency",
    body: "A plain config file of clinical red-flag rules — auditable in five minutes, unit-tested, zero model calls. Every verdict records exactly which rules fired and which version decided.",
  },
  {
    title: "A person signs everything",
    body: "A nurse approves every booking. A physician approves every prior-auth packet, then the agent dials the payer's phone tree and brings back the status. The agent prepares; humans commit.",
  },
];

const SAFEGUARDS = [
  "Urgency is monotonic — the system can raise it, never lower it. Property-tested.",
  "No code path auto-clears a patient. Every failure routes to a human.",
  "The voice cannot say a condition name. The output filter runs inside the speech synthesizer, fail-closed.",
  "Nothing books without a named human's signature — recorded with a hash of what they approved.",
  "A prior-auth sentence with no source does not render.",
];

const SPONSORS = [
  {
    name: "Daytona",
    job: "Every scanned referral is parsed in an ephemeral, zero-egress sandbox, then the sandbox is destroyed. It's the blast door: fax and PDF toolchains are a classic attack surface, and here they never run in-process. The worklist badges each item with its sandbox ID as proof.",
  },
  {
    name: "Fireworks AI",
    job: "Structured extraction of clinical facts from messy text — perception, never judgment. The model was picked by a measured A/B (verdict-preservation, hallucination rate, latency), not by default. Extraction runs in about a second.",
  },
  {
    name: "Braintrust",
    job: "Every live decision streams a full trace: sandbox → extraction → rules. Experiments score the rule engine (escalation recall 100%, false reassurance 0) and diff the extraction models — the model choice ships with its receipt.",
  },
  {
    name: "ElevenLabs",
    job: "Both phone legs of the product: the patient intake call and the payer IVR call, audible end to end. Every agent line passes the no-diagnosis filter before it reaches the synthesizer.",
  },
];

const SHOTS = [
  {
    src: "/landing/intake-call.png",
    alt: "The intake call: red flags elicited, urgent slot booked in the same call",
    caption:
      "The call books the appointment. A 42-year-old reports three weeks of bleeding — urgent slot, same call, and the transcript plays out loud.",
  },
  {
    src: "/landing/worklist.png",
    alt: "Nurse worklist with urgency verdicts, fired rules, and sandbox provenance",
    caption:
      "The nurse worklist. Every verdict shows which rules fired; anything the pipeline couldn't assess says so honestly and waits for a human.",
  },
  {
    src: "/landing/dashboard.png",
    alt: "Safety evals dashboard: escalation recall 100%, false reassurance 0",
    caption:
      "The numbers we run on: escalation recall 100%, false reassurance 0 — and over-triage reported honestly, because that's the error we chose.",
  },
];

export default function Home() {
  return (
    <div className="space-y-20 pb-10">
      {/* Hero */}
      <section className="-mx-4 rounded-2xl bg-slate-950 px-6 py-16 text-white sm:mx-0 sm:px-12 dark:border dark:border-slate-800">
        <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
          Meridian — referral triage, not diagnosis
        </p>
        <h1 className="mt-4 max-w-3xl text-4xl font-bold tracking-tight sm:text-5xl">
          A 42-year-old with rectal bleeding gets told it&apos;s probably
          hemorrhoids.
        </h1>
        <p className="mt-5 max-w-2xl text-lg leading-relaxed text-slate-300">
          Meridian is the agent that makes that miss impossible. It answers one
          question — <em>does this person need a GI appointment, and how fast</em> —
          books the slot, drafts the prior auth, and chases the payer. It never
          diagnoses anyone. That&apos;s not a disclaimer; it&apos;s the architecture.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/intake"
            className="rounded-md bg-white px-5 py-2.5 text-sm font-semibold text-slate-900 hover:bg-slate-200"
          >
            Hear a live call
          </Link>
          <Link
            href="/worklist"
            className="rounded-md border border-slate-600 px-5 py-2.5 text-sm font-semibold text-slate-200 hover:bg-slate-800"
          >
            See the worklist
          </Link>
        </div>
      </section>

      {/* Problem */}
      <section>
        <h2 className="text-2xl font-bold tracking-tight">
          The failure isn&apos;t medicine. It&apos;s routing.
        </h2>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          Early-onset colorectal cancer has risen every year for a decade, and
          the most common miss is mundane: a young patient&apos;s bleeding gets
          written off, the referral sits in a fax queue, the prior auth adds
          weeks. Nine in ten physicians say prior authorization delays care.
          None of that needs a smarter doctor — it needs the right people to
          get scoped, in the right order, faster.
        </p>
        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          {PROBLEM_STATS.map((s) => (
            <div
              key={s.value}
              className="rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
            >
              <p className="text-3xl font-bold tracking-tight">{s.value}</p>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section>
        <h2 className="text-2xl font-bold tracking-tight">
          Models read. Rules decide. People sign.
        </h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {STEPS.map((step, i) => (
            <div
              key={step.title}
              className="rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
            >
              <p className="font-mono text-xs text-slate-400">0{i + 1}</p>
              <h3 className="mt-2 font-semibold">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                {step.body}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Screenshots */}
      <section className="space-y-10">
        <h2 className="text-2xl font-bold tracking-tight">The working system</h2>
        {SHOTS.map((shot) => (
          <figure key={shot.src}>
            <div className="overflow-hidden rounded-xl border border-slate-200 shadow-sm dark:border-slate-800">
              <Image
                src={shot.src}
                alt={shot.alt}
                width={1440}
                height={900}
                className="w-full"
              />
            </div>
            <figcaption className="mt-3 max-w-3xl text-sm text-slate-500">
              {shot.caption}
            </figcaption>
          </figure>
        ))}
      </section>

      {/* Safeguards */}
      <section className="-mx-4 rounded-2xl bg-slate-950 px-6 py-12 text-white sm:mx-0 sm:px-12 dark:border dark:border-slate-800">
        <h2 className="text-2xl font-bold tracking-tight">
          Safeguards that are code, not promises
        </h2>
        <p className="mt-2 text-sm text-slate-400">
          Each of these is enforced by the type system, a filter, or a test that
          fails the build — not by a prompt.
        </p>
        <ul className="mt-6 space-y-3">
          {SAFEGUARDS.map((s) => (
            <li key={s} className="flex gap-3 text-sm leading-relaxed text-slate-200">
              <span className="mt-0.5 select-none text-emerald-400">—</span>
              {s}
            </li>
          ))}
        </ul>
      </section>

      {/* Sponsors / stack */}
      <section>
        <h2 className="text-2xl font-bold tracking-tight">
          Four tools, each load-bearing
        </h2>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          Nothing here is a logo on a slide. Remove any one of these and a
          specific, demonstrable capability disappears.
        </p>
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {SPONSORS.map((sp) => (
            <div
              key={sp.name}
              className="rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
            >
              <h3 className="font-semibold">{sp.name}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                {sp.job}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Close */}
      <section className="text-center">
        <h2 className="text-2xl font-bold tracking-tight">
          We don&apos;t diagnose. We make sure the right people get scoped.
        </h2>
        <div className="mt-6 flex justify-center gap-3">
          <Link
            href="/intake"
            className="rounded-md bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-700 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-200"
          >
            Try the demo
          </Link>
          <Link
            href="/dashboard"
            className="rounded-md border border-slate-300 px-5 py-2.5 text-sm font-semibold hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
          >
            See the evals
          </Link>
        </div>
      </section>
    </div>
  );
}
