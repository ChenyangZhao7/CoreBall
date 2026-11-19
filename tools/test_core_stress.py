import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core_stress as S


def near(a, b, tol, msg):
    if abs(a - b) > tol:
        raise SystemExit("FAIL: %s (%r vs %r)" % (msg, a, b))


r = S.check()
near(r["cup"], 28.3, 0.5, "杯壁根部")
near(r["cup_kt"], 56.6, 1.0, "杯壁根部含 Kt")
near(r["pcr"], 11850, 100, "柱屈曲")
near(r["ring"], 90.3, 1.0, "环弯曲")
near(r["bearing_washer"], 10.7, 0.5, "壳体垫圈")
near(r["bearing_bare"], 50.0, 0.5, "壳体无垫圈")

if r["cup_sf"] < 2 or r["pcr_sf"] < 5 or r["ring_sf"] < 2:
    raise SystemExit("FAIL: 主结构余量不足")
if r["bearing_washer_sf"] < 3:
    raise SystemExit("FAIL: 加垫圈后壳体仍不够")
if r["bearing_bare_sf"] > 2:
    raise SystemExit("FAIL: 无垫圈工况没有暴露问题")

print("PASS")
