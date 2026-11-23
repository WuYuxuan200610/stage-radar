# --- 路径前导（由 _migrate_research.py 注入，使脚本可在任意机器运行）---
# _HERE 本目录；_REPO 本仓库根（含 benchmark.py）；_APP 桌面管线所在仓库（可用环境变量覆盖）
import os as _os
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_REPO = _HERE.parent
_APP = _Path(_os.environ.get("STAGE_RADAR_APP", str(_REPO.parent / "stage-radar-app")))
# --- 前导结束 ---

"""三路来源覆盖对比图。"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

R = Path(str(_HERE))
d = json.loads((R / "coverage_three_summary.json").read_text(encoding="utf-8"))
GREY, ORANGE, GREEN, BLUE = "#C9CDD2", "#F5B482", "#7FB069", "#8FAFC9"

fig, axes = plt.subplots(1, 3, figsize=(13.6, 4.6), dpi=200)

# ① 每个策略能看到多少 / 漏多少
ax = axes[0]
names = ["只查预印本\n（bioRxiv+medRxiv 整窗）", "只查聚合库\n（Europe PMC 关键词）",
         "只查期刊\n（51 本刊整窗）", "三路并用\n（本项目）"]
seen = [d["only_preprint"], d["only_epmc"], d["only_journal"], d["union"]]
U = d["union"]
missed = [U - s for s in seen]
x = np.arange(4)
cols = [ORANGE, BLUE, "#D9B48F", GREEN]
ax.bar(x, seen, 0.55, color=cols, zorder=2)
for i in range(4):
    if missed[i]:
        ax.bar(x[i], missed[i], 0.55, bottom=seen[i], color=GREY, zorder=2)
        ax.text(x[i], seen[i] + missed[i] / 2, "漏 %d" % missed[i], ha="center",
                va="center", color="#444", fontsize=10)
    else:
        ax.text(x[i], seen[i] + 12, "全覆盖", ha="center", color="#2E7D32", fontsize=10)
    ax.text(x[i], -34, "%.0f%%" % (missed[i] / U * 100), ha="center", fontsize=10,
            color="#B3261E" if missed[i] else "#2E7D32")
ax.set_xticks(x)
ax.set_xticklabels(names, fontsize=7.6)
ax.set_ylabel("相关论文条数", fontsize=11)
ax.set_ylim(-52, U * 1.12)
ax.set_title("① 单来源覆盖（按归一化标题去重后 %d 条）" % U, fontsize=11.5, pad=10)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", color="#ECECEC", zorder=0)

# ② 独有贡献
ax = axes[1]
parts = [("预印本独有", d["unique_preprint"], ORANGE),
         ("聚合库独有", d["unique_epmc"], BLUE),
         ("期刊独有", d["unique_journal"], "#D9B48F")]
left = 0
for name, v, c in parts:
    ax.barh([0], [v], 0.5, left=left, color=c, label="%s %d 条" % (name, v), zorder=2)
    ax.text(left + v / 2, 0, str(v), ha="center", va="center",
            color="white" if c != "#D9B48F" else "#5A4632", fontsize=11)
    left += v
ax.set_yticks([])
ax.set_xlabel("相关论文条数", fontsize=11)
ax.set_title("② 三路各自的独有贡献", fontsize=11.5, pad=10)
ax.legend(frameon=False, fontsize=9, loc="lower center", ncol=3)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", color="#ECECEC", zorder=0)
ax.set_ylim(-0.9, 0.9)

# ③ 两两重叠：证明"不重叠"
ax = axes[2]
labels = ["预印本∩期刊", "预印本∩聚合库", "期刊∩聚合库", "三路都有"]
vals = [d["overlap_pj"], d["overlap_pe"], d["overlap_je"], d["overlap_all"]]
ax.bar(range(4), vals, 0.55, color=[GREY, ORANGE, "#D9B48F", "#B0B0B0"], zorder=2)
for i, v in enumerate(vals):
    ax.text(i, v + 0.7, str(v), ha="center", fontsize=11)
ax.set_xticks(range(4))
ax.set_xticklabels(labels, fontsize=9)
ax.set_ylabel("重叠条数", fontsize=11)
ax.set_ylim(0, max(vals) + 6)
ax.set_title("③ 来源之间的重叠（按归一化标题）", fontsize=11.5, pad=10)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", color="#ECECEC", zorder=0)

fig.suptitle("来源覆盖实测：三种取数方式的可见集合（N=8 课题，窗口 2026-10-18..11-17）",
             fontsize=12.5, y=0.985)
fig.text(0.5, 0.012,
         "注：三种取数方式是各来源**唯一可行**的方式——预印本平台与期刊不提供主题检索，只能整窗扫描；"
         "聚合库只能按关键词查。因此本图比较的是「来源策略」，不是排序算法。"
         "对应工具形态：只查预印本 ≈ zotero-arxiv-daily、Preprint Bot；只查聚合库 ≈ 关键词直查的通用 agent；只查期刊 ≈ 期刊目次订阅。",
         ha="center", fontsize=7.4, color="#666666", wrap=True)
fig.tight_layout(rect=[0, 0.05, 1, 0.955])
for ext in ("svg",):
    fig.savefig(R / f"fig_coverage.{ext}")
print("WROTE", R / "fig_coverage.svg")
