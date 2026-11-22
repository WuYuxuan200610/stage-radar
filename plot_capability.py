"""能力对比矩阵热力图：定性机制对比（✓/✗/部分 → 颜色块），突出 stage-radar 唯一全 ✓。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

# 行 = 能力，列 = 工具；0=✗，0.5=部分，1=✓
ABILITIES = [
    "关键词查询",
    "文献推送",
    "阶段感知（用户可控）",
    "撞题画像（按卖点防抢发）",
    "可解释竞争判断",
    "全源（预印本+期刊+聚合库）",
]
TOOLS = [
    "白板 Agent",
    "简单 Prompt",
    "zotero-arxiv-daily",
    "arxiv-mcp-server",
    "Preprint Bot",
    "wetware",
    "stage-radar",
]
DATA = np.array([
    [0, 1, 1, 1, 1, 1, 1],       # 关键词查询
    [0, 0, 1, 1, 1, 1, 1],       # 文献推送
    [0, 0, 0, 0, 0, 0, 1],       # 阶段感知
    [0, 0, 0, 0, 0, 0, 1],       # 撞题画像
    [0, 0, 0, 0, 0, 0, 1],       # 可解释竞争判断
    [0, 0, 0.5, 0.5, 0, 0.5, 1],  # 全源
], dtype=float)

# 颜色映射：0=浅灰，0.5=中黄，1=橙（stage-radar 主题色）
from matplotlib.colors import ListedColormap
cmap = ListedColormap(["#F0F0F0", "#F0D080", "#F5B482"])

fig, ax = plt.subplots(figsize=(10.5, 4.6), dpi=140)
im = ax.imshow(DATA, cmap=cmap, vmin=0, vmax=1, aspect="auto")

# 网格线
ax.set_xticks(np.arange(len(TOOLS)))
ax.set_yticks(np.arange(len(ABILITIES)))
ax.set_xticklabels(TOOLS, fontsize=9)
ax.set_yticklabels(ABILITIES, fontsize=10)
# stage-radar 列名加粗
for label in ax.get_xticklabels():
    if label.get_text() == "stage-radar":
        label.set_fontweight("bold")

# 单元格标注 有 / 半 / 空白=无
for i in range(len(ABILITIES)):
    for j in range(len(TOOLS)):
        v = DATA[i, j]
        text = "有" if v == 1 else ("半" if v == 0.5 else "")
        ax.text(j, i, text, ha="center", va="center", fontsize=11,
                color="#7A4A1E" if v >= 0.5 else "#BBBBBB")

# stage-radar 列高亮边框
for i in range(len(ABILITIES)):
    ax.add_patch(plt.Rectangle((len(TOOLS) - 1.5, i - 0.5), 1, 1,
                               fill=False, edgecolor="#C97B3F", linewidth=2.2))

ax.grid(False)
ax.set_xticks(np.arange(len(TOOLS) + 1) - 0.5, minor=True)
ax.set_yticks(np.arange(len(ABILITIES) + 1) - 0.5, minor=True)
ax.grid(which="minor", color="white", linewidth=1.6)
ax.tick_params(which="minor", length=0)
ax.tick_params(which="major", length=0)

# 顶部旋转工具名
plt.setp(ax.get_xticklabels(), rotation=28, ha="right", rotation_mode="anchor")

ax.set_title("能力对比（据官方文档；空白=无  半=部分  有=有）", fontsize=12, pad=14)
fig.tight_layout()
for ext in ("svg",):
    fig.savefig(Path(__file__).resolve().parent / f"capability_matrix.{ext}")
print("能力矩阵图 OK：capability_matrix.svg")
