"use client";

import {
  Activity,
  AudioLines,
  BookOpenCheck,
  CircleStop,
  KeyRound,
  Mic,
  MicOff,
  PhoneCall,
  Radio,
  ShieldCheck,
  Sparkles,
  Wrench,
} from "lucide-react";
import {
  ConnectionState,
  Room,
  RoomEvent,
  Track,
  type RemoteParticipant,
  type RemoteTrack,
  type TranscriptionSegment,
} from "livekit-client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { parseStatusEvent, STATUS_TOPIC, type StatusEvent } from "@/lib/telemetry";

type ConnectionDetails = {
  serverUrl: string;
  participantToken: string;
};

type TranscriptLine = {
  id: string;
  speaker: "You" | "Concierge";
  text: string;
  final: boolean;
};

type ConsoleState = "idle" | "connecting" | "connected" | "reconnecting" | "ending" | "error";

const PREVIEW_EVENTS: StatusEvent[] = [
  {
    schema_version: 1,
    sequence: 1,
    timestamp: "2026-08-10T00:00:00.000Z",
    source: "model",
    type: "model.ready",
    status: "ready",
    label: "Realtime model ready",
    duration_ms: null,
  },
  {
    schema_version: 1,
    sequence: 2,
    timestamp: "2026-08-10T00:00:01.000Z",
    source: "knowledge",
    type: "knowledge.matched",
    status: "ok",
    label: "Knowledge found",
    duration_ms: 18,
  },
  {
    schema_version: 1,
    sequence: 3,
    timestamp: "2026-08-10T00:00:02.000Z",
    source: "tool",
    type: "tool.request.completed",
    status: "ok",
    label: "Service request created",
    duration_ms: 146,
  },
];

const PREVIEW_TRANSCRIPT: TranscriptLine[] = [
  { id: "preview-1", speaker: "You", text: "Could I get two extra towels after 7 PM?", final: true },
  {
    id: "preview-2",
    speaker: "Concierge",
    text: "Your demo housekeeping request is open. The request reference is SR-DEMO248.",
    final: true,
  },
];

function errorMessage(value: unknown): string {
  if (value instanceof DOMException && value.name === "NotAllowedError") {
    return "Microphone permission was denied.";
  }
  if (value instanceof Error && value.message) return value.message;
  return "The voice session could not be started.";
}

export function VoiceConsole() {
  const roomRef = useRef<Room | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioHostRef = useRef<HTMLDivElement>(null);
  const [preview, setPreview] = useState(false);
  const [state, setState] = useState<ConsoleState>("idle");
  const [events, setEvents] = useState<StatusEvent[]>([]);
  const [transcript, setTranscript] = useState<TranscriptLine[]>([]);
  const [accessCode, setAccessCode] = useState("");
  const [muted, setMuted] = useState(false);
  const [avatarVisible, setAvatarVisible] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const connected = state === "connected" || state === "reconnecting";

  useEffect(() => {
    if (!new URLSearchParams(window.location.search).has("preview")) return;
    setPreview(true);
    setState("connected");
    setEvents(PREVIEW_EVENTS);
    setTranscript(PREVIEW_TRANSCRIPT);
  }, []);

  const statusLabel = useMemo(() => {
    const labels: Record<ConsoleState, string> = {
      idle: "Ready",
      connecting: "Connecting",
      connected: "Live",
      reconnecting: "Reconnecting",
      ending: "Ending",
      error: "Needs attention",
    };
    return labels[state];
  }, [state]);

  const endSession = useCallback(async () => {
    const room = roomRef.current;
    roomRef.current = null;
    if (!room) return;
    setState("ending");
    try {
      await room.localParticipant.setMicrophoneEnabled(false);
      await room.disconnect();
    } finally {
      if (audioHostRef.current) audioHostRef.current.replaceChildren();
      setAvatarVisible(false);
      setMuted(false);
      setState("idle");
    }
  }, []);

  useEffect(() => {
    return () => {
      const room = roomRef.current;
      roomRef.current = null;
      if (room) void room.disconnect();
    };
  }, []);

  const startSession = useCallback(async () => {
    if (roomRef.current || preview) return;
    setError(null);
    setEvents([]);
    setTranscript([]);
    setState("connecting");

    const room = new Room({ adaptiveStream: true, dynacast: true });
    roomRef.current = room;

    const onTrackSubscribed = (track: RemoteTrack) => {
      if (track.kind === Track.Kind.Video && videoRef.current) {
        track.attach(videoRef.current);
        setAvatarVisible(true);
      }
      if (track.kind === Track.Kind.Audio && audioHostRef.current) {
        const element = track.attach();
        element.setAttribute("data-remote-audio", "true");
        audioHostRef.current.append(element);
      }
    };

    const onTrackUnsubscribed = (track: RemoteTrack) => {
      track.detach().forEach((element) => element.remove());
      if (track.kind === Track.Kind.Video) setAvatarVisible(false);
    };

    const onData = (payload: Uint8Array, _participant?: RemoteParticipant, _kind?: unknown, topic?: string) => {
      if (topic !== STATUS_TOPIC) return;
      const event = parseStatusEvent(payload);
      if (event) setEvents((current) => [...current.slice(-11), event]);
    };

    const onTranscription = (segments: TranscriptionSegment[], participant?: { isLocal?: boolean }) => {
      setTranscript((current) => {
        const updated = new Map(current.map((line) => [line.id, line]));
        for (const segment of segments) {
          updated.set(segment.id, {
            id: segment.id,
            speaker: participant?.isLocal ? "You" : "Concierge",
            text: segment.text,
            final: segment.final,
          });
        }
        return [...updated.values()].slice(-24);
      });
    };

    room
      .on(RoomEvent.TrackSubscribed, onTrackSubscribed)
      .on(RoomEvent.TrackUnsubscribed, onTrackUnsubscribed)
      .on(RoomEvent.DataReceived, onData)
      .on(RoomEvent.TranscriptionReceived, onTranscription)
      .on(RoomEvent.Reconnecting, () => setState("reconnecting"))
      .on(RoomEvent.Reconnected, () => setState("connected"))
      .on(RoomEvent.Disconnected, () => {
        if (roomRef.current === room) {
          roomRef.current = null;
          setState("idle");
          setAvatarVisible(false);
        }
      });

    try {
      const response = await fetch("/api/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        body: JSON.stringify(accessCode ? { accessCode } : {}),
      });
      const payload = (await response.json()) as ConnectionDetails & {
        error?: { message?: string };
      };
      if (!response.ok) throw new Error(payload.error?.message || "Unable to create a voice session.");
      await room.connect(payload.serverUrl, payload.participantToken);
      await room.localParticipant.setMicrophoneEnabled(true);
      setState("connected");
    } catch (value) {
      roomRef.current = null;
      await room.disconnect();
      setError(errorMessage(value));
      setState("error");
    }
  }, [accessCode, preview]);

  const toggleMicrophone = useCallback(async () => {
    const room = roomRef.current;
    if (!room || room.state !== ConnectionState.Connected) return;
    const nextMuted = !muted;
    await room.localParticipant.setMicrophoneEnabled(!nextMuted);
    setMuted(nextMuted);
  }, [muted]);

  return (
    <main className="console-shell">
      <header className="topbar">
        <div className="brand-lockup" aria-label="Harborlight Live">
          <span className="brand-mark"><AudioLines aria-hidden="true" size={20} /></span>
          <span>Harborlight <strong>Live</strong></span>
        </div>
        <div className={`connection-badge state-${state}`} role="status">
          <span className="status-dot" />{statusLabel}
        </div>
      </header>

      <section className="workspace" aria-label="Voice concierge console">
        <div className="stage-column">
          <div className="avatar-stage" data-testid="avatar-stage">
            <video ref={videoRef} autoPlay playsInline aria-label="Digital human video" />
            <div className={`avatar-fallback ${avatarVisible ? "is-hidden" : ""}`}>
              <div className="monogram" aria-hidden="true">H</div>
              <div>
                <span className="eyebrow">Harborlight Hotel</span>
                <h1>Voice Concierge</h1>
              </div>
            </div>
            <div className="stage-meta">
              <span><Radio size={14} aria-hidden="true" /> Realtime</span>
              <span>EN / 中文</span>
            </div>
          </div>

          <div className="controls" aria-label="Session controls">
            <label className="access-field">
              <KeyRound size={16} aria-hidden="true" />
              <span className="sr-only">Demo access code</span>
              <input
                type="password"
                autoComplete="off"
                placeholder="Access code (optional)"
                value={accessCode}
                onChange={(event) => setAccessCode(event.target.value)}
                disabled={state !== "idle" && state !== "error"}
              />
            </label>
            {!connected ? (
              <button
                className="primary-control"
                type="button"
                onClick={startSession}
                disabled={state === "connecting" || state === "ending" || preview}
              >
                <PhoneCall size={18} aria-hidden="true" />
                {state === "connecting" ? "Connecting" : preview ? "Preview" : "Start call"}
              </button>
            ) : (
              <>
                <button className="icon-control" type="button" onClick={toggleMicrophone} title={muted ? "Unmute" : "Mute"}>
                  {muted ? <MicOff size={19} aria-hidden="true" /> : <Mic size={19} aria-hidden="true" />}
                  <span className="sr-only">{muted ? "Unmute microphone" : "Mute microphone"}</span>
                </button>
                <button className="end-control" type="button" onClick={endSession} disabled={preview}>
                  <CircleStop size={18} aria-hidden="true" /> End
                </button>
              </>
            )}
          </div>
          {error && <p className="error-banner" role="alert">{error}</p>}
          <div ref={audioHostRef} className="audio-host" aria-hidden="true" />
        </div>

        <aside className="activity-column">
          <section className="transcript-panel" aria-labelledby="transcript-title">
            <div className="panel-heading">
              <div><span className="eyebrow">Conversation</span><h2 id="transcript-title">Live transcript</h2></div>
              <Sparkles size={18} aria-hidden="true" />
            </div>
            <div className="transcript-stream" aria-live="polite" data-testid="transcript-stream">
              {transcript.length === 0 ? (
                <div className="empty-state"><AudioLines size={24} aria-hidden="true" /><span>Transcript will appear here</span></div>
              ) : transcript.map((line) => (
                <div className={`transcript-line speaker-${line.speaker === "You" ? "guest" : "agent"}`} key={line.id}>
                  <span>{line.speaker}</span>
                  <p className={line.final ? "" : "interim"}>{line.text}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="timeline-panel" aria-labelledby="timeline-title">
            <div className="panel-heading compact">
              <div><span className="eyebrow">Runtime</span><h2 id="timeline-title">Capability status</h2></div>
              <Activity size={18} aria-hidden="true" />
            </div>
            <div className="status-timeline" data-testid="status-timeline">
              {events.length === 0 ? (
                <div className="status-placeholder"><span />Waiting for session</div>
              ) : events.slice(-5).map((event) => (
                <div className={`status-row status-${event.status}`} key={`${event.sequence}-${event.type}`}>
                  <span className="event-icon" aria-hidden="true">
                    {event.source === "knowledge" ? <BookOpenCheck size={15} /> : event.source === "tool" ? <Wrench size={15} /> : <ShieldCheck size={15} />}
                  </span>
                  <div><strong>{event.label}</strong><small>{event.source}{event.duration_ms !== null ? ` · ${event.duration_ms} ms` : ""}</small></div>
                </div>
              ))}
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}
