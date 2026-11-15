import { useCallback, useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import { api } from "@/lib/api";

const VISITOR_STORAGE_KEY = "gtex_public_visitor_v1";
const HEARTBEAT_INTERVAL_MS = 30_000;

function createVisitorId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  const bytes = new Uint8Array(16);
  if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
    crypto.getRandomValues(bytes);
    return Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
  }
  return `${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}`;
}

/**
 * Runs inside the canonical React Router so public, authenticated, and advertiser
 * routes all contribute page views. Only a random first-party visitor UUID and the
 * route pathname are sent; query strings, IP addresses, and browser fingerprints
 * are deliberately not collected by this tracker.
 */
export function PublicTrafficTracker() {
  const location = useLocation();
  const visitorIdRef = useRef<string | null>(null);

  const getVisitorId = useCallback((): string => {
    if (visitorIdRef.current) return visitorIdRef.current;

    let visitorId: string | null = null;
    try {
      visitorId = window.localStorage.getItem(VISITOR_STORAGE_KEY);
    } catch {
      // Storage may be disabled. Keep an in-memory ID for this page lifetime.
    }

    if (!visitorId) {
      visitorId = createVisitorId();
      try {
        window.localStorage.setItem(VISITOR_STORAGE_KEY, visitorId);
      } catch {
        // In-memory tracking still works for this page lifetime.
      }
    }

    visitorIdRef.current = visitorId;
    return visitorId;
  }, []);

  const sendHeartbeat = useCallback(
    (pageView: boolean) => {
      if (typeof document === "undefined" || document.visibilityState === "hidden") return;
      void api
        .post(
          "/public/traffic/heartbeat",
          {
            visitor_id: getVisitorId(),
            path: location.pathname || "/",
            page_view: pageView,
          },
          { timeout: 4_000 },
        )
        .catch(() => {
          // Public telemetry must never block navigation or the application shell.
        });
    },
    [getVisitorId, location.pathname],
  );

  useEffect(() => {
    sendHeartbeat(true);
  }, [sendHeartbeat]);

  useEffect(() => {
    const timer = window.setInterval(() => sendHeartbeat(false), HEARTBEAT_INTERVAL_MS);
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") sendHeartbeat(false);
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [sendHeartbeat]);

  return null;
}
