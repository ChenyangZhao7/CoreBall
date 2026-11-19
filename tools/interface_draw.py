"""
CoreBall - 接口图生成器（井的俯视图）

尺寸全部从 interface_spec 取，不要在这里另抄一份。

用法：
  python tools/interface_draw.py --out docs/interface.svg
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import interface_spec as I

VIEW = 420
CX = CY = VIEW / 2.0
SCALE = 9.0                    # px / mm：井 r15 → 135 px


def _pt(radius_mm, angle_deg):
    """数学角度（逆时针）→ SVG 坐标；SVG 的 y 向下，所以取负。"""
    x, y = I.polar(radius_mm * SCALE, angle_deg)
    return CX + x, CY - y


def _fmt(value):
    return "%.2f" % value


def svg(size=420):
    """返回完整的 SVG 文本。"""
    well_r = I.WELL_R * SCALE
    pad_r = (I.PAD_D / 2.0) * SCALE
    key_half = (I.SLOT_W / 2.0) * SCALE
    magnet_r = (I.MAGNET_D / 2.0) * SCALE
    pin_label_r = 6.2

    out = []
    out.append('<?xml version="1.0" encoding="UTF-8"?>')
    out.append(
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
        'viewBox="0 0 %d %d" role="img" '
        'aria-label="CoreBall 接口 v%s 井俯视图">'
        % (size, size, VIEW, VIEW, I.VERSION)
    )
    out.append("<style>"
               "text{font-family:'DejaVu Sans','Noto Sans CJK SC',"
               "'Microsoft YaHei',sans-serif;fill:#222}"
               ".ref{stroke:#cfcfcf;stroke-width:1;stroke-dasharray:4 4}"
               ".dim{stroke:#444;stroke-width:1}"
               ".pad{fill:#b87333;stroke:#7a4a20;stroke-width:1}"
               ".slot{fill:#4a4a4a}"
               ".magnet{fill:#c9a227;stroke:#8a6d0f;stroke-width:1}"
               "</style>")

    out.append('<rect x="0" y="0" width="%d" height="%d" fill="#ffffff"/>'
               % (VIEW, VIEW))

    # 标题
    out.append('<text x="%.1f" y="24" font-size="14" text-anchor="middle">'
               'CoreBall 接口 · 井俯视 v%s</text>' % (CX, I.VERSION))

    # 井
    out.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#f7f7f7" '
               'stroke="#333" stroke-width="2"/>' % (CX, CY, well_r))

    # 每 60° 一条参考线，标出 0° 起点
    for angle in I.PAD_ANGLES:
        x2, y2 = _pt(I.WELL_R, angle)
        out.append('<line class="ref" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                   % (CX, CY, x2, y2))
        lx, ly = _pt(I.WELL_R + 1.7, angle)
        weight = ' font-weight="bold"' if angle == 0.0 else ""
        out.append('<text x="%.1f" y="%.1f" font-size="10" '
                   'text-anchor="middle"%s>%g°</text>'
                   % (lx, ly + 3.5, weight, angle))

    # φ30.00 尺寸线
    top = CY - well_r
    out.append('<line class="dim" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
               % (CX - well_r, top - 22, CX + well_r, top - 22))
    for x in (CX - well_r, CX + well_r):
        out.append('<line class="dim" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                   % (x, top - 27, x, top - 17))
    out.append('<text x="%.1f" y="%.1f" font-size="14" text-anchor="middle">'
               'φ%s</text>' % (CX, top - 30, _fmt(I.WELL_R * 2)))

    # 6 个焊盘 + 引脚名
    for angle, name in zip(I.PAD_ANGLES, I.PIN_NAMES):
        x, y = _pt(I.PAD_PITCH_R, angle)
        out.append('<circle class="pad" cx="%.1f" cy="%.1f" r="%.1f"/>'
                   % (x, y, pad_r))
        lx, ly = _pt(pin_label_r, angle)
        out.append('<text x="%.1f" y="%.1f" font-size="7" '
                   'text-anchor="middle">%s</text>' % (lx, ly + 2.5, name))

    # 3 块磁铁
    for angle in I.MAGNET_ANGLES:
        x, y = _pt(I.MAGNET_R, angle)
        out.append('<circle class="magnet" cx="%.1f" cy="%.1f" r="%.1f"/>'
                   % (x, y, magnet_r))

    # 3 个键槽（球井底的凹槽，不是键）
    for angle in I.KEY_ANGLES:
        x, y = _pt(I.KEY_R, angle)
        out.append('<rect class="slot" x="%.1f" y="%.1f" width="%.1f" '
                   'height="%.1f" transform="rotate(%.1f %.1f %.1f)"/>'
                   % (x - key_half, y - key_half, key_half * 2, key_half * 2,
                      angle, x, y))

    # 深与键位
    out.append('<text x="%.1f" y="%.1f" font-size="12" text-anchor="middle">'
               '深 %s</text>' % (CX, CY + well_r + 23, _fmt(I.WELL_DEPTH)))
    out.append('<text x="%.1f" y="%.1f" font-size="12" text-anchor="middle">'
               '键 %s · 槽 %s × %s</text>'
               % (CX, CY + well_r + 45,
                  " / ".join("%g°" % a for a in I.KEY_ANGLES),
                  _fmt(I.SLOT_W), _fmt(I.SLOT_DEPTH)))

    # 图例 + 单位
    out.append('<text x="%.1f" y="%.1f" font-size="9" text-anchor="middle">'
               '金色=磁铁位置（球侧为钢片）；灰=键槽；铜=焊盘 · 尺寸单位 mm</text>'
               % (CX, CY + well_r + 64))

    out.append("</svg>")
    return "\n".join(out) + "\n"


def write(path, size=420):
    """把接口图写成 UTF-8 文件，换行固定为 LF。"""
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg(size))


def main(argv=None):
    parser = argparse.ArgumentParser(description="生成 CoreBall 接口图")
    parser.add_argument("--out", default=os.path.join("docs", "interface.svg"),
                        help="输出路径（默认 docs/interface.svg）")
    parser.add_argument("--size", type=int, default=420, help="画布边长（px）")
    args = parser.parse_args(argv)
    write(args.out, args.size)
    print("wrote %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
