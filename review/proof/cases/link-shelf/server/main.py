import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import shelf
import version_check

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(HERE, "static")
PORT = int(os.environ.get("PORT") or os.environ.get("LOAM_PLUGIN_PORT") or "9100")

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript",
    ".css": "text/css",
    ".svg": "image/svg+xml",
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _static(self, path):
        rel = path.lstrip("/") or "index.html"
        full = os.path.normpath(os.path.join(STATIC_DIR, rel))
        if not (full == STATIC_DIR or full.startswith(STATIC_DIR + os.sep)) or not os.path.isfile(full):
            self.send_error(404)
            return
        ext = os.path.splitext(full)[1]
        with open(full, "rb") as handle:
            data = handle.read()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/links":
            self._json(200, {"links": shelf.all_links()})
        elif parsed.path == "/api/search":
            query = parse_qs(parsed.query).get("q", [""])[0]
            self._json(200, {"links": shelf.search(query)})
        else:
            self._static(parsed.path)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except ValueError:
            return {}

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/links":
            self.send_error(404)
            return
        data = self._body()
        url = (data.get("url") or "").strip()
        if not url:
            self._json(400, {"error": "a link needs a url"})
            return
        title = (data.get("title") or url).strip()
        link = shelf.add_link(url, title, data.get("tags") or [])
        self._json(200, {"link": link})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        parts = parsed.path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "links":
            ok = shelf.remove_link(parts[2])
            self._json(200 if ok else 404, {"removed": ok})
        else:
            self.send_error(404)


def main():
    worker = threading.Thread(target=version_check.run_forever, daemon=True)
    worker.start()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
