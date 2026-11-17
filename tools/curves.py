"""
CoreBall - 速度曲线：同一段路，三种节奏

同一段 1139mm 的路，三种时间曲线：
  A 匀速   —— 梯形速度，像机器
  B 柔和   —— S 曲线，慢起慢收
  C 落定   —— S 曲线 + 到位后 4mm 的回落

输出 out/rig/curves.html

用法：
  python curves.py
"""

import os
import math

L = 1139.0          # 路径长度 mm
T = 6.0             # 目标到达时间 s
VMIN_MM = 0.0

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "blender", "out", "rig", "curves.html")


# ---------------- 三条曲线 ----------------
def trapezoid(t):
    """梯形：加速 - 匀速 - 减速，加速度恒定"""
    a = 0.12            # mm/ms^2? 用 mm 和 s 单位
    a = 120.0           # mm/s^2
    vmax = 260.0        # mm/s
    ta = vmax / a                       # 加速时间
    if t < 0:
        return 0.0, 0.0
    if t < ta:
        v = a * t
        return 0.5 * a * t * t, v
    d_total = L
    d_acc = 0.5 * a * ta * ta
    d_cruise = d_total - 2 * d_acc
    if d_cruise < 0:                     # 三角形速度
        ta2 = math.sqrt(d_total / a)
        if t < ta2:
            return 0.5 * a * t * t, a * t
        if t < 2 * ta2:
            v = a * ta2
            return d_total - 0.5 * a * (2 * ta2 - t) ** 2, v - a * (t - ta2)
        return d_total, 0.0
    tc = d_cruise / vmax
    if t < ta + tc:
        return d_acc + vmax * (t - ta), vmax
    td = t - ta - tc
    if td < ta:
        return d_total - 0.5 * a * (ta - td) ** 2, vmax - a * td
    return d_total, 0.0


def scurve(t):
    """S 曲线（最小 jerk 的五次多项式）"""
    if t <= 0:
        return 0.0, 0.0
    if t >= T:
        return L, 0.0
    s = t / T
    x = L * (10 * s ** 3 - 15 * s ** 4 + 6 * s ** 5)
    v = L * (30 * s ** 2 - 60 * s ** 3 + 30 * s ** 4) / T
    return x, v


def settle(t):
    """S 曲线 + 到位后带阻尼的 4mm 回落"""
    x, v = scurve(t)
    if t > T * 0.92:
        dt = t - T * 0.92
        # 阻尼振荡，振幅 4mm，频率约 1.2 Hz
        amp = 4.0
        zeta = 4.5
        w = 2 * math.pi * 1.2
        e = math.exp(-zeta * dt)
        dx = -amp * e * math.cos(w * dt)
        dv = amp * e * (zeta * math.cos(w * dt) + w * math.sin(w * dt))
        x += dx
        v += dv
    return x, v


CURVES = [
    ("匀速", "#e0b060", trapezoid),
    ("柔和", "#4fa87f", scurve),
    ("落定", "#6aa8d8", settle),
]


# ---------------- 画图 ----------------
def sample(fn, t0, t1, n=340):
    pts = []
    for k in range(n + 1):
        t = t0 + (t1 - t0) * k / n
        x, v = fn(t)
        pts.append((t, x, v))
    return pts


def chart(series, key, ylabel, ymax, ymin, width=760, height=260, title=""):
    pad_l, pad_r, pad_t, pad_b = 62, 22, 34, 40
    w = width - pad_l - pad_r
    h = height - pad_t - pad_b
    tmax = max(p[0] for s in series for p in s[2])

    def sx(t): return pad_l + t / tmax * w
    def sy(v): return pad_t + (ymax - v) / (ymax - ymin) * h

    out = ['<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg">' % (width, height),
           '<rect width="%d" height="%d" fill="#101418" rx="10"/>' % (width, height),
           '<text x="%d" y="22" fill="#c2ccd6" font-size="13" font-weight="600">%s</text>' % (pad_l, title)]

    # 网格
    for k in range(5):
        v = ymin + (ymax - ymin) * k / 4
        y = sy(v)
        out.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#1b222a"/>'
                   % (pad_l, y, pad_l + w, y))
        out.append('<text x="%d" y="%.1f" text-anchor="end" fill="#5f6f7c" font-size="10">%.0f</text>'
                   % (pad_l - 8, y + 3, v))
    for k in range(7):
        t = tmax * k / 6
        x = sx(t)
        out.append('<text x="%.1f" y="%d" text-anchor="middle" fill="#5f6f7c" font-size="10">%.0f</text>'
                   % (x, height - 14, t))

    for _, colr, pts in series:
        d = " ".join("%.1f,%.1f" % (sx(p[0]), sy(p[key])) for p in pts)
        out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.2" '
                   'stroke-linejoin="round"/>' % (d, colr))

    out.append('<text x="%d" y="%d" text-anchor="middle" fill="#6f7a85" font-size="11">%s</text>'
               % (pad_l + w / 2, height - 2, ylabel))
    out.append('</svg>')
    return "".join(out)


def main():
    tmax = 8.2
    series = []
    stats = []
    for name, colr, fn in CURVES:
        pts = sample(fn, 0, tmax)
        series.append((name, colr, pts))
        # 到达时间：第一次到 L 的 99%
        t_arr = next((p[0] for p in pts if p[1] >= L * 0.99), tmax)
        vmax = max(p[2] for p in pts)
        # 极端起步与收尾的差别，用两个直观数字
        walk = next(p[1] for p in pts if p[0] >= 0.5)
        stats.append((name, colr, t_arr, vmax, walk))

    LABEL = {"匀速": "硬停", "柔和": "平滑收住", "落定": "回弹 4mm 再停"}

    pos_svg = chart(series, 1, "位置 mm", L + 12, -6, title="位置 - 时间")
    vel_svg = chart(series, 2, "速度 mm/s", 300, -40, title="速度 - 时间")

    legend = "".join('<span><i style="background:%s"></i>%s</span>' % (c, n)
                     for n, c, _, _, _ in stats)
    rows = "".join(
        "<tr><td><b style='color:%s'>%s</b></td><td>%.2f s</td><td>%.0f mm/s</td>"
        "<td>%.0f mm</td><td>%s</td></tr>" % (c, n, ta, vm, wk, LABEL[n])
        for n, c, ta, vm, wk in stats)

    html = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>速度曲线</title><style>
:root{color-scheme:dark}
body{margin:0;padding:36px 24px 70px;background:#0a0d10;color:#d7dbe0;
font:15px/1.65 "Segoe UI","Microsoft YaHei",system-ui,sans-serif}
.wrap{max-width:820px;margin:0 auto}
h1{font-size:21px;margin:0 0 4px}
.sub{color:#79838d;font-size:13px}
svg{display:block;width:100%%;height:auto;margin-top:14px}
table{border-collapse:collapse;margin-top:22px;font-size:13.5px;width:100%%}
th,td{text-align:left;padding:8px 16px 8px 0;border-bottom:1px solid #1d232a}
th{color:#8b949e;font-weight:500}
.legend{display:flex;gap:22px;margin-top:14px;font-size:13px;color:#98a3ad}
.legend i{display:inline-block;width:16px;height:3px;border-radius:2px;margin-right:7px;vertical-align:3px}
</style></head><body><div class="wrap">
<h1>同一段 1139mm 的路，三种节奏</h1>
<div class="sub">位置和速度都是毫米、秒。上面的是"它在哪"，下面的是"它多急"。</div>
<div class="legend">%s</div>
%s
%s
<table><tr><th>节奏</th><th>到达耗时</th><th>峰值速度</th><th>前 0.5 秒走了</th><th>收尾</th></tr>%s</table>
</div></body></html>""" % (legend, pos_svg, vel_svg, rows)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("输出:", os.path.abspath(OUT))
    for n, c, ta, vm, wk in stats:
        print("  %-4s 耗时 %.2fs  峰值 %.0f mm/s  起步 %.0f mm"
              % (n, ta, vm, wk))


if __name__ == "__main__":
    main()
