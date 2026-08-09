import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { createConnectionDetails, TokenRequestError, validateTokenRequest } from "./token";

const ENV_KEYS = [
  "LIVEKIT_API_KEY",
  "LIVEKIT_API_SECRET",
  "PUBLIC_LIVEKIT_URL",
  "AGENT_NAME",
  "SHOWCASE_ACCESS_CODE",
] as const;
const originalEnv = Object.fromEntries(ENV_KEYS.map((key) => [key, process.env[key]]));

function decodePart(value: string): Record<string, unknown> {
  return JSON.parse(Buffer.from(value, "base64url").toString("utf8")) as Record<string, unknown>;
}

beforeEach(() => {
  process.env.LIVEKIT_API_KEY = "test-api-key";
  process.env.LIVEKIT_API_SECRET = "test-api-secret-at-least-32-characters";
  process.env.PUBLIC_LIVEKIT_URL = "wss://rtc.example.test";
  process.env.AGENT_NAME = "showcase-voice-agent";
  delete process.env.SHOWCASE_ACCESS_CODE;
});

afterEach(() => {
  for (const key of ENV_KEYS) {
    const value = originalEnv[key];
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
});

describe("token issuance", () => {
  it("uses a random room, fixed dispatch, and ten-minute claims", async () => {
    const first = await createConnectionDetails({});
    const second = await createConnectionDetails({});
    const claims = decodePart(first.participantToken.split(".")[1]);

    expect(first.roomName).toMatch(/^showcase-[a-f0-9]{16}$/);
    expect(first.roomName).not.toBe(second.roomName);
    expect(first.participantName).toMatch(/^guest-[a-f0-9]{10}$/);
    expect(first.expiresInSeconds).toBe(600);
    expect(claims.sub).toBe(first.participantName);
    expect((claims.video as Record<string, unknown>).room).toBe(first.roomName);
    expect((claims.video as Record<string, unknown>).roomJoin).toBe(true);
    expect((claims.roomConfig as { agents: Array<{ agentName: string }> }).agents[0].agentName).toBe(
      "showcase-voice-agent",
    );
    expect(Object.keys(claims.roomConfig as Record<string, unknown>)).toEqual(["agents"]);
    expect(
      Object.keys((claims.roomConfig as { agents: Array<Record<string, unknown>> }).agents[0]),
    ).toEqual(["agentName"]);
    expect((claims.exp as number) - (claims.nbf as number)).toBe(600);
  });

  it("enforces the optional access code", async () => {
    process.env.SHOWCASE_ACCESS_CODE = "demo-only";

    await expect(createConnectionDetails({ accessCode: "wrong" })).rejects.toMatchObject({
      status: 401,
      code: "ACCESS_DENIED",
    });
    await expect(createConnectionDetails({ accessCode: "demo-only" })).resolves.toHaveProperty(
      "participantToken",
    );
  });

  it("rejects client-controlled room or agent fields", () => {
    expect(() => validateTokenRequest({ room: "chosen-by-client" })).toThrowError(TokenRequestError);
    expect(() => validateTokenRequest({ agentName: "another-agent" })).toThrowError(
      "Only accessCode is accepted.",
    );
  });
});
