import { describe, expect, it } from "vitest";

import { formatDate, formatDateTime, formatNumber, formatRelative, initials } from "@/lib/format";

describe("formatNumber", () => {
  it("adds thousands separators", () => {
    expect(formatNumber(14923)).toBe("14,923");
  });

  it("is n/a for null, undefined, or non-finite values", () => {
    expect(formatNumber(null)).toBe("n/a");
    expect(formatNumber(undefined)).toBe("n/a");
    expect(formatNumber(Number.NaN)).toBe("n/a");
  });
});

describe("formatDateTime and formatDate", () => {
  it("is n/a for a missing or invalid timestamp", () => {
    expect(formatDateTime(null)).toBe("n/a");
    expect(formatDateTime("not-a-date")).toBe("n/a");
    expect(formatDate(undefined)).toBe("n/a");
    expect(formatDate("not-a-date")).toBe("n/a");
  });

  it("formats a valid ISO timestamp", () => {
    expect(formatDate("2026-03-05T12:00:00Z")).toBe("Mar 5, 2026");
  });
});

describe("formatRelative", () => {
  const now = new Date("2026-03-05T12:00:00Z");

  it("is Never for a missing timestamp", () => {
    expect(formatRelative(null, now)).toBe("Never");
  });

  it("is n/a for an invalid timestamp", () => {
    expect(formatRelative("not-a-date", now)).toBe("n/a");
  });

  it("is just now for a moment just past", () => {
    expect(formatRelative(new Date(now.getTime() - 5_000).toISOString(), now)).toBe("just now");
  });

  it("buckets minutes, hours, and days ago", () => {
    expect(formatRelative(new Date(now.getTime() - 5 * 60_000).toISOString(), now)).toBe("5m ago");
    expect(formatRelative(new Date(now.getTime() - 3 * 3_600_000).toISOString(), now)).toBe("3h ago");
    expect(formatRelative(new Date(now.getTime() - 2 * 86_400_000).toISOString(), now)).toBe("2d ago");
  });

  it("falls back to a date beyond two weeks", () => {
    expect(formatRelative(new Date(now.getTime() - 20 * 86_400_000).toISOString(), now)).toBe(
      formatDate(new Date(now.getTime() - 20 * 86_400_000).toISOString()),
    );
  });

  it("handles a future timestamp", () => {
    expect(formatRelative(new Date(now.getTime() + 5 * 60_000).toISOString(), now)).toBe("in 5m");
  });
});

describe("initials", () => {
  it("takes the first letter of the first and last name", () => {
    expect(initials("Avery Chen")).toBe("AC");
  });

  it("takes a single letter for a single name", () => {
    expect(initials("Avery")).toBe("A");
  });

  it("is ? for a missing or blank name", () => {
    expect(initials(null)).toBe("?");
    expect(initials(undefined)).toBe("?");
    expect(initials("   ")).toBe("?");
  });
});
