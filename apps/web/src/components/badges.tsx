import type { Disposition, SandboxInfo, Urgency } from "@/lib/types";

// Color-coded per spec: routine=gray, soon=blue, urgent=orange, emergency=red.
const URGENCY_STYLES: Record<Urgency, string> = {
  routine: "bg-slate-100 text-slate-700 ring-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-600",
  soon: "bg-blue-50 text-blue-700 ring-blue-300 dark:bg-blue-950 dark:text-blue-300 dark:ring-blue-700",
  urgent: "bg-orange-50 text-orange-700 ring-orange-300 dark:bg-orange-950 dark:text-orange-300 dark:ring-orange-700",
  emergency: "bg-red-50 text-red-700 ring-red-400 dark:bg-red-950 dark:text-red-300 dark:ring-red-700",
};

export function UrgencyBadge({ urgency }: { urgency: Urgency }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide ring-1 ring-inset ${URGENCY_STYLES[urgency]}`}
    >
      {urgency}
    </span>
  );
}

const DISPOSITION_STYLES: Record<Disposition, string> = {
  BOOK: "bg-emerald-50 text-emerald-700 ring-emerald-300 dark:bg-emerald-950 dark:text-emerald-300 dark:ring-emerald-700",
  ESCALATE: "bg-amber-50 text-amber-800 ring-amber-300 dark:bg-amber-950 dark:text-amber-300 dark:ring-amber-700",
  NEEDS_INFO: "bg-violet-50 text-violet-700 ring-violet-300 dark:bg-violet-950 dark:text-violet-300 dark:ring-violet-700",
};

export function DispositionBadge({ disposition }: { disposition: Disposition }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${DISPOSITION_STYLES[disposition]}`}
    >
      {disposition.replace("_", " ")}
    </span>
  );
}

// Auditable proof the document was decoded inside an isolated, network-blocked
// Daytona sandbox that was then destroyed. Renders nothing for synthetic seed
// data or the unsandboxed local-decode fallback (sandboxed === false).
export function SandboxBadge({ sandbox }: { sandbox: SandboxInfo | null | undefined }) {
  if (!sandbox?.sandboxed) return null;
  const secs =
    sandbox.duration_ms != null ? `${(sandbox.duration_ms / 1000).toFixed(1)}s` : null;
  // "snapshot:meridian-parse:1" -> "snapshot", "declarative-build" -> "build".
  // The prefix is the audit-worthy bit (which OS parsed this); the full label
  // lives in the tooltip. Null on older rows — then we just omit it.
  const source = sandbox.sandbox_source;
  const sourceShort = source ? source.split(":")[0] : null;
  return (
    <span
      title={
        "Untrusted document decoded inside an isolated, network-blocked Daytona sandbox, then destroyed." +
        (source ? `\nParsed by: ${source}` : "")
      }
      className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-300 dark:bg-emerald-950 dark:text-emerald-300 dark:ring-emerald-700"
    >
      🔒 Daytona sandbox
      {sandbox.sandbox_id ? <span className="font-mono">{sandbox.sandbox_id}</span> : null}
      {secs ? <span className="text-emerald-600 dark:text-emerald-400">· {secs}</span> : null}
      {sourceShort ? (
        <span className="text-emerald-600 dark:text-emerald-400">· {sourceShort}</span>
      ) : null}
    </span>
  );
}
