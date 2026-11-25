# -*- coding: utf-8 -*-
"""用 Pillow 按新版式画出 docs/stage-flow.png（与 stage-flow.svg 同布局）。

为什么要重画：第一问原来是「手上已有论文/方法/积累想找新方向吗」，
把「有没有积累」当成了阶段判据。按用户 2026-11-25 的口径改为「你卡在哪一步」。
"""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1120, 780
S = 2  # 2x 超采样，导出后缩小，边缘更干净
BG = "#FFF9F2"
INK = "#2B1A0E"
SUB = "#6B5545"
ORANGE = "#F5B482"
ORANGE_LN = "#C97B3F"
RED = "#E26D4E"
RED_LN = "#B2452C"
LINE = "#E9D8C8"
CREAM = "#FFF1E6"

FONT = r"C:\Windows\Fonts\msyh.ttc"
FONT_B = r"C:\Windows\Fonts\msyhbd.ttc"


def f(size, bold=False):
    path = FONT_B if bold and os.path.exists(FONT_B) else FONT
    return ImageFont.truetype(path, size * S)


img = Image.new("RGB", (W * S, H * S), BG)
d = ImageDraw.Draw(img)


def box(x, y, w, h, fill, outline):
    d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + h) * S],
                        radius=16 * S, fill=fill, outline=outline, width=3 * S)


def ctext(cx, y, lines, size, color, bold=False, dy=29):
    fo = f(size, bold)
    for i, t in enumerate(lines):
        bb = d.textbbox((0, 0), t, font=fo)
        tw = bb[2] - bb[0]
        d.text(((cx * S) - tw / 2, (y + i * dy) * S), t, font=fo, fill=color)


def arrow(x1, y1, x2, y2, label=None, lx=None, ly=None):
    d.line([x1 * S, y1 * S, x2 * S, y2 * S], fill=ORANGE_LN, width=4 * S)
    # 箭头
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    L, Wd = 16, 6
    pts = [(x2, y2),
           (x2 - L * math.cos(ang) + Wd * math.sin(ang),
            y2 - L * math.sin(ang) - Wd * math.cos(ang)),
           (x2 - L * math.cos(ang) - Wd * math.sin(ang),
            y2 - L * math.sin(ang) + Wd * math.cos(ang))]
    d.polygon([(px * S, py * S) for px, py in pts], fill=ORANGE_LN)
    if label:
        fo = f(21)
        bb = d.textbbox((0, 0), label, font=fo)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        cx, cy = (lx if lx is not None else (x1 + x2) / 2), (ly if ly is not None else (y1 + y2) / 2)
        d.rectangle([(cx * S - tw / 2 - 6 * S), (cy * S - th / 2 - 6 * S),
                     (cx * S + tw / 2 + 6 * S), (cy * S + th / 2 + 6 * S)], fill=BG)
        d.text((cx * S - tw / 2, cy * S - th / 2 - bb[1]), label, font=fo, fill=ORANGE_LN)


# 标题
d.text((60 * S, 22 * S), "你卡在哪一步？ —— 一句话就能定阶段", font=f(30), fill=INK)

# 问 1
box(60, 90, 330, 150, "#FFFFFF", LINE)
ctext(225, 112, ["你现在卡在哪一步？"], 22, INK, bold=True)
ctext(225, 152, ["A 不知道下一步该做什么"], 19, SUB, dy=35)
ctext(225, 187, ["B 有方向，不知选哪个切口"], 19, SUB, dy=35)

# 启发思路
box(560, 90, 500, 110, ORANGE, ORANGE_LN)
ctext(810, 112, ["启发思路", "往外扩：别人的什么能搬过来"], 25, INK, dy=33)
arrow(390, 172, 556, 148, "A", 474, 158)

# 选题中
box(560, 230, 500, 110, ORANGE, ORANGE_LN)
ctext(810, 252, ["选题中", "往里收：哪块值得挖、别人还没占"], 25, INK, dy=33)
arrow(390, 207, 556, 282, "B", 474, 248)

# C 下到问 2
arrow(225, 240, 225, 376, "C", 225, 300)

# 问 2
box(60, 380, 330, 160, "#FFFFFF", LINE)
ctext(225, 400, ["C 已经定了具体题目", "实验开题了吗？"], 22, INK, bold=True, dy=33)
ctext(225, 475, ["还在设计 · 已经在做"], 19, SUB, dy=35)

# 定题设计实验
box(560, 380, 500, 110, ORANGE, ORANGE_LN)
ctext(810, 402, ["定题设计实验", "前人工作 · 类似思路 · 方法可复用"], 25, INK, dy=33)
arrow(390, 432, 556, 432, "还在设计", 460, 420)

# 已开题未结题
box(560, 520, 500, 110, RED, RED_LN)
ctext(810, 542, ["已开题未结题（防抢发）", "谁可能已经抢在你前面发文"], 25, "#FFF9F2", dy=33)
arrow(390, 492, 556, 572, "已经在做", 460, 535)

# 底部说明
d.rounded_rectangle([60 * S, 668 * S, 1060 * S, 748 * S],
                    radius=14 * S, fill=CREAM, outline=LINE, width=2 * S)
ctext(560, 686, ["「有没有前期积累」要单独问一句，但它不决定阶段：",
                 "任何领域的积累都算（交叉最有用）；有积累也可能不知道下一步做什么，零积累也可能已经定了方向。"],
      19, SUB, dy=28)

out = img.resize((W, H), Image.LANCZOS)
p = r"F:/stage-radar/stage-radar/docs/stage-flow.png"
out.save(p, "PNG", optimize=True)
print("已生成:", p, out.size, "%d KB" % (os.path.getsize(p) // 1024))
