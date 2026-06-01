import { describe, it, expect } from "vitest";
import { scoreTier, scoreLabel, tierColor } from "@/lib/scores";

describe("scoreTier", () => {
  it("buckets scores into tiers", () => {
    expect(scoreTier(90)).toBe("good");
    expect(scoreTier(80)).toBe("good");
    expect(scoreTier(70)).toBe("moderate");
    expect(scoreTier(60)).toBe("moderate");
    expect(scoreTier(50)).toBe("poor");
    expect(scoreTier(40)).toBe("poor");
    expect(scoreTier(28)).toBe("critical");
    expect(scoreTier(0)).toBe("critical");
  });

  it("treats null/undefined as 'none'", () => {
    expect(scoreTier(null)).toBe("none");
    expect(scoreTier(undefined)).toBe("none");
  });
});

describe("scoreLabel", () => {
  it("labels each tier", () => {
    expect(scoreLabel(85)).toBe("Good");
    expect(scoreLabel(65)).toBe("Moderate");
    expect(scoreLabel(45)).toBe("Poor");
    expect(scoreLabel(20)).toBe("Critical");
    expect(scoreLabel(null)).toBe("Not scored");
  });
});

describe("tierColor", () => {
  it("has a color for every tier", () => {
    for (const t of ["good", "moderate", "poor", "critical", "none"] as const) {
      expect(tierColor[t]).toMatch(/^#[0-9a-f]{6}$/i);
    }
  });
});
