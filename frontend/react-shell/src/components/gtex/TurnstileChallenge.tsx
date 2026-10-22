import React, { useEffect, useRef, useState } from "react";

declare global {
  interface Window {
    turnstile?: {
      render: (container: HTMLElement, options: Record<string, unknown>) => string;
      remove: (widgetId: string) => void;
    };
  }
}

export const TURNSTILE_SITE_KEY = String(
  process.env.REACT_APP_GTE_TURNSTILE_SITE_KEY || "",
).trim();

export function TurnstileChallenge({
  onTokenChange,
}: {
  onTokenChange: (token: string | null) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const [widgetError, setWidgetError] = useState("");

  useEffect(() => {
    if (!TURNSTILE_SITE_KEY) {
      onTokenChange(null);
      return;
    }

    let disposed = false;
    let widgetId: string | null = null;
    let script = document.getElementById("gtex-turnstile-script") as HTMLScriptElement | null;

    const render = () => {
      if (disposed || !container.current || !window.turnstile) return;
      try {
        widgetId = window.turnstile.render(container.current, {
          sitekey: TURNSTILE_SITE_KEY,
          theme: "dark",
          callback: (token: string) => {
            if (disposed) return;
            setWidgetError("");
            onTokenChange(token);
          },
          "expired-callback": () => {
            if (!disposed) onTokenChange(null);
          },
          "error-callback": () => {
            if (disposed) return;
            onTokenChange(null);
            setWidgetError("The security check could not be completed. Refresh the challenge and try again.");
          },
        });
      } catch {
        onTokenChange(null);
        setWidgetError("The security check could not be loaded. Please refresh and try again.");
      }
    };

    const handleLoad = () => {
      if (window.turnstile) render();
      else setWidgetError("The security service did not initialise. Please refresh and try again.");
    };
    const handleError = () => {
      if (!disposed) {
        onTokenChange(null);
        setWidgetError("The security service could not be reached. Check your connection and try again.");
      }
    };

    if (window.turnstile) {
      render();
    } else {
      if (!script) {
        script = document.createElement("script");
        script.id = "gtex-turnstile-script";
        script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
        script.async = true;
        script.defer = true;
        document.head.appendChild(script);
      }
      script.addEventListener("load", handleLoad);
      script.addEventListener("error", handleError);
    }

    return () => {
      disposed = true;
      script?.removeEventListener("load", handleLoad);
      script?.removeEventListener("error", handleError);
      if (widgetId && window.turnstile) window.turnstile.remove(widgetId);
    };
  }, [onTokenChange]);

  if (!TURNSTILE_SITE_KEY) return null;

  return (
    <div className="space-y-2" data-testid="signup-turnstile">
      <p className="gx-label">Security check</p>
      <div ref={container} className="min-h-[65px]" />
      {widgetError && <p role="alert" className="text-xs text-red-300">{widgetError}</p>}
    </div>
  );
}
