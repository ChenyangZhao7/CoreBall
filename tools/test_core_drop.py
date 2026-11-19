import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core_drop as D


def near(a, b, tol, msg):
    if abs(a - b) > tol:
        raise SystemExit("FAIL: %s (%r vs %r)" % (msg, a, b))


r = D.check()
near(r["v"], 4.85, 0.01, "落地速度")
near(r["g"], 600, 1, "冲击 g")
near(r["force"], 1530, 2, "总冲击力")
near(r["battery"], 265, 2, "电池托架")
near(r["screw_util"], 0.36, 0.01, "M2.5 利用率")
if r["screw_util"] > 0.6:
    raise SystemExit("FAIL: 螺纹利用率过高")

print("PASS")
