import { describe, it, expect } from "vitest";
import { slugify, domainFromUrl } from "@/lib/util";

describe("slugify", () => {
  it("kebab-cases and strips junk", () => {
    expect(slugify("Acme Roofing Co.")).toBe("acme-roofing-co");
    expect(slugify("  Hello--World  ")).toBe("hello-world");
    expect(slugify("STG!!!")).toBe("stg");
  });
});

describe("domainFromUrl", () => {
  it("extracts the bare domain", () => {
    expect(domainFromUrl("https://www.example.com/path")).toBe("example.com");
    expect(domainFromUrl("example.com")).toBe("example.com");
    expect(domainFromUrl("http://sub.example.co.uk")).toBe("sub.example.co.uk");
  });
});
