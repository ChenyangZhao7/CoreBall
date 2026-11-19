"""Analytical pre-check of the prototype core under a 1.2 m drop.

This is NOT FEA: it is a beam/plate screening model. Use it to find the
weak link before spending time on a real solver or a drop sample.

Usage:
  python tools/core_stress.py
"""
import math

Y_6061 = 276.0     # MPa, 6061-T6
Y_PC = 60.0        # MPa, PC/ABS, conservative


def cup_root(F=1500.0, r_wall=15.8, r_support=14.0, t=2.4, Kt=2.0):
    """Annular floor between the cup wall and the 3 column supports."""
    M = F * (r_wall - r_support) / (2.0 * math.pi * r_wall)   # N·mm/mm
    W = t * t / 6.0                                            # mm³/mm
    nominal = M / W
    return nominal, nominal * Kt


def column_buckling(F=500.0, d=5.0, L=42.0, E=69000.0):
    I = math.pi * d ** 4 / 64.0
    Pcr = math.pi ** 2 * E * I / (L * L)
    return Pcr, Pcr / F


def ring_bending(F=500.0, span=65.0, width=7.5, height=6.0):
    I = height ** 3 * width / 12.0
    M = F * span / 8.0
    return M * (height / 2.0) / I


def shell_bearing(F=250.0, d=2.5, t=2.0, washer=6.0):
    """Screw clamp load into the 2 mm PC shell, with and without a washer."""
    with_washer = F / (math.pi / 4.0 * (washer ** 2 - d ** 2))
    without = F / (d * t)
    return with_washer, without


def check():
    cup_nom, cup_kt = cup_root()
    pcr, pcr_sf = column_buckling()
    ring = ring_bending()
    bear_w, bear_n = shell_bearing()
    return {
        "cup": cup_nom,
        "cup_kt": cup_kt,
        "cup_sf": Y_6061 / cup_kt,
        "pcr": pcr,
        "pcr_sf": pcr_sf,
        "ring": ring,
        "ring_sf": Y_6061 / ring,
        "bearing_washer": bear_w,
        "bearing_washer_sf": Y_PC / bear_w,
        "bearing_bare": bear_n,
        "bearing_bare_sf": Y_PC / bear_n,
    }


def main():
    r = check()
    print("杯壁根部：%.1f MPa（含 Kt %.1f），SF %.1f" %
          (r["cup"], r["cup_kt"], r["cup_sf"]))
    print("柱屈曲：Pcr %.0f N，SF %.1f" % (r["pcr"], r["pcr_sf"]))
    print("环弯曲：%.1f MPa，SF %.1f" % (r["ring"], r["ring_sf"]))
    print("壳固定点（6 mm 垫圈）：%.1f MPa，SF %.1f" %
          (r["bearing_washer"], r["bearing_washer_sf"]))
    print("壳固定点（无垫圈）：%.1f MPa，SF %.1f" %
          (r["bearing_bare"], r["bearing_bare_sf"]))
    print("结论：瓶颈是壳固定点，必须加垫圈/金属衬套；环有 3 倍余量；杯和柱富余。")


if __name__ == "__main__":
    main()
