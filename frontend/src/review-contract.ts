export const absenceStatuses = ["PRESENTE", "NAO_INFORMADO", "NAO_APLICAVEL", "NAO_EXTRAIDO", "INCERTO", "NAO_HOUVE_EVENTO"] as const;
export const criticalFields = new Set(["purpose", "population", "design", "intervention", "comparator", "outcome", "time_frame", "sample_size", "result", "effect_summary"]);
export type ReviewDecision = "ACEITAR" | "CORRIGIR" | "REJEITAR";
