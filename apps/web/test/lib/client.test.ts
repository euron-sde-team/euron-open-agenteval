import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/errors";
import { unwrap } from "@/lib/api/client";

function fakeResponse(status: number): Response {
  return new Response(null, { status });
}

describe("unwrap", () => {
  it("returns the data for a successful call", async () => {
    const result = await unwrap(
      Promise.resolve({ data: { id: "1" }, response: fakeResponse(200) }),
    );
    expect(result).toEqual({ id: "1" });
  });

  it("throws an ApiError built from the envelope for a non-ok response", async () => {
    await expect(
      unwrap(
        Promise.resolve({
          error: { error: { code: "not_found", message: "Repository not found" } },
          response: fakeResponse(404),
        }),
      ),
    ).rejects.toMatchObject({ status: 404, code: "not_found", message: "Repository not found" });
  });

  it("turns a thrown network failure into a status 0 ApiError", async () => {
    await expect(unwrap(Promise.reject(new TypeError("Failed to fetch")))).rejects.toMatchObject({
      status: 0,
    });
  });

  it("rethrows an ApiError thrown by the call itself unchanged", async () => {
    const original = new ApiError({ status: 401, code: "session_expired", message: "x" });
    await expect(unwrap(Promise.reject(original))).rejects.toBe(original);
  });
});
