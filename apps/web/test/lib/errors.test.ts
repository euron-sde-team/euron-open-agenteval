import { describe, expect, it } from "vitest";

import { ApiError, errorMessage, isErrorEnvelope, parseApiError, validationMessages } from "@/lib/api/errors";

describe("isErrorEnvelope", () => {
  it("is true for a well-formed error envelope", () => {
    expect(isErrorEnvelope({ error: { code: "not_found", message: "Not found" } })).toBe(true);
  });

  it("is false for a plain object, null, or a missing field", () => {
    expect(isErrorEnvelope(null)).toBe(false);
    expect(isErrorEnvelope({})).toBe(false);
    expect(isErrorEnvelope({ error: {} })).toBe(false);
    expect(isErrorEnvelope({ error: { message: "x" } })).toBe(false);
    expect(isErrorEnvelope({ error: { code: "x" } })).toBe(false);
  });
});

describe("validationMessages", () => {
  it("formats a field path and message for each validation error", () => {
    const lines = validationMessages({
      errors: [
        { loc: ["body", "email"], msg: "field required" },
        { loc: ["body", "password"], msg: "too short" },
      ],
    });
    expect(lines).toEqual(["email: field required", "password: too short"]);
  });

  it("drops the body/query/path location prefix", () => {
    const lines = validationMessages({ errors: [{ loc: ["query", "page"], msg: "must be positive" }] });
    expect(lines).toEqual(["page: must be positive"]);
  });

  it("omits the field prefix when there is no location", () => {
    const lines = validationMessages({ errors: [{ msg: "something is wrong" }] });
    expect(lines).toEqual(["something is wrong"]);
  });

  it("returns an empty list when errors is missing or not an array", () => {
    expect(validationMessages({})).toEqual([]);
    expect(validationMessages({ errors: "not an array" })).toEqual([]);
  });

  it("skips an entry with no message", () => {
    const lines = validationMessages({ errors: [{ loc: ["body", "x"] }] });
    expect(lines).toEqual([]);
  });
});

describe("parseApiError", () => {
  it("builds an ApiError from the server's error envelope", () => {
    const err = parseApiError(404, { error: { code: "not_found", message: "Repository not found" } });
    expect(err.status).toBe(404);
    expect(err.code).toBe("not_found");
    expect(err.message).toBe("Repository not found");
  });

  it("builds a validation_error ApiError from FastAPI's default 422 body", () => {
    const err = parseApiError(422, { detail: [{ loc: ["body", "email"], msg: "field required" }] });
    expect(err.code).toBe("validation_error");
    expect(err.details.errors).toEqual([{ loc: ["body", "email"], msg: "field required" }]);
  });

  it("falls back to a generic error for an unrecognized body", () => {
    const err = parseApiError(500, "plain text, not json");
    expect(err.code).toBe("http_500");
    expect(err.message).toMatch(/unexpected error/);
  });

  it("gives a specific fallback message per status code", () => {
    expect(parseApiError(401, null).message).toMatch(/session expired/);
    expect(parseApiError(403, null).message).toMatch(/role does not allow/);
    expect(parseApiError(404, null).message).toMatch(/no longer exists/);
    expect(parseApiError(429, null).message).toMatch(/Too many requests/);
    expect(parseApiError(0, null).message).toMatch(/Cannot reach/);
  });
});

describe("ApiError", () => {
  it("exposes isUnauthorized, isForbidden and isNetwork", () => {
    expect(new ApiError({ status: 401, code: "x", message: "x" }).isUnauthorized).toBe(true);
    expect(new ApiError({ status: 403, code: "x", message: "x" }).isForbidden).toBe(true);
    expect(new ApiError({ status: 0, code: "x", message: "x" }).isNetwork).toBe(true);
    expect(new ApiError({ status: 200, code: "x", message: "x" }).isUnauthorized).toBe(false);
  });
});

describe("errorMessage", () => {
  it("joins validation messages for a validation_error ApiError", () => {
    const err = new ApiError({
      status: 422,
      code: "validation_error",
      message: "Request validation failed",
      details: { errors: [{ loc: ["body", "name"], msg: "field required" }] },
    });
    expect(errorMessage(err)).toBe("name: field required");
  });

  it("uses the session-expired fallback for a 401 that is not invalid_credentials", () => {
    const err = new ApiError({ status: 401, code: "session_expired", message: "whatever" });
    expect(errorMessage(err)).toMatch(/session expired/);
  });

  it("keeps the server's own message for invalid_credentials", () => {
    const err = new ApiError({ status: 401, code: "invalid_credentials", message: "Email or password is incorrect" });
    expect(errorMessage(err)).toBe("Email or password is incorrect");
  });

  it("treats a TypeError as a network failure", () => {
    expect(errorMessage(new TypeError("Failed to fetch"))).toMatch(/Cannot reach/);
  });

  it("uses a plain Error's own message", () => {
    expect(errorMessage(new Error("boom"))).toBe("boom");
  });

  it("gives a generic message for a thrown non-Error value", () => {
    expect(errorMessage("a string, not an Error")).toMatch(/Something went wrong/);
  });
});
