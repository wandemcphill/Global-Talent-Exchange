/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * useMatchSpectatorStream: Real-Time Spectator WebSocket Streaming Hook.
 *
 * Implements:
 * 1. Dedicated WebSocket transport connected to `/ws/spectate/{match_id}`.
 * 2. Asynchronous single-use, match-scoped ticket lifecycle (`requestTicket`) for authenticated viewers
 *    with strict anti-downgrade, anti-replay, and concurrent reconnect race protection.
 * 3. Strict read-only protocol enforcement (client can only send non-state-mutating reactions/chat).
 * 4. Exponential backoff auto-reconnection with automatic `/match-viewer/{id}` snapshot resynchronization.
 * 5. Deduplication and monotonic time ordering via StreamFrameDeduplicator.
 * 6. Live spectator presence metrics and connection state telemetry.
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
  /** Whether the current viewer is authenticated (determines whether a ticket is mandatory) */
  isAuthenticated?: boolean;
  /**
   * Asynchronous ticket provider invoked immediately before each authenticated connection
   * and each reconnect attempt (e.g. calling `POST /matches/{match_id}/spectate-ticket`).
   */
  requestTicket?: (matchId: string) => Promise<string | null>;
  /** Max reconnection attempts before entering error state (default: 8) */
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
  /** Callback triggered when a gift event is broadcast across the match spectator stream */
  onGiftReceived?: (gift: any) => void;
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

const FORBIDDEN_URL_TOKEN_KEYS = new Set([
  "token",
  "access_token",
  "accesstoken",
  "bearer",
  "auth_token",
  "authtoken",
  "authorization",
  "jwt",
]);

function stripForbiddenUrlParameters(url: URL): void {
  const keys = Array.from(url.searchParams.keys());
  for (const key of keys) {
    if (FORBIDDEN_URL_TOKEN_KEYS.has(key.trim().toLowerCase())) {
      url.searchParams.delete(key);
    }
  }
}

export function useMatchSpectatorStream(
  options: UseMatchSpectatorStreamOptions
): UseMatchSpectatorStreamResult {
  const {
    matchId,
    enabled = true,
    wsUrl,
    displayName,
    isAuthenticated,
    requestTicket,
    maxReconnectAttempts = 8,
    onFrameReceived,
    onEventReceived,
    onScoreUpdate,
    onViewerCountUpdate,
    onResyncRequired,
    onGiftReceived,
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

  // Concurrency and single-use ticket tracking with operation-scoped fetch tracking
  const connectSeqRef = useRef<number>(0);
  const activeTicketFetchOpIdRef = useRef<number | null>(null);
  const consumedTicketsRef = useRef<Set<string>>(new Set());

  // Keep callback refs fresh to avoid reconnect churn
  const requestTicketRef = useRef(requestTicket);
  requestTicketRef.current = requestTicket;
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
  const onGiftRef = useRef(onGiftReceived);
  onGiftRef.current = onGiftReceived;

  // Resolve Canonical Match Key
  const canonicalId = resolveCanonicalMatchKey(matchId);

  // Build the target WebSocket URL with case-insensitive bearer token stripping
  const buildTargetWsUrl = useCallback(
    (activeTicket: string | null): string => {
      if (wsUrl) {
        try {
          const parsed = new URL(wsUrl);
          stripForbiddenUrlParameters(parsed);
          parsed.searchParams.delete("ticket");
          if (displayName && !parsed.searchParams.has("display_name")) {
            parsed.searchParams.set("display_name", displayName);
          }
          if (activeTicket) {
            parsed.searchParams.set("ticket", activeTicket);
          }
          return parsed.toString();
        } catch {
          const cleaned = wsUrl
            .replace(/([?&])(token|access_token|accesstoken|bearer|auth_token|authtoken|authorization|jwt)=[^&]*(&|$)/gi, "$1")
            .replace(/[?&]$/, "");
          if (!activeTicket) return cleaned;
          const sep = cleaned.includes("?") ? "&" : "?";
          return `${cleaned}${sep}ticket=${encodeURIComponent(activeTicket)}`;
        }
      }
      if (typeof window === "undefined") return "";

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.host;
      const url = new URL(`${protocol}//${host}/ws/spectate/${encodeURIComponent(canonicalId || matchId)}`);

      if (displayName) {
        url.searchParams.set("display_name", displayName);
      }
      if (activeTicket) {
        url.searchParams.set("ticket", activeTicket);
      }
      return url.toString();
    },
    [wsUrl, canonicalId, matchId, displayName]
  );

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

  // Connect function with async single-use ticket acquisition & concurrency guard
  const connect = useCallback(
    async (fromManualReconnect: boolean = false) => {
      if (!enabled || !matchId) {
        cleanupSocket();
        setConnectionStatus("disconnected");
        return;
      }

      // Prevent concurrent reconnect operations from racing to acquire/consume tickets
      if (activeTicketFetchOpIdRef.current !== null && !fromManualReconnect) {
        return;
      }

      cleanupSocket();
      const opId = ++connectSeqRef.current;
      manualDisconnectRef.current = false;
      setConnectionStatus(attemptsRef.current > 0 || isReconnectingRef.current ? "reconnecting" : "connecting");

      const requiresAuthenticatedTicket =
        isAuthenticated === true || (isAuthenticated !== false && Boolean(requestTicketRef.current));

      let activeTicket: string | null = null;
      if (requiresAuthenticatedTicket) {
        if (!requestTicketRef.current) {
          // Authenticated user without a ticket provider must fail closed, never downgrade to guest
          setConnectionStatus("error");
          return;
        }
        activeTicketFetchOpIdRef.current = opId;
        try {
          const issued = await requestTicketRef.current(canonicalId || matchId);
          if (activeTicketFetchOpIdRef.current === opId) {
            activeTicketFetchOpIdRef.current = null;
          }

          // Abort if superseded by a newer connect/disconnect while awaiting ticket
          if (opId !== connectSeqRef.current || manualDisconnectRef.current) {
            return;
          }

          const trimmedTicket = typeof issued === "string" ? issued.trim() : "";
          if (!trimmedTicket || consumedTicketsRef.current.has(trimmedTicket)) {
            // Do not silently downgrade failed or replayed ticket to guest authentication
            setConnectionStatus("error");
            return;
          }
          consumedTicketsRef.current.add(trimmedTicket);
          activeTicket = trimmedTicket;
        } catch {
          if (activeTicketFetchOpIdRef.current === opId) {
            activeTicketFetchOpIdRef.current = null;
          }
          if (opId !== connectSeqRef.current || manualDisconnectRef.current) {
            return;
          }
          // Failed authenticated ticket request must fail closed without guest downgrade
          setConnectionStatus("error");
          return;
        }
      }

      if (opId !== connectSeqRef.current || manualDisconnectRef.current) {
        return;
      }

      const targetUrl = buildTargetWsUrl(activeTicket);
      if (!targetUrl) return;

      try {
        const ws = new WebSocket(targetUrl);
        socketRef.current = ws;

        ws.onopen = () => {
          if (opId !== connectSeqRef.current) return;
          setConnectionStatus("connected");
          const wasReconnect = isReconnectingRef.current;
          isReconnectingRef.current = false;
          attemptsRef.current = 0;
          setReconnectAttempts(0);

          if (wasReconnect && onResyncRef.current) {
            onResyncRef.current();
          }

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

            if (data.type === "pong" || data.type === "heartbeat") {
              if (pingTimestampRef.current > 0) {
                const rtt = Math.max(0, Date.now() - pingTimestampRef.current);
                setLatencyMs(rtt);
              }
              return;
            }

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

            if (
              data.type === "gift_broadcast" ||
              data.type === "gift_animation" ||
              data.event_type === "gift_broadcast" ||
              data.topic === "match_gift" ||
              data.gift ||
              data.payload?.gift_id ||
              data.payload?.gift_key
            ) {
              const giftPayload = data.payload || data.data || data;
              if (onGiftRef.current) {
                onGiftRef.current(giftPayload);
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
          if (manualDisconnectRef.current || opId !== connectSeqRef.current) {
            if (manualDisconnectRef.current) {
              setConnectionStatus("disconnected");
            }
            return;
          }

          isReconnectingRef.current = true;
          attemptsRef.current += 1;
          setReconnectAttempts(attemptsRef.current);

          if (attemptsRef.current <= maxReconnectAttempts) {
            setConnectionStatus("reconnecting");
            const delayMs = Math.min(15000, Math.pow(2, attemptsRef.current - 1) * 1000);
            reconnectTimerRef.current = setTimeout(() => {
              void connect(false);
            }, delayMs);
          } else {
            setConnectionStatus("error");
          }
        };
      } catch {
        setConnectionStatus("error");
      }
    },
    [enabled, matchId, canonicalId, isAuthenticated, buildTargetWsUrl, cleanupSocket, maxReconnectAttempts]
  );

  // Connect on mount or when dependencies change
  useEffect(() => {
    void connect(false);
    return () => {
      manualDisconnectRef.current = true;
      connectSeqRef.current += 1;
      activeTicketFetchOpIdRef.current = null;
      cleanupSocket();
    };
  }, [connect, cleanupSocket]);

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
    if (activeTicketFetchOpIdRef.current !== null) {
      return;
    }
    isReconnectingRef.current = true;
    attemptsRef.current = 0;
    setReconnectAttempts(0);
    void connect(true);
  }, [connect]);

  const manualDisconnect = useCallback(() => {
    manualDisconnectRef.current = true;
    connectSeqRef.current += 1;
    activeTicketFetchOpIdRef.current = null;
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
