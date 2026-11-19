import http.client
import json
import os
import socket
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import control_server as C


def eq(a, b, msg):
    if a != b:
        raise SystemExit("FAIL: %s (%r != %r)" % (msg, a, b))


C.UDP_ADDR = ("127.0.0.1", 4599)
srv = C.ThreadingHTTPServer(("127.0.0.1", 8011), C.Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()

udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp.bind(C.UDP_ADDR)
udp.settimeout(2)

http = http.client.HTTPConnection("127.0.0.1", 8011)
http.request("POST", "/intent",
             body=json.dumps({"intent": "goto", "point": [1, 2, 3]}),
             headers={"Content-Type": "application/json"})
r = http.getresponse()
eq(r.status, 204, "POST 状态")
data, _ = udp.recvfrom(2048)
eq(json.loads(data.decode())["intent"], "goto", "UDP 内容")

http.request("GET", "/")
r = http.getresponse()
eq(r.status, 200, "首页状态")
if b"CoreBall" not in r.read():
    raise SystemExit("FAIL: 首页不是控制台")

srv.shutdown()
udp.close()
print("PASS")
