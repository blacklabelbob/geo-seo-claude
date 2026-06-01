import type { Database } from "@/lib/database.types";

export type Site = Database["public"]["Tables"]["sites"]["Row"];
export type Audit = Database["public"]["Tables"]["audits"]["Row"];
export type Finding = Database["public"]["Tables"]["audit_findings"]["Row"];
export type Fix = Database["public"]["Tables"]["fixes"]["Row"];
export type Deliverable = Database["public"]["Tables"]["deliverables"]["Row"];
export type Org = Database["public"]["Tables"]["orgs"]["Row"];

export type Tier = "good" | "moderate" | "poor" | "critical" | "none";

export function scoreTier(score: number | null | undefined): Tier {
  if (score === null || score === undefined) return "none";
  if (score >= 80) return "good";
  if (score >= 60) return "moderate";
  if (score >= 40) return "poor";
  return "critical";
}

export function scoreLabel(score: number | null | undefined): string {
  switch (scoreTier(score)) {
    case "good":
      return "Good";
    case "moderate":
      return "Moderate";
    case "poor":
      return "Poor";
    case "critical":
      return "Critical";
    default:
      return "Not scored";
  }
}

/** Tailwind text/border/bg color per tier (used across the UI). */
export const tierColor: Record<Tier, string> = {
  good: "#00b894",
  moderate: "#0984e3",
  poor: "#fdcb6e",
  critical: "#d63031",
  none: "#6c757d",
};

export const statusMeta: Record<string, { label: string; badge: string }> = {
  new: { label: "New", badge: "#6c757d" },
  audited: { label: "Audited", badge: "#fdcb6e" },
  proposal: { label: "Proposal Sent", badge: "#0984e3" },
  active: { label: "Active", badge: "#00b894" },
  won: { label: "Won", badge: "#00b894" },
  archived: { label: "Archived", badge: "#484f58" },
  lost: { label: "Lost", badge: "#484f58" },
};
