import { createHash, randomUUID, timingSafeEqual } from "node:crypto";

import { SignJWT } from "jose";

export type TokenRequest = {
  accessCode?: string;
};

export type ConnectionDetails = {
  serverUrl: string;
  participantToken: string;
  roomName: string;
  participantName: string;
  expiresInSeconds: number;
};

export class TokenRequestError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

function required(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) {
    throw new TokenRequestError(503, "TOKEN_SERVICE_UNAVAILABLE", "Token service is not configured.");
  }
  return value;
}

function safeEqual(received: string, expected: string): boolean {
  const left = createHash("sha256").update(received).digest();
  const right = createHash("sha256").update(expected).digest();
  return timingSafeEqual(left, right);
}

export function validateTokenRequest(value: unknown): TokenRequest {
  if (value === undefined || value === null) return {};
  if (typeof value !== "object" || Array.isArray(value)) {
    throw new TokenRequestError(400, "INVALID_REQUEST", "Request body must be a JSON object.");
  }

  const record = value as Record<string, unknown>;
  if (Object.keys(record).some((key) => key !== "accessCode")) {
    throw new TokenRequestError(400, "UNSUPPORTED_FIELD", "Only accessCode is accepted.");
  }
  if (record.accessCode !== undefined && typeof record.accessCode !== "string") {
    throw new TokenRequestError(400, "INVALID_ACCESS_CODE", "Access code must be a string.");
  }
  return { accessCode: record.accessCode as string | undefined };
}

export async function createConnectionDetails(request: TokenRequest): Promise<ConnectionDetails> {
  const expectedCode = process.env.SHOWCASE_ACCESS_CODE?.trim() ?? "";
  if (expectedCode && !safeEqual(request.accessCode ?? "", expectedCode)) {
    throw new TokenRequestError(401, "ACCESS_DENIED", "Access code is invalid.");
  }

  const apiKey = required("LIVEKIT_API_KEY");
  const apiSecret = required("LIVEKIT_API_SECRET");
  const serverUrl = required("PUBLIC_LIVEKIT_URL");
  const agentName = process.env.AGENT_NAME?.trim() || "showcase-voice-agent";
  if (!/^\w[\w.-]{0,63}$/.test(agentName)) {
    throw new TokenRequestError(503, "TOKEN_SERVICE_UNAVAILABLE", "Agent dispatch is invalid.");
  }
  let parsedServerUrl: URL;
  try {
    parsedServerUrl = new URL(serverUrl);
  } catch {
    throw new TokenRequestError(503, "TOKEN_SERVICE_UNAVAILABLE", "LiveKit URL is invalid.");
  }
  if (!new Set(["ws:", "wss:"]).has(parsedServerUrl.protocol)) {
    throw new TokenRequestError(503, "TOKEN_SERVICE_UNAVAILABLE", "LiveKit URL is invalid.");
  }
  const suffix = randomUUID().replaceAll("-", "").slice(0, 16);
  const roomName = `showcase-${suffix}`;
  const participantName = `guest-${suffix.slice(0, 10)}`;
  const expiresInSeconds = 600;

  const now = Math.floor(Date.now() / 1000);
  const participantToken = await new SignJWT({
    name: "Showcase Guest",
    video: {
      room: roomName,
      roomJoin: true,
      canPublish: true,
      canPublishData: true,
      canSubscribe: true,
    },
    roomConfig: { agents: [{ agentName }] },
  })
    .setProtectedHeader({ alg: "HS256", typ: "JWT" })
    .setIssuer(apiKey)
    .setSubject(participantName)
    .setNotBefore(now)
    .setExpirationTime(now + expiresInSeconds)
    .sign(new TextEncoder().encode(apiSecret));

  return {
    serverUrl,
    participantToken,
    roomName,
    participantName,
    expiresInSeconds,
  };
}
