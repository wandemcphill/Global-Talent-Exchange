import { useEffect, useRef, useState } from "react";
import { API, tokens } from "@/lib/api";

export type RealtimeConnectionState =
  | "idle"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "auth_error"
  | "closed";

export type RealtimeEvent = { type: string; data: any };

const AUTH_REJECT_CLOSE_CODES = new Set([1008, 4401, 4403]);

function isAuthFailureClose(code?: number, reason?: string): boolean {
  if (typeof code === "number" && AUTH_REJECT_CLOSE_CODES.has(code)) return true;
  const text = (reason || "").toLowerCase();
  return text.includes("unauthorized") || text.includes("forbidden") || text.includes("invalid token") || text.includes("auth");
}

function wsUrl(topics: string[]): { url: string; hasToken: boolean } {
  const origin = API.replace(/\/api$/, "");
  const base = origin.replace(/^http/, "ws");
  const params = new URLSearchParams();
  topics.forEach((t) => params.append("topic", t));
  const token = tokens.get();
  if (token) params.set("token", token);
  return {
    url: `${base}/realtime/stream?${params.toString()}`,
    hasToken: Boolean(token),
  };
}

/**
 * Subscribes to authorized realtime topics. REST remains the durable source of truth:
 * on every (re)connect `onReconnect` fires so callers can fetch messages after their
 * last known seq and de-duplicate by seq/id.
 */
export function useRealtimeTopics(
  topics: string[],
  onEvent: (event: RealtimeEvent) => void,
  onReconnect?: () => void,
  enabled = true
) {
  const [connected, setConnected] = useState(false);
  const [connectionState, setConnectionState] = useState<RealtimeConnectionState>("idle");
  const [lastCloseCode, setLastCloseCode] = useState<number | null>(null);
  const [lastCloseReason, setLastCloseReason] = useState<string | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState<number>(0);

  const handlerRef = useRef(onEvent);
  const reconnectRef = useRef(onReconnect);
  handlerRef.current = onEvent;
  reconnectRef.current = onReconnect;
  const key = topics.join("|");

  useEffect(() => {
    if (!enabled || topics.length === 0 || typeof WebSocket === "undefined") {
      setConnected(false);
      setConnectionState("idle");
      return;
    }
    let socket: WebSocket | null = null;
    let closed = false;
    let attempt = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let hasConnectedBefore = false;

    const open = () => {
      if (closed) return;
      const { url, hasToken } = wsUrl(topics);
      setConnectionState(attempt > 0 ? "reconnecting" : "connecting");
      try {
        socket = new WebSocket(url);
      } catch (err) {
        setLastError(err instanceof Error ? err.message : "Failed to construct WebSocket");
        schedule();
        return;
      }
      socket.onopen = () => {
        attempt = 0;
        setConnected(true);
        setConnectionState("connected");
        setLastCloseCode(null);
        setLastCloseReason(null);
        setLastError(null);
        setReconnectAttempts(0);
        if (hasConnectedBefore) reconnectRef.current?.();
        hasConnectedBefore = true;
      };
      socket.onmessage = (msg) => {
        try {
          const parsed = JSON.parse(msg.data);
          if (parsed?.type && parsed.type !== "subscription_ack" && parsed.type !== "pong") {
            handlerRef.current(parsed);
          }
        } catch {
          /* ignore malformed frames */
        }
      };
      socket.onclose = (closeEvent) => {
        setConnected(false);
        if (closed) {
          setConnectionState("closed");
          return;
        }
        const code = typeof closeEvent?.code === "number" ? closeEvent.code : null;
        const reason = typeof closeEvent?.reason === "string" && closeEvent.reason.trim() ? closeEvent.reason.trim() : null;
        setLastCloseCode(code);
        setLastCloseReason(reason);

        if (isAuthFailureClose(code ?? undefined, reason ?? undefined)) {
          setConnectionState("auth_error");
          setLastError(
            hasToken
              ? `Realtime WebSocket authentication rejected (code ${code ?? "unknown"}).`
              : "Realtime WebSocket requires an authenticated session token.",
          );
          return;
        }
        schedule();
      };
      socket.onerror = () => {
        setLastError("Realtime WebSocket transport error");
        socket?.close();
      };
    };
    const schedule = () => {
      if (closed) return;
      attempt += 1;
      setReconnectAttempts(attempt);
      setConnectionState("reconnecting");
      timer = setTimeout(open, Math.min(15000, 800 * 2 ** Math.min(attempt, 5)));
    };
    open();
    return () => {
      closed = true;
      if (timer) clearTimeout(timer);
      socket?.close();
    };
  }, [key, enabled]);

  return {
    connected,
    connectionState,
    lastCloseCode,
    lastCloseReason,
    lastError,
    reconnectAttempts,
  };
}
