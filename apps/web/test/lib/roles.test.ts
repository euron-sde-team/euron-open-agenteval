import { describe, expect, it } from "vitest";

import { roleAtLeast, roleLabel } from "@/lib/roles";

describe("roleAtLeast", () => {
  it("ranks owner above admin above member above viewer", () => {
    expect(roleAtLeast("owner", "admin")).toBe(true);
    expect(roleAtLeast("admin", "member")).toBe(true);
    expect(roleAtLeast("member", "viewer")).toBe(true);
  });

  it("is true for a role exactly matching the minimum", () => {
    expect(roleAtLeast("admin", "admin")).toBe(true);
  });

  it("is false for a role below the minimum", () => {
    expect(roleAtLeast("viewer", "admin")).toBe(false);
    expect(roleAtLeast("member", "owner")).toBe(false);
  });

  it("is false for a null or undefined role", () => {
    expect(roleAtLeast(null, "viewer")).toBe(false);
    expect(roleAtLeast(undefined, "viewer")).toBe(false);
  });

  it("is false for an unrecognized role string", () => {
    expect(roleAtLeast("superadmin", "viewer")).toBe(false);
  });
});

describe("roleLabel", () => {
  it("capitalizes the role", () => {
    expect(roleLabel("owner")).toBe("Owner");
    expect(roleLabel("admin")).toBe("Admin");
  });
});
