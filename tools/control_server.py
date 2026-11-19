"""Local bridge for the 2D/3D control page.

Serves web/ and forwards POST /intent to the Blender command scene over UDP
(127.0.0.1:4590). Browsers cannot send UDP directly, hence this bridge.

Usage:
  python tools/control_server.py
  # then open http://127.0.0.1:8010/
"""
import json
import os
import socket
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
UDP_ADDR = ("127.0.0.1", 4590)
PORT = 8010


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB, **kwargs)

    def do_GET(self):
        if self.path == "/":
            self.path = "/control.html"
        return super().do_GET()

    def do_POST(self):
        if self.path != "/intent":
            self.send_error(404)
            return
        try:
            n = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(n)
            json.loads(raw.decode("utf-8"))       # validate only
        except Exception:
            self.send_error(400, "bad json")
            return
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.sendto(raw, UDP_ADDR)
            s.close()
        except OSError as e:
            self.send_error(503, "udp: %s" % e)
            return
        self.send_response(204)
        self.end_headers()

    def log_message(self, fmt, *args):
        print("[control] " + fmt % args)


if __name__ == "__main__":
    print("CoreBall control: http://127.0.0.1:%d/  -> UDP %s" %
          (PORT, UDP_ADDR))
    with ThreadingHTTPServer(("127.0.0.1", PORT), Handler) as http:
        http.serve_forever()
