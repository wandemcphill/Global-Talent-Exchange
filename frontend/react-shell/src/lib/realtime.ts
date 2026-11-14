import { useEffect, useRef, useState } from "react";
import { API, tokens } from "@/lib/api";

function wsUrl(topics: string[]): string {
  const origin = API.replace(/\/api$/, "");
  const base = origin.replace(/^http/, "ws");
  const params = new URLSearchParams();
  topics.forEach((t) => params.append("topic", t));
  const token = tokens.get();
  if (token) params.set("token", token);
  return `${base}/realtime/stream?${params.toString()}`;
}

export type RealtimeEvent = { type: string; data: any };

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
  const handlerRef = useRef(onEvent);
  const reconnectRef = useRef(onReconnect);
  handlerRef.current = onEvent;
  reconnectRef.current = onReconnect;
  const key = topics.join("|");

  useEffect(() => {
    if (!enabled || topics.length === 0 || typeof WebSocket === "undefined") return;
    let socket: WebSocket | null = null;
    let closed = false;
    let attempt = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let hasConnectedBefore = false;

    const open = () => {
      if (closed) return;
      try {
        socket = new WebSocket(wsUrl(topics));
      } catch {
        schedule();
        return;
      }
      socket.onopen = () => {
        attempt = 0;
        setConnected(true);
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
      socket.onclose = () => {
        setConnected(false);
        schedule();
      };
      socket.onerror = () => socket?.close();
    };
    const schedule = () => {
      if (closed) return;
      attempt += 1;
      timer = setTimeout(open, Math.min(15000, 800 * 2 ** Math.min(attempt, 5)));
    };
    open();
    return () => {
      closed = true;
      if (timer) clearTimeout(timer);
      socket?.close();
    };
  }, [key, enabled]);

  return { connected };
}
