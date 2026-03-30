#!/usr/bin/env python3
"""Yerel test sayfası. Varsayılan port 8765; doluysa sıradaki boş port kullanılır."""

import errno
import os
import sys
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT_START = int(os.environ.get("PORT", "8765"))
ROOT = os.path.dirname(os.path.abspath(__file__))
MAX_TRY = 30


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def log_message(self, format, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))


class ReuseHTTPServer(HTTPServer):
    allow_reuse_address = True


def main() -> None:
    os.chdir(ROOT)
    server = None
    chosen = None
    for port in range(PORT_START, PORT_START + MAX_TRY):
        try:
            server = ReuseHTTPServer(("127.0.0.1", port), Handler)
            chosen = port
            break
        except OSError as e:
            if e.errno != errno.EADDRINUSE:
                raise
            continue
    if server is None or chosen is None:
        print(
            f"Boş port bulunamadı ({PORT_START}–{PORT_START + MAX_TRY - 1}).\n"
            "Çalışan süreci kapat:  lsof -ti :8765 | xargs kill -9",
            file=sys.stderr,
        )
        sys.exit(1)

    url = f"http://127.0.0.1:{chosen}/"
    if chosen != PORT_START:
        print(
            f"\n  Not: {PORT_START} meşgul, port {chosen} kullanılıyor.\n",
            file=sys.stderr,
        )
    print(f"\n  TRIBE web arayüzü: {url}\n  Durdurmak için: Ctrl+C\n")
    try:
        webbrowser.open(url)
    except Exception:
        print("  Tarayıcıyı elle aç: yukarıdaki adresi kopyala.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Kapatıldı.")


if __name__ == "__main__":
    main()
