import Image from "next/image";
import Link from "next/link";
import { Newsreader } from "next/font/google";
import DemoBanner from "@/components/DemoBanner";

// Landing page. Server-rendered, no client JS — the product pages carry the
// interactivity; this page carries the argument. Its own full-bleed dark
// editorial layout (the light app shell lives in (app)/layout.tsx). Copy
// rules: short sentences, numbers over adjectives, and no claim that isn't
// enforced in code somewhere in this repo.

const newsreader = Newsreader({
  subsets: ["latin"],
  style: ["normal", "italic"],
  weight: ["400", "500"],
  variable: "--font-newsreader",
});

const NAV_LINKS = [
  { href: "/intake", label: "Intake Line" },
  { href: "/worklist", label: "Worklist" },
  { href: "/pa-packets", label: "PA Packets" },
  { href: "/dashboard", label: "Dashboard" },
];

const PROBLEM_STATS = [
  {
    value: "91% → 15%",
    label: "five-year survival for colorectal cancer, caught early versus late",
  },
  {
    value: "3 in 4",
    label: "cases in under-50s are found at an advanced stage",
  },
  {
    value: "98.5%",
    label: "of pediatric oncology prior auths are approved anyway — the harm is the delay",
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
    job: "Structured extraction of clinical facts from messy text — perception, never judgment. The model was picked by a measured A/B (verdict preservation, hallucination rate, latency), not by default. Extraction runs in about a second.",
  },
  {
    name: "Braintrust",
    job: "Every live decision streams a full trace: sandbox → extraction → rules. Experiments score the rule engine — escalation recall 100%, false reassurance 0 — and diff the extraction models, so the model choice ships with its receipt.",
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
      "The call books the appointment — a 42-year-old reports three weeks of bleeding; urgent slot, same call, transcript plays out loud.",
  },
  {
    src: "/landing/worklist.png",
    alt: "Nurse worklist with urgency verdicts, fired rules, and sandbox provenance",
    caption:
      "The nurse worklist — every verdict shows which rules fired; anything the pipeline couldn't assess says so honestly and waits for a human.",
  },
  {
    src: "/landing/dashboard.png",
    alt: "Safety evals dashboard: escalation recall 100%, false reassurance 0",
    caption:
      "Escalation recall 100%, false reassurance 0 — and over-triage reported honestly, because that's the error we chose.",
  },
];

function Kicker({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-mono text-[11px] font-medium uppercase tracking-[0.25em] text-slate-500">
      {children}
    </p>
  );
}

export default function Home() {
  return (
    <div
      className={`${newsreader.variable} min-h-screen bg-[#070c18] text-slate-300 selection:bg-amber-200 selection:text-slate-900`}
    >
      <DemoBanner />

      {/* Nav */}
      <header className="border-b border-white/10">
        <nav className="mx-auto flex max-w-5xl items-center justify-between px-6 py-5">
          <span className="font-[family-name:var(--font-newsreader)] text-xl text-white">
            Meridian
          </span>
          <div className="flex items-center gap-6">
            {NAV_LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="text-sm text-slate-400 transition-colors hover:text-white"
              >
                {l.label}
              </Link>
            ))}
          </div>
        </nav>
      </header>

      <main className="mx-auto max-w-5xl px-6">
        {/* Hero */}
        <section className="py-24 sm:py-32">
          <Kicker>Referral triage, not diagnosis</Kicker>
          <h1 className="mt-8 font-[family-name:var(--font-newsreader)] text-5xl font-normal leading-[1.08] tracking-tight text-white sm:text-6xl">
            A 42-year-old with rectal bleeding is told it&apos;s{" "}
            <em className="text-amber-200/90">probably hemorrhoids.</em>
          </h1>
          <p className="mt-8 max-w-2xl text-lg font-light leading-relaxed text-slate-400">
            Meridian is the agent that makes that miss impossible. It answers
            one question — does this person need a GI appointment, and how
            fast — books the slot, drafts the prior auth, and chases the
            payer. It never diagnoses anyone. That&apos;s not a disclaimer;
            it&apos;s the architecture.
          </p>
          <div className="mt-10 flex flex-wrap items-center gap-6">
            <Link
              href="/intake"
              className="rounded-full bg-white px-6 py-3 text-sm font-medium text-slate-900 transition-colors hover:bg-amber-100"
            >
              Hear a live call
            </Link>
            <Link
              href="/worklist"
              className="text-sm text-slate-400 transition-colors hover:text-white"
            >
              See the worklist <span aria-hidden>→</span>
            </Link>
          </div>
        </section>

        {/* Problem */}
        <section className="border-t border-white/10 py-20">
          <Kicker>The problem</Kicker>
          <h2 className="mt-6 max-w-2xl font-[family-name:var(--font-newsreader)] text-3xl leading-snug text-white sm:text-4xl">
            The failure isn&apos;t medicine. <em>It&apos;s routing.</em>
          </h2>
          <p className="mt-6 max-w-2xl leading-relaxed text-slate-400">
            Early-onset colorectal cancer has risen every year for a decade,
            and the most common miss is mundane: a young patient&apos;s
            bleeding gets written off, the referral sits in a fax queue, the
            prior auth adds weeks. Nine in ten physicians say prior
            authorization delays care. None of that needs a smarter doctor —
            it needs the right people to get scoped, in the right order,
            faster.
          </p>
          <dl className="mt-14 grid gap-px overflow-hidden rounded-lg bg-white/10 sm:grid-cols-3">
            {PROBLEM_STATS.map((s) => (
              <div key={s.value} className="bg-[#070c18] p-8 sm:bg-[#0a1020]/60">
                <dt className="sr-only">{s.label}</dt>
                <dd className="font-[family-name:var(--font-newsreader)] text-4xl text-white">
                  {s.value}
                </dd>
                <p className="mt-3 text-sm leading-relaxed text-slate-500">{s.label}</p>
              </div>
            ))}
          </dl>
        </section>

        {/* How it works */}
        <section className="border-t border-white/10 py-20">
          <Kicker>How it works</Kicker>
          <h2 className="mt-6 font-[family-name:var(--font-newsreader)] text-3xl leading-snug text-white sm:text-4xl">
            Models read. Rules decide. <em>People sign.</em>
          </h2>
          <ol className="mt-14">
            {STEPS.map((step, i) => (
              <li
                key={step.title}
                className="grid gap-4 border-t border-white/10 py-8 first:border-t-0 sm:grid-cols-[6rem_16rem_1fr] sm:gap-8"
              >
                <span className="font-mono text-sm text-amber-200/60">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <h3 className="font-[family-name:var(--font-newsreader)] text-xl text-white">
                  {step.title}
                </h3>
                <p className="text-sm leading-relaxed text-slate-400">{step.body}</p>
              </li>
            ))}
          </ol>
        </section>

        {/* Screenshots */}
        <section className="border-t border-white/10 py-20">
          <Kicker>The working system</Kicker>
          <div className="mt-14 space-y-20">
            {SHOTS.map((shot) => (
              <figure key={shot.src}>
                <div className="overflow-hidden rounded-xl border border-white/10 bg-white/5 p-1.5 shadow-2xl shadow-black/50">
                  <div className="overflow-hidden rounded-lg">
                    <Image src={shot.src} alt={shot.alt} width={1440} height={900} className="w-full" />
                  </div>
                </div>
                <figcaption className="mx-auto mt-5 max-w-2xl text-center font-mono text-xs leading-relaxed text-slate-500">
                  {shot.caption}
                </figcaption>
              </figure>
            ))}
          </div>
        </section>

        {/* Safeguards */}
        <section className="border-t border-white/10 py-20">
          <Kicker>Safeguards</Kicker>
          <h2 className="mt-6 font-[family-name:var(--font-newsreader)] text-3xl leading-snug text-white sm:text-4xl">
            Code, <em>not promises.</em>
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-relaxed text-slate-500">
            Each of these is enforced by the type system, a filter, or a test
            that fails the build — not by a prompt.
          </p>
          <ul className="mt-12">
            {SAFEGUARDS.map((s, i) => (
              <li
                key={s}
                className="flex gap-6 border-t border-white/10 py-5 first:border-t-0"
              >
                <span className="font-mono text-sm text-amber-200/60">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <p className="leading-relaxed text-slate-300">{s}</p>
              </li>
            ))}
          </ul>
        </section>

        {/* Stack */}
        <section className="border-t border-white/10 py-20">
          <Kicker>The stack</Kicker>
          <h2 className="mt-6 font-[family-name:var(--font-newsreader)] text-3xl leading-snug text-white sm:text-4xl">
            Four tools, <em>each load-bearing.</em>
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-relaxed text-slate-500">
            Nothing here is a logo on a slide. Remove any one of these and a
            specific, demonstrable capability disappears.
          </p>
          <dl className="mt-12">
            {SPONSORS.map((sp) => (
              <div
                key={sp.name}
                className="grid gap-3 border-t border-white/10 py-8 first:border-t-0 sm:grid-cols-[14rem_1fr] sm:gap-8"
              >
                <dt className="font-[family-name:var(--font-newsreader)] text-xl text-white">
                  {sp.name}
                </dt>
                <dd className="text-sm leading-relaxed text-slate-400">{sp.job}</dd>
              </div>
            ))}
          </dl>
        </section>

        {/* Close */}
        <section className="border-t border-white/10 py-24 text-center sm:py-32">
          <p className="mx-auto max-w-3xl font-[family-name:var(--font-newsreader)] text-3xl leading-snug text-white sm:text-4xl">
            We don&apos;t diagnose. We make sure the right people{" "}
            <em className="text-amber-200/90">get scoped.</em>
          </p>
          <div className="mt-10 flex justify-center gap-6">
            <Link
              href="/intake"
              className="rounded-full bg-white px-6 py-3 text-sm font-medium text-slate-900 transition-colors hover:bg-amber-100"
            >
              Try the demo
            </Link>
            <Link
              href="/dashboard"
              className="rounded-full border border-white/20 px-6 py-3 text-sm font-medium text-slate-300 transition-colors hover:border-white/40 hover:text-white"
            >
              See the evals
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-white/10">
        <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-2 px-6 py-8 font-mono text-[11px] tracking-wide text-slate-600 sm:flex-row">
          <span>MERIDIAN — DEMO. SYNTHETIC DATA. NOT FOR CLINICAL USE.</span>
          <span>LLMS EXTRACT · RULES DECIDE · HUMANS SIGN</span>
        </div>
      </footer>
    </div>
  );
}
