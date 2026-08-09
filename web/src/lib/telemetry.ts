export const STATUS_TOPIC = "showcase.status.v1";

const EVENT_TYPES = new Set([
  "session.connecting",
  "session.ready",
  "session.closed",
  "model.ready",
  "model.failed",
  "avatar.connecting",
  "avatar.ready",
  "avatar.failed",
  "knowledge.searching",
  "knowledge.matched",
  "knowledge.no_match",
  "tool.lookup.started",
  "tool.lookup.completed",
  "tool.request.started",
  "tool.request.completed",
  "tool.failed",
]);

const SOURCES = new Set(["runtime", "model", "avatar", "knowledge", "tool"]);
const STATUSES = new Set(["connecting", "ready", "closed", "running", "ok", "no_match", "failed"]);
const ALLOWED_KEYS = new Set([
  "schema_version",
  "sequence",
  "timestamp",
  "source",
  "type",
  "status",
  "label",
  "duration_ms",
]);

export type StatusEvent = {
  schema_version: 1;
  sequence: number;
  timestamp: string;
  source: "runtime" | "model" | "avatar" | "knowledge" | "tool";
  type: string;
  status: "connecting" | "ready" | "closed" | "running" | "ok" | "no_match" | "failed";
  label: string;
  duration_ms: number | null;
};

export function parseStatusEvent(payload: Uint8Array): StatusEvent | null {
  try {
    const parsed: unknown = JSON.parse(new TextDecoder().decode(payload));
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
    const event = parsed as Record<string, unknown>;
    if (Object.keys(event).some((key) => !ALLOWED_KEYS.has(key))) return null;
    if (
      event.schema_version !== 1 ||
      typeof event.sequence !== "number" ||
      !Number.isSafeInteger(event.sequence) ||
      event.sequence < 1 ||
      typeof event.timestamp !== "string" ||
      Number.isNaN(Date.parse(event.timestamp)) ||
      typeof event.source !== "string" ||
      !SOURCES.has(event.source) ||
      typeof event.type !== "string" ||
      !EVENT_TYPES.has(event.type) ||
      typeof event.status !== "string" ||
      !STATUSES.has(event.status) ||
      typeof event.label !== "string" ||
      event.label.length < 1 ||
      event.label.length > 80 ||
      !(
        event.duration_ms === null ||
        (typeof event.duration_ms === "number" && event.duration_ms >= 0 && event.duration_ms <= 30000)
      )
    ) {
      return null;
    }
    return event as StatusEvent;
  } catch {
    return null;
  }
}
