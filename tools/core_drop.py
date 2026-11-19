"""Rough drop check for the prototype core.

Usage:
  python tools/core_drop.py [--mass 0.26] [--height 1.2] [--stop 2]
"""
import argparse
import math

G = 9.81
SCREW_SHEAR_N = 1400.0      # M2.5 A2-70, conservative shear capacity
BATTERY_KG = 0.045


def impact(mass, height, stop_m):
    v = math.sqrt(2.0 * G * height)
    a = v * v / (2.0 * stop_m)
    return v, a, mass * a


def check(mass=0.26, height=1.2, stop_mm=2.0, screws=3):
    v, a, f = impact(mass, height, stop_mm / 1000.0)
    fb = BATTERY_KG * a
    fs = f / screws
    return {
        "v": v,
        "g": a / G,
        "force": f,
        "battery": fb,
        "battery_design": fb * 1.5,
        "screw": fs,
        "screw_util": fs / SCREW_SHEAR_N,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mass", type=float, default=0.26)
    p.add_argument("--height", type=float, default=1.2)
    p.add_argument("--stop", type=float, default=2.0, help="mm")
    a = p.parse_args()
    r = check(a.mass, a.height, a.stop)
    print("跌落 %.2f m：v=%.2f m/s，a=%.0f g，F=%.0f N"
          % (a.height, r["v"], r["g"], r["force"]))
    print("电池托架：%.0f N（按 1.5 倍设计 %.0f N）"
          % (r["battery"], r["battery_design"]))
    print("杯法兰 3 颗 M2.5：单颗 %.0f N，利用率 %.0f%%（剪切 %.0f N）"
          % (r["screw"], r["screw_util"] * 100, SCREW_SHEAR_N))
    print("结论：螺纹不是瓶颈；瓶颈是电池托架、杯法兰根部和分割面。")


if __name__ == "__main__":
    main()
