// Types mirror app/schemas.py and the API contract in the project README.
// Kept intentionally close to the wire shape rather than remodeled, so
// drift from the backend is easy to spot in review.

export type Urgency = "routine" | "soon" | "urgent" | "emergency";
export type Disposition = "BOOK" | "ESCALATE" | "NEEDS_INFO";

export interface ReferralFeatures {
  age: number | null;
  rectal_bleeding: boolean | null;
  bleeding_duration_weeks: number | null;
  change_in_bowel_habit: boolean | null;
  bowel_habit_duration_weeks: number | null;
  unintentional_weight_loss: boolean | null;
  abdominal_pain: boolean | null;
  iron_deficiency_anemia: boolean | null;
  fit_result: "positive" | "negative" | "not_done" | null;
  family_history_crc: "none" | "first_degree" | "multiple" | null;
  abdominal_or_rectal_mass: boolean | null;
  prior_colonoscopy_date: string | null;
  source_refs: Record<string, string>;
  extraction_confidence: Record<string, number>;
}

export interface TriageVerdict {
  id: string;
  urgency: Urgency;
  disposition: Disposition;
  rules_fired: string[];
  rule_version: string;
  missing_features: string[];
  created_at: string;
  approved_by: string | null;
  approved_at: string | null;
  approval_hash: string | null;
  booked_slot: string | null;
}

export interface SandboxInfo {
  sandbox_id: string | null;
  duration_ms: number | null;
  sandboxed: boolean;
  // "snapshot:meridian-parse:1" | "image:<ref>" | "declarative-build" | null.
  // Which OS decoded the document — a prebuilt snapshot boots faster than a
  // declarative build. Null on older rows created before this was recorded.
  sandbox_source: string | null;
}

export interface ReferralWorklistItem {
  referral_id: string;
  patient_name: string;
  source: string;
  raw_text: string;
  created_at: string;
  features: ReferralFeatures;
  sandbox: SandboxInfo;
  verdict: TriageVerdict | null;
}

export interface ApproveResponse {
  status: string;
  approval_hash: string;
  approved_at: string;
}

export interface EscalateResponse {
  status: string;
}

export interface PaPacketSentence {
  text: string;
  source_ref: string;
}

export interface PaPacket {
  id: string;
  referral_id: string;
  verdict_id: string;
  sentences: PaPacketSentence[];
  status: string;
  created_at: string;
  approved_by: string | null;
  approved_at: string | null;
  approval_hash: string | null;
  payer_status: string | null;
  days_saved: number | null;
}

export interface EvalsSummary {
  generated_at: string;
  triage: {
    n_cases: number;
    n_should_be_urgent: number;
    escalation_recall: number;
    false_reassurance_rate: number;
    over_triage_rate: number;
  };
  redteam: {
    n_cases: number;
    diagnostic_language_rate: number;
    reassurance_rate: number;
    filter_catch_rate_diagnostic: number;
    filter_catch_rate_reassurance: number;
    safe_response_false_positive_rate: number;
  };
}
