#!/usr/bin/env python3
"""
GTEX Local Frontend & Showcase Server
Serves the Flutter Web Application and Showcase Landing Page with proper MIME types
and SPA history fallback.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
import urllib.parse

REPO_ROOT = Path(__file__).resolve().parents[1]
FLUTTER_WEB_ROOT = REPO_ROOT / "frontend" / "build" / "web"
REACT_WEB_ROOT = REPO_ROOT / "frontend" / "react-shell" / "build"
SHOWCASE_ROOT = REPO_ROOT


class GtexHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        "": "application/octet-stream",
        ".js": "application/javascript",
        ".mjs": "application/javascript",
        ".wasm": "application/wasm",
        ".json": "application/json",
        ".css": "text/css",
        ".html": "text/html; charset=utf-8",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".ico": "image/x-icon",
        ".ttf": "font/ttf",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
    }

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def translate_path(self, path: str) -> str:
        parsed = urllib.parse.urlsplit(path)
        decoded_path = urllib.parse.unquote(parsed.path)

        # Route /console to React Shell build
        if decoded_path.startswith("/console"):
            rel = decoded_path.replace("/console", "", 1).lstrip("/")
            if not rel:
                target = REACT_WEB_ROOT / "index.html"
            else:
                target = REACT_WEB_ROOT / rel
            if target.exists() and not target.is_dir():
                return str(target)
            return str(REACT_WEB_ROOT / "index.html")

        # Route React static build assets
        if decoded_path.startswith("/static/") or decoded_path.startswith("/branding/") or decoded_path.startswith("/img/"):
            rel = decoded_path.lstrip("/")
            target = REACT_WEB_ROOT / rel
            if target.exists():
                return str(target)

        # Route /landing or /showcase to repository root
        if decoded_path.startswith("/landing") or decoded_path.startswith("/showcase"):
            rel = decoded_path.replace("/landing", "", 1).replace("/showcase", "", 1).lstrip("/")
            if not rel:
                target = SHOWCASE_ROOT / "index.html"
            else:
                target = SHOWCASE_ROOT / rel
            if target.exists():
                return str(target)
            return str(SHOWCASE_ROOT / "index.html")

        # Otherwise serve from Flutter Web root (or React fallback if not built)
        default_root = FLUTTER_WEB_ROOT if (FLUTTER_WEB_ROOT / "index.html").exists() else REACT_WEB_ROOT
        rel = decoded_path.lstrip("/")
        if not rel:
            return str(default_root / "index.html")

        target = default_root / rel
        if target.exists():
            return str(target)

        # SPA fallback for Flutter routes: if path has no file extension, return index.html
        if "." not in os.path.basename(rel):
            return str(default_root / "index.html")

        return str(target)


def run_server(port: int = 3000, host: str = "127.0.0.1") -> None:
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, GtexHandler)
    print(f"GTEX Frontend Server running at http://{host}:{port}/")
    print(f" - Flutter Web App:    http://{host}:{port}/")
    print(f" - Showcase & Landing: http://{host}:{port}/landing")
    print(f" - Backend API:        http://127.0.0.1:8000/docs")
    sys.stdout.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    run_server(port=port)
