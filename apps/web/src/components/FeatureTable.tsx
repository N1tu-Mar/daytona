import type { ReferralFeatures } from "@/lib/types";

const FEATURE_LABELS: Record<string, string> = {
  age: "Age",
  rectal_bleeding: "Rectal bleeding",
  bleeding_duration_weeks: "Bleeding duration (weeks)",
  change_in_bowel_habit: "Change in bowel habit",
  bowel_habit_duration_weeks: "Bowel habit change duration (weeks)",
  unintentional_weight_loss: "Unintentional weight loss",
  abdominal_pain: "Abdominal pain",
  iron_deficiency_anemia: "Iron deficiency anemia",
  fit_result: "FIT result",
  family_history_crc: "Family history of colorectal cancer",
  abdominal_or_rectal_mass: "Abdominal or rectal mass",
  prior_colonoscopy_date: "Prior colonoscopy date",
};

const FEATURE_ORDER = Object.keys(FEATURE_LABELS);

function formatValue(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "boolean") return v ? "Yes" : "No";
  return String(v);
}

function confidenceColor(c: number | undefined): string {
  if (c === undefined) return "text-slate-400";
  if (c >= 0.8) return "text-emerald-600 dark:text-emerald-400";
  if (c >= 0.5) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

export default function FeatureTable({ features }: { features: ReferralFeatures }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead className="bg-slate-100 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900 dark:text-slate-400">
          <tr>
            <th className="px-4 py-2 font-medium">Feature</th>
            <th className="px-4 py-2 font-medium">Value</th>
            <th className="px-4 py-2 font-medium">Source</th>
            <th className="px-4 py-2 font-medium">Confidence</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
          {FEATURE_ORDER.map((key) => {
            const value = (features as unknown as Record<string, unknown>)[key];
            const sourceRef = features.source_refs?.[key];
            const confidence = features.extraction_confidence?.[key];
            const isMissing = value === null || value === undefined;
            return (
              <tr
                key={key}
                className={isMissing ? "bg-slate-50/60 dark:bg-slate-900/40" : undefined}
              >
                <td className="px-4 py-2 font-medium text-slate-700 dark:text-slate-200">
                  {FEATURE_LABELS[key]}
                </td>
                <td className="px-4 py-2 text-slate-900 dark:text-slate-100">
                  {formatValue(value)}
                </td>
                <td
                  className="max-w-xs truncate px-4 py-2 text-slate-500 dark:text-slate-400"
                  title={sourceRef || undefined}
                >
                  {sourceRef || "—"}
                </td>
                <td className={`px-4 py-2 font-mono text-xs ${confidenceColor(confidence)}`}>
                  {confidence !== undefined ? confidence.toFixed(2) : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
