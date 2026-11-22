# -*- coding: utf-8 -*-
"""阶段流程图：一套坐标，同时产出 SVG（矢量·可手改）和 PNG（README 直接显示）。

改布局只改下面的「坐标」区即可，两个文件一起变，不会打架。
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
QX, QW, QH = 60, 300, 110
SX, SW, SH = 560, 420, 110
QYS = [90, 320, 550]          # 三个问句的 y
SYS = [90, 320, 550, 730]     # 四个阶段的 y
W, H = 1120, 880
TITLE = "你处在哪个阶段？问三句话就知道"

q1, q2, q3 = QYS
s1, s2, s3, s4 = SYS
QXc = QX + QW / 2
mid = lambda y: y + QH / 2

BOXES = [
    (QX, q1, QW, QH, ["手上已有论文 / 方法 / 积累", "想用它找新方向吗？"], CARD, BORDER, 21),
    (QX, q2, QW, QH, ["决定具体做什么了吗？"], CARD, BORDER, 21),
    (QX, q3, QW, QH, ["实验开题了吗？"], CARD, BORDER, 21),
    (SX, s1, SW, SH, ["启发思路", "往外推：它还能干什么"], STAGE, STAGE_LN, 25),
    (SX, s2, SW, SH, ["选题中", "往里收：哪块值得挖"], STAGE, STAGE_LN, 25),
    (SX, s3, SW, SH, ["定题设计实验", "前人工作 · 方法可复用"], STAGE, STAGE_LN, 25),
    (SX, s4, SW, SH, ["已开题未结题", "防抢发"], STAGE, STAGE_LN, 25),
]

# 箭头：((x1,y1,x2,y2), 标签 or None, 箭头朝向)
BEND_Y = mid(s4)
SEGS = [
    ((QX + QW, mid(q1), SX, mid(s1)), "有", 0),
    ((QXc, q1 + QH, QXc, q2), "没有", 90),
    ((QX + QW, mid(q2), SX, mid(s2)), "只有大方向", 0),
    ((QXc, q2 + QH, QXc, q3), "定了", 90),
    ((QX + QW, mid(q3), SX, mid(s3)), "还在设计", 0),
    # 已经在做：**先往下、再往右**（不往回拐）
    ((QXc, q3 + QH, QXc, BEND_Y), None, None),
    ((QXc, BEND_Y, SX, BEND_Y), "已经在做", 0),
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

svg.append('</svg>')

# ══ PNG ═════════════════════════════════════════════════
SS = 1.4                                  # 放大倍数，字更清楚
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

base = r"F:\stage-radar\stage-radar\docs\stage-flow"
os.makedirs(os.path.dirname(base), exist_ok=True)
with open(base + ".svg", "w", encoding="utf-8") as f:
    f.write("\n".join(svg))
img.save(base + ".png")
print("saved", base + ".svg", "and", base + ".png", img.size)
