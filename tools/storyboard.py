"""
CoreBall - 它的一天

不是渲染，是分镜：每个时刻它在哪、做什么、灯怎么变、为什么这么做。

用法：
  python storyboard.py
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "blender", "out", "rig", "day.html")

PERSON = (0.0, 890.0)

# t, 标题, x, y, z, 动作, 灯, 为什么
BEATS = [
    ("08:50", "你还没来", -430, 520, 1300,
     "停在待命位，完全静止", "灭",
     "你不在的时候它动，就是耗电和噪音。静止才是本分。"),

    ("09:02", "你坐下", -430, 520, 1300,
     "先不动，3 秒后才亮灯、慢慢转过来", "0 → 40%，2 秒",
     "立刻反应像人体感应灯；延迟 3 秒，才像「注意到你」。"),

    ("09:05", "你开始工作", -500, 700, 1350,
     "退到侧后方，脸转向屏幕，不再看你", "降到 15%",
     "看屏幕的人不需要被看。它要让开视线，不是抢视线。"),

    ("10:30", "你 20 分钟没动", -450, 640, 1260,
     "下降 40mm，靠近 100mm", "缓慢升到 30%",
     "长时间静止可能意味着累。用「靠近」代替「问候」。"),

    ("10:31", "你抬头看它一眼", -450, 640, 1260,
     "立刻停住 → 退回原位", "回落到 15%",
     "被看见就退。这是「不打扰」的最高级表达。"),

    ("12:10", "你去吃饭", -430, 820, 1450,
     "升到高处，转向门口", "暖色，很暗",
     "门是你回来的方向。它面朝门，是等待，不是待机。"),

    ("13:20", "你回来坐下", -500, 700, 1350,
     "你先坐下，它才缓慢滑回侧位", "40% → 15%",
     "迎接应该发生在你安顿之后。在你进门那一刻扑上来，是狗，不是伴。"),

    ("15:00", "你在开会", -520, 850, 1400,
     "退到最远，伸缩轴全收", "灭",
     "持续说话 = 不需要陪伴。这时候任何存在感都是干扰。"),

    ("16:40", "你叹了口气", -380, 620, 1200,
     "下降 60mm，靠近 200mm，**不说任何话**", "暖色，25%",
     "叹气是最明确的需要在场、不需要语言的信号。"),

    ("16:42", "你没理它", -380, 620, 1200,
     "退回原位", "回落到 12%",
     "不被接受就撤，不追问。第二次靠近必须有理由。"),

    ("18:30", "你收拾东西", -380, 520, 1350,
     "升到待命位，正面朝你", "亮着，不呼吸",
     "这是「我在」，不是「我要走」。"),

    ("19:00", "你离开", -430, 600, 1200,
     "慢慢降到最低，灯渐灭", "渐灭，6 秒",
     "关灯要慢。瞬间熄灭是开关，慢慢暗下去是睡觉。"),
]


def mini(x, y, on):
    """小俯视图：工位 + 人 + 球"""
    W, H = 150, 92
    def px(vx, vy):
        return (6 + (vx + 820) / 1640 * (W - 12),
                6 + (vy / 1100) * (H - 12))
    bx, by = px(x, y)
    hx, hy = px(*PERSON)
    col = "#cfe3f0" if on else "#6b7c8a"
    return (
        '<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg">'
        '<rect width="%d" height="%d" rx="6" fill="#0e1216" stroke="#1e2830"/>'
        '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#181c20"/>'
        '<circle cx="%.1f" cy="%.1f" r="4.5" fill="#3a2a28" stroke="#7a4a44"/>'
        '<circle cx="%.1f" cy="%.1f" r="15" fill="none" stroke="#d9534f" '
        'stroke-opacity="0.55" stroke-dasharray="3 3"/>'
        '<circle cx="%.1f" cy="%.1f" r="4" fill="%s"/>'
        '</svg>'
        % (W, H, W, H,
           6 + (40 + 820) / 1640 * (W - 12), 6 + (20 / 1100) * (H - 12),
           (1560 / 1640) * (W - 12), (700 / 1100) * (H - 12),
           hx, hy, hx, hy, bx, by, col))


def main():
    rows = []
    for (t, title, x, y, z, act, led, why) in BEATS:
        rows.append(
            '<div class="beat">'
            '<div class="time">%s</div>'
            '<div class="pic">%s</div>'
            '<div class="body">'
            '<div class="ttl">%s<span class="coord">(%d, %d, %d)</span></div>'
            '<div class="act">%s</div>'
            '<div class="led">灯：%s</div>'
            '<div class="why">%s</div>'
            '</div></div>' % (t, mini(x, y, led != "灭"), title, x, y, z,
                             act, led, why))

    html = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>它的一天</title><style>
:root{color-scheme:dark}
body{margin:0;padding:40px 24px 80px;background:#0a0d10;color:#d7dbe0;
font:15px/1.65 "Segoe UI","Microsoft YaHei",system-ui,sans-serif}
.wrap{max-width:880px;margin:0 auto}
h1{font-size:22px;margin:0 0 6px}
.sub{color:#79838d;font-size:13.5px;margin-bottom:8px}
.rule{margin:26px 0 8px;padding:14px 18px;background:#101519;border-left:3px solid #3f6f8a;
border-radius:0 8px 8px 0;font-size:13.5px;color:#a9b5bf}
.rule b{color:#d7dbe0}
.beat{display:grid;grid-template-columns:56px 150px 1fr;gap:18px;align-items:start;
padding:18px 0;border-bottom:1px solid #161d24}
.time{color:#6f9db5;font-variant-numeric:tabular-nums;font-size:14px;padding-top:4px}
.pic svg{display:block;width:150px;height:auto}
.ttl{font-weight:600;color:#e2eaf0;font-size:15px}
.coord{color:#5f6f7c;font-weight:400;font-size:12px;margin-left:10px;font-variant-numeric:tabular-nums}
.act{margin-top:3px;color:#c2ccd6}
.led{color:#8b949e;font-size:13px;margin-top:2px}
.why{color:#7f8f9c;font-size:13px;margin-top:6px;padding-left:10px;border-left:2px solid #23303a}
h2{font-size:15px;margin:44px 0 10px;color:#c2ccd6}
ul{color:#a9b5bf;font-size:13.5px;padding-left:20px}
li{margin:6px 0}
</style></head><body><div class="wrap">
<h1>它的一天</h1>
<div class="sub">工位场景 · 09:00–19:00 · 十二个时刻</div>

<div class="rule"><b>一天的动作用量是有限的。</b>
如果它一天动五十次，每一次都不再意味着什么。
目标：<b>超过 20mm 的位移，一天 15–25 次</b>，其余时间真的不动。</div>

%s

<h2>它一天里不会做的事</h2>
<ul>
<li>不在你打字的时候靠近</li>
<li>不在你说话的时候发光</li>
<li>不在你静止的时候反复刷存在感</li>
<li>不主动开口——除非被叫</li>
<li>不在同一件事上靠近两次</li>
</ul>

<h2>一天里它说的话</h2>
<ul>
<li>不超过三次</li>
<li>其中至少一次不是信息，只是声音（比如叹气一样的轻响）</li>
</ul>
</div></body></html>""" % "".join(rows)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("输出:", os.path.abspath(OUT))
    print("共 %d 个时刻" % len(BEATS))


if __name__ == "__main__":
    main()
