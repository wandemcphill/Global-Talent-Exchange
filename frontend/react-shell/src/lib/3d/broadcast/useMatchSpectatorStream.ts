/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * useMatchSpectatorStream: Real-Time Spectator WebSocket Streaming Hook.
 *
 * Implements:
 * 1. Dedicated WebSocket transport connected to `/ws/spectate/{match_id}`.
 * 2. Strict read-only protocol enforcement (client can only send non-state-mutating reactions/chat).
 * 3. Exponential backoff auto-reconnection with automatic `/match-viewer/{id}` snapshot resynchronization.
 * 4. Deduplication and monotonic time ordering via StreamFrameDeduplicator.
 * 5. Live spectator presence metrics and connection state telemetry.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import {
  SpectatorSafeFrameView,
  SpectatorSafeEventView,
  StreamFrameDeduplicator,
  resolveCanonicalMatchKey,
} from "./spectatorContract";

export type SpectatorConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "error";

export interface SpectatorScoreUpdate {
  home_score: number;
  away_score: number;
  minute?: number;
  status?: string;
}

export interface UseMatchSpectatorStreamOptions {
  /** The match ID or canonical competition match ID */
  matchId: string;
  /** Whether the streaming connection should be active (defaults to true) */
  enabled?: boolean;
  /** Custom WebSocket URL override (useful for testing or dedicated edge relays) */
  wsUrl?: string;
  /** Optional viewer display name */
  displayName?: string;
  /** Optional short-lived, single-use, match-scoped spectator ticket (issued via POST /matches/{id}/spectate-ticket) */
  ticket?: string;
  /** Optional Max reconnection attempts before entering error state (default: 8) */
  maxReconnectAttempts?: number;
  /** Callback triggered when a new sanitized frame is received and verified */
  onFrameReceived?: (frame: SpectatorSafeFrameView) => void;
  /** Callback triggered when a new match event occurs */
  onEventReceived?: (event: SpectatorSafeEventView) => void;
  /** Callback triggered on score changes */
  onScoreUpdate?: (score: SpectatorScoreUpdate) => void;
  /** Callback triggered on viewer count changes */
  onViewerCountUpdate?: (viewerCount: number) => void;
  /** Callback triggered when connection recovers after a drop and a snapshot resync is required */
  onResyncRequired?: () => void;
}

export interface UseMatchSpectatorStreamResult {
  connectionStatus: SpectatorConnectionStatus;
  viewerCount: number;
  lastFrame: SpectatorSafeFrameView | null;
  recentEvents: SpectatorSafeEventView[];
  latestScore: SpectatorScoreUpdate | null;
  latencyMs: number;
  reconnectAttempts: number;
  sendReaction: (reaction: string) => boolean;
  sendChatMessage: (message: string) => boolean;
  reconnect: () => void;
  disconnect: () => void;
}

export function useMatchSpectatorStream(
  options: UseMatchSpectatorStreamOptions
): UseMatchSpectatorStreamResult {
  const {
    matchId,
    enabled = true,
    wsUrl,
    displayName,
    ticket,
    maxReconnectAttempts = 8,
    onFrameReceived,
    onEventReceived,
    onScoreUpdate,
    onViewerCountUpdate,
    onResyncRequired,
  } = options;

  const [connectionStatus, setConnectionStatus] = useState<SpectatorConnectionStatus>("disconnected");
  const [viewerCount, setViewerCount] = useState<number>(0);
  const [lastFrame, setLastFrame] = useState<SpectatorSafeFrameView | null>(null);
  const [recentEvents, setRecentEvents] = useState<SpectatorSafeEventView[]>([]);
  const [latestScore, setLatestScore] = useState<SpectatorScoreUpdate | null>(null);
  const [latencyMs, setLatencyMs] = useState<number>(0);
  const [reconnectAttempts, setReconnectAttempts] = useState<number>(0);

  const socketRef = useRef<WebSocket | null>(null);
  const deduplicatorRef = useRef<StreamFrameDeduplicator>(new StreamFrameDeduplicator());
  const reconnectTimerRef = useRef<any>(null);
  const pingTimerRef = useRef<any>(null);
  const pingTimestampRef = useRef<number>(0);
  const attemptsRef = useRef<number>(0);
  const manualDisconnectRef = useRef<boolean>(false);
  const isReconnectingRef = useRef<boolean>(false);

  // Keep callback refs fresh to avoid reconnect churn
  const onFrameRef = useRef(onFrameReceived);
  onFrameRef.current = onFrameReceived;
  const onEventRef = useRef(onEventReceived);
  onEventRef.current = onEventReceived;
  const onScoreRef = useRef(onScoreUpdate);
  onScoreRef.current = onScoreUpdate;
  const onViewerCountRef = useRef(onViewerCountUpdate);
  onViewerCountRef.current = onViewerCountUpdate;
  const onResyncRef = useRef(onResyncRequired);
  onResyncRef.current = onResyncRequired;

  // Resolve Canonical Match Key
  const canonicalId = resolveCanonicalMatchKey(matchId);

  // Build the target WebSocket URL (strictly forbids bearer tokens in query parameters)
  const resolveTargetWsUrl = useCallback(() => {
    if (wsUrl) {
      try {
        const parsed = new URL(wsUrl);
        parsed.searchParams.delete("token");
        parsed.searchParams.delete("access_token");
        parsed.searchParams.delete("bearer");
        if (displayName && !parsed.searchParams.has("display_name")) {
          parsed.searchParams.set("display_name", displayName);
        }
        if (ticket) {
          parsed.searchParams.set("ticket", ticket);
        }
        return parsed.toString();
      } catch {
        return wsUrl.replace(/([?&])(token|access_token|bearer)=[^&]*(&|$)/gi, "$1").replace(/[?&]$/, "");
      }
    }
    if (typeof window === "undefined") return "";

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const url = new URL(`${protocol}//${host}/ws/spectate/${encodeURIComponent(canonicalId || matchId)}`);

    if (displayName) {
      url.searchParams.set("display_name", displayName);
    }
    if (ticket) {
      url.searchParams.set("ticket", ticket);
    }
    return url.toString();
  }, [wsUrl, canonicalId, matchId, displayName, ticket]);

  // Clean disconnect
  const cleanupSocket = useCallback(() => {
    if (pingTimerRef.current) {
      clearInterval(pingTimerRef.current);
      pingTimerRef.current = null;
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (socketRef.current) {
      try {
        socketRef.current.onopen = null;
        socketRef.current.onclose = null;
        socketRef.current.onerror = null;
        socketRef.current.onmessage = null;
        socketRef.current.close();
      } catch {
        // Suppress close exceptions on already closing socket
      }
      socketRef.current = null;
    }
  }, []);

  // Connect function
  const connect = useCallback(() => {
    cleanupSocket();
    if (!enabled || !matchId) {
      setConnectionStatus("disconnected");
      return;
    }

    const targetUrl = resolveTargetWsUrl();
    if (!targetUrl) return;

    manualDisconnectRef.current = false;
    setConnectionStatus(attemptsRef.current > 0 ? "reconnecting" : "connecting");

    try {
      const ws = new WebSocket(targetUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        setConnectionStatus("connected");
        const wasReconnect = isReconnectingRef.current;
        isReconnectingRef.current = false;
        attemptsRef.current = 0;
        setReconnectAttempts(0);

        // If this is a recovery connection after dropped frames, request a snapshot resync
        if (wasReconnect && onResyncRef.current) {
          onResyncRef.current();
        }

        // Setup ping/heartbeat loop every 15 seconds to measure round-trip latency
        pingTimerRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            pingTimestampRef.current = Date.now();
            ws.send(JSON.stringify({ type: "ping" }));
          }
        }, 15000);
      };

      ws.onmessage = (event) => {
        try {
          const data = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
          if (!data || typeof data !== "object") return;

          // Latency measurement for pong / heartbeat
          if (data.type === "pong" || data.type === "heartbeat") {
            if (pingTimestampRef.current > 0) {
              const rtt = Math.max(0, Date.now() - pingTimestampRef.current);
              setLatencyMs(rtt);
            }
            return;
          }

          // Handle Snapshot event
          if (data.type === "snapshot" && data.snapshot) {
            const count = Number(data.snapshot.viewer_count) || 0;
            setViewerCount(count);
            if (onViewerCountRef.current) {
              onViewerCountRef.current(count);
            }
            if (data.snapshot.score_update) {
              const sc: SpectatorScoreUpdate = {
                home_score: Number(data.snapshot.score_update.home_score) || 0,
                away_score: Number(data.snapshot.score_update.away_score) || 0,
                minute: data.snapshot.score_update.minute,
                status: data.snapshot.score_update.status,
              };
              setLatestScore(sc);
              if (onScoreRef.current) onScoreRef.current(sc);
            }
          }

          // Handle viewer_count event
          if (data.type === "viewer_count") {
            const count =
              data.snapshot?.viewer_count ??
              data.payload?.viewer_count ??
              data.payload?.active_viewers ??
              0;
            setViewerCount(Number(count) || 0);
            if (onViewerCountRef.current) {
              onViewerCountRef.current(Number(count) || 0);
            }
          }

          // Handle score_update event
          if (data.type === "score_update" || data.score_update) {
            const src = data.score_update || data.payload || {};
            const sc: SpectatorScoreUpdate = {
              home_score: Math.max(0, Number(src.home_score) || 0),
              away_score: Math.max(0, Number(src.away_score) || 0),
              minute: src.minute != null ? Number(src.minute) : undefined,
              status: src.status ? String(src.status) : undefined,
            };
            setLatestScore(sc);
            if (onScoreRef.current) {
              onScoreRef.current(sc);
            }
          }

          // Handle frame stream
          const candidateFrame =
            data.payload?.frame ||
            (data.payload?.frame_id ? data.payload : null) ||
            data.frame ||
            (data.frame_id ? data : null);

          if (candidateFrame && candidateFrame.frame_id) {
            const processed = deduplicatorRef.current.process(candidateFrame as SpectatorSafeFrameView);
            if (processed) {
              setLastFrame(processed);
              if (onFrameRef.current) {
                onFrameRef.current(processed);
              }
            }
          }

          // Handle event stream (goals, cards, VAR, substitutions)
          const candidateEvent =
            data.payload?.event ||
            (data.payload?.event_id ? data.payload : null) ||
            data.event ||
            (data.event_id ? data : null);

          if (candidateEvent && candidateEvent.event_id) {
            const ev = candidateEvent as SpectatorSafeEventView;
            setRecentEvents((prev) => [ev, ...prev].slice(0, 20));
            if (onEventRef.current) {
              onEventRef.current(ev);
            }
          }
        } catch {
          // Suppress parsing anomalies on corrupted frames
        }
      };

      ws.onerror = () => {
        // Handled in onclose
      };

      ws.onclose = () => {
        cleanupSocket();
        if (manualDisconnectRef.current) {
          setConnectionStatus("disconnected");
          return;
        }

        isReconnectingRef.current = true;
        attemptsRef.current += 1;
        setReconnectAttempts(attemptsRef.current);

        if (attemptsRef.current <= maxReconnectAttempts) {
          setConnectionStatus("reconnecting");
          // Exponential backoff: 1s, 2s, 4s, 8s, up to 15s max
          const delayMs = Math.min(15000, Math.pow(2, attemptsRef.current - 1) * 1000);
          reconnectTimerRef.current = setTimeout(() => {
            connect();
          }, delayMs);
        } else {
          setConnectionStatus("error");
        }
      };
    } catch {
      setConnectionStatus("error");
    }
  }, [enabled, matchId, resolveTargetWsUrl, cleanupSocket, maxReconnectAttempts]);

  // Connect on mount or when dependencies change
  useEffect(() => {
    connect();
    return () => {
      manualDisconnectRef.current = true;
      cleanupSocket();
    };
  }, [connect, cleanupSocket]);

  // Client non-mutating broadcast actions
  const sendReaction = useCallback((reaction: string): boolean => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: "reaction",
          reaction: String(reaction).slice(0, 32),
        })
      );
      return true;
    }
    return false;
  }, []);

  const sendChatMessage = useCallback((message: string): boolean => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: "chat_message",
          message: String(message).slice(0, 280),
        })
      );
      return true;
    }
    return false;
  }, []);

  const manualReconnect = useCallback(() => {
    isReconnectingRef.current = true;
    attemptsRef.current = 0;
    setReconnectAttempts(0);
    connect();
  }, [connect]);

  const manualDisconnect = useCallback(() => {
    manualDisconnectRef.current = true;
    cleanupSocket();
    setConnectionStatus("disconnected");
  }, [cleanupSocket]);

  return {
    connectionStatus,
    viewerCount,
    lastFrame,
    recentEvents,
    latestScore,
    latencyMs,
    reconnectAttempts,
    sendReaction,
    sendChatMessage,
    reconnect: manualReconnect,
    disconnect: manualDisconnect,
  };
}
