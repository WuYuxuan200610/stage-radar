# -*- coding: utf-8 -*-
"""阶段流程图：一套坐标，同时产出 SVG 和 PNG。

**跟旧版的唯一区别是流程本身**：
  旧：问1（手上已有论文/方法/积累？）→ 问2（决定具体做什么了吗）→ 问3（实验开题了吗）
  新：问1（你现在卡在哪一步？A/B/C）→ A→启发思路、B→选题中、C→问2（实验开题了吗）

版式、配色、字号、箭头写法全部沿用旧脚本，没有重设计。
输出到 _preview 前缀的文件，
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

BG = "#FFF9F2"
CARD = "#FFFFFF"
BORDER = "#E9D8C8"
STAGE = "#F5B482"
STAGE_LN = "#C97B3F"
INK = "#2B1A0E"
MUTED = "#8A6B4F"
LINE = "#C97B3F"
FONT = "'Microsoft YaHei','PingFang SC',sans-serif"

# ── 坐标区（要调布局改这里）──────────────────────────────
QX, QW = 60, 340
QH1, QH2 = 170, 120          # 问 1 要高一些（列了 A/B 两个选项）
SX, SW, SH = 580, 440, 110
W, H = 1120, 800
TITLE = "你处在哪个阶段？问两句话就知道"

q1, q2 = 90, 430
s1, s2, s3, s4 = 90, 250, 430, 590

q1c = q1 + QH1 / 2
q2c = q2 + QH2 / 2
Q1Xc = QX + QW / 2
Q2Xc = QX + QW / 2

BOXES = [
    # 问 1：标题 + 两个选项（C 由箭头往下带出）
    (QX, q1, QW, QH1,
     ["你现在卡在哪一步？", "A  不知道下一步该做什么", "B  有方向，不知选哪个切口"],
     CARD, BORDER, 20),
    # 问 2
    (QX, q2, QW, QH2, ["C  已经定了具体题目", "实验开题了吗？"], CARD, BORDER, 20),
    (SX, s1, SW, SH, ["启发思路", "往外扩：别人的什么能搬过来"], STAGE, STAGE_LN, 25),
    (SX, s2, SW, SH, ["选题中", "往里收：哪块值得挖、别人还没占"], STAGE, STAGE_LN, 25),
    (SX, s3, SW, SH, ["定题设计实验", "前人工作 · 类似思路 · 方法可复用"], STAGE, STAGE_LN, 25),
    (SX, s4, SW, SH, ["已开题未结题", "防抢发：谁可能已经抢在你前面"], STAGE, STAGE_LN, 25),
]

BEND_Y = s4 + SH / 2
SEGS = [
    # A：问1 的第二个文字行高度 → 启发思路
    ((QX + QW, q1 + 100, SX, s1 + SH / 2), "A", 0),
    # B：问1 的第三个文字行高度 → 选题中
    ((QX + QW, q1 + 140, SX, s2 + SH / 2), "B", 0),
    # C：问1 往下 → 问2
    ((Q1Xc, q1 + QH1, Q2Xc, q2), "C", 90),
    # 问2 → 定题设计实验
    ((QX + QW, q2c, SX, s3 + SH / 2), "还在设计", 0),
    # 问2 往下再往右 → 已开题未结题（与旧版同法，不往回拐）
    ((Q2Xc, q2 + QH2, Q2Xc, BEND_Y), None, None),
    ((Q2Xc, BEND_Y, SX, BEND_Y), "已经在做", 0),
]


def arrow_head(cx, cy, angle):
    L, Wd = 16, 6
    a = math.radians(angle)
    p2 = (cx - L * math.cos(a) + Wd * math.sin(a), cy - L * math.sin(a) - Wd * math.cos(a))
    p3 = (cx - L * math.cos(a) - Wd * math.sin(a), cy - L * math.sin(a) + Wd * math.cos(a))
    return [(cx, cy), p2, p3]


# ══ SVG ═════════════════════════════════════════════════
svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
       'viewBox="0 0 %d %d" font-family="%s">' % (W, H, W, H, FONT),
       '<rect width="%d" height="%d" fill="%s"/>' % (W, H, BG),
       '<text x="60" y="52" font-size="30" fill="%s">%s</text>' % (INK, TITLE)]

for x, y, w, h, lines, fill, stroke, size in BOXES:
    svg.append('<rect x="%d" y="%d" width="%d" height="%d" rx="16" fill="%s" '
               'stroke="%s" stroke-width="3"/>' % (x, y, w, h, fill, stroke))
    lh = size + 8
    y0 = y + h / 2 - (len(lines) - 1) * lh / 2 + size * 0.35
    svg.append('<text x="%.1f" y="%.1f" font-size="%d" fill="%s" text-anchor="middle">'
               % (x + w / 2, y0, size, INK))
    for i, ln in enumerate(lines):
        svg.append('<tspan x="%.1f" dy="%.1f">%s</tspan>'
                   % (x + w / 2, 0 if i == 0 else lh, ln))
    svg.append('</text>')

for (x1, y1, x2, y2), text, ang in SEGS:
    svg.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
               'stroke-width="3.5"/>' % (x1, y1, x2, y2, LINE))
    if text:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        wpx = len(text) * 21 * 1.02 + 16
        svg.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                   % (mx - wpx / 2, my - 21 * 0.78, wpx, 21 * 1.5, BG))
        svg.append('<text x="%.1f" y="%.1f" font-size="21" fill="%s" '
                   'text-anchor="middle">%s</text>' % (mx, my + 21 * 0.34, LINE, text))
    if ang is not None:
        pts = arrow_head(x2, y2, ang)
        svg.append('<polygon points="%s" fill="%s"/>'
                   % (" ".join("%.1f,%.1f" % p for p in pts), LINE))

# 底部说明
note = ("「有没有前期积累」单独问一句，但它不决定阶段：任何领域的积累都算（交叉最有用）")
svg.append('<text x="560" y="755" font-size="19" fill="%s" text-anchor="middle">%s</text>'
           % (MUTED, note))
svg.append('</svg>')

# ══ PNG ═════════════════════════════════════════════════
SS = 1.4
PW, PH = int(W * SS), int(H * SS)
img = Image.new("RGB", (PW, PH), BG)
d = ImageDraw.Draw(img)
FONT_FILE = r"C:\Windows\Fonts\msyh.ttc"


def hx(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def font(sz):
    return ImageFont.truetype(FONT_FILE, int(sz * SS))


def put(x, y, text, f, fill, anchor="mm"):
    d.text((x * SS, y * SS), text, font=f, fill=hx(fill), anchor=anchor)


put(60, 38, TITLE, font(30), INK, "lm")

for x, y, w, h, lines, fill, stroke, size in BOXES:
    d.rounded_rectangle([x * SS, y * SS, (x + w) * SS, (y + h) * SS], radius=16 * SS,
                        fill=hx(fill), outline=hx(stroke), width=int(3 * SS))
    lh = size + 8
    y0 = y + h / 2 - (len(lines) - 1) * lh / 2
    for i, ln in enumerate(lines):
        put(x + w / 2, y0 + i * lh, ln, font(size), INK)

for (x1, y1, x2, y2), text, ang in SEGS:
    d.line([x1 * SS, y1 * SS, x2 * SS, y2 * SS], fill=hx(LINE), width=int(3.5 * SS))
    if text:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        f = font(21)
        bb = d.textbbox((0, 0), text, font=f)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        d.rectangle([mx * SS - tw / 2 - 8, my * SS - th / 2 - 6,
                     mx * SS + tw / 2 + 8, my * SS + th / 2 + 6], fill=hx(BG))
        put(mx, my, text, f, LINE)
    if ang is not None:
        pts = arrow_head(x2, y2, ang)
        d.polygon([(p[0] * SS, p[1] * SS) for p in pts], fill=hx(LINE))

put(560, 755, note, font(19), MUTED)

base = r"F:\stage-radar\stage-radar\docs\stage-flow"
os.makedirs(os.path.dirname(base), exist_ok=True)
with open(base + ".svg", "w", encoding="utf-8") as f:
    f.write("\n".join(svg))
img.save(base + ".png")
print("saved", base + ".svg", "and", base + ".png", img.size)
