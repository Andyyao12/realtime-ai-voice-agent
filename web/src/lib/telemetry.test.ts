import { describe, expect, it } from "vitest";

import { parseStatusEvent } from "./telemetry";

const encode = (value: unknown) => new TextEncoder().encode(JSON.stringify(value));

describe("parseStatusEvent", () => {
  it("accepts the public status schema", () => {
    const event = parseStatusEvent(
      encode({
        schema_version: 1,
        sequence: 4,
        timestamp: "2026-08-10T00:00:00.000Z",
        source: "tool",
        type: "tool.lookup.completed",
        status: "ok",
        label: "Reservation lookup complete",
        duration_ms: 42,
      }),
    );

    expect(event?.type).toBe("tool.lookup.completed");
  });

  it("rejects unknown fields and malformed payloads", () => {
    expect(
      parseStatusEvent(
        encode({
          schema_version: 1,
          sequence: 1,
          timestamp: "2026-08-10T00:00:00.000Z",
          source: "tool",
          type: "tool.lookup.completed",
          status: "ok",
          label: "Done",
          duration_ms: null,
          raw_arguments: { last_name: "private" },
        }),
      ),
    ).toBeNull();
    expect(parseStatusEvent(new TextEncoder().encode("not-json"))).toBeNull();
  });
});
