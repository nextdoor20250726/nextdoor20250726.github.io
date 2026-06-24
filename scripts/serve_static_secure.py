#!/usr/bin/env python
from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class SecureStaticHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "application/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".json": "application/json; charset=utf-8",
    }

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer-when-downgrade")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' https: data:; style-src 'self'; script-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'none'; object-src 'none'")
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description="Serve the static site with local security headers.")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", default=8001, type=int)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), SecureStaticHandler)
    print(f"Serving secure local preview at http://{args.host}:{args.port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
