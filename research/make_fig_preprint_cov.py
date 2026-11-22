# --- 路径前导（由 _migrate_research.py 注入，使脚本可在任意机器运行）---
# _HERE 本目录；_REPO 本仓库根（含 benchmark.py）；_APP 桌面管线所在仓库（可用环境变量覆盖）
import os as _os
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_REPO = _HERE.parent
_APP = _Path(_os.environ.get("STAGE_RADAR_APP", str(_REPO.parent / "stage-radar-app")))
# --- 前导结束 ---

"""期刊论文中「有预印本」的比例图（终版）。"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

R = Path(str(_HERE))
d = json.loads((R / "preprint_coverage_summary.json").read_text(encoding="utf-8"))
tc = json.loads((R / "title_change_summary.json").read_text(encoding="utf-8"))
ORANGE, GREY, GREEN = "#F5B482", "#C9CDD2", "#7FB069"

overall = d["with_preprint"] / d["total"] * 100
corrected = overall / tc["same_rate"]

fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.6), dpi=200)

# ① 按家族
ax = axes[0]
items = sorted([(k, v) for k, v in d["by_family"].items() if v["total"] >= 100],
               key=lambda kv: kv[1]["with_pre"] / kv[1]["total"])
names = [k for k, _ in items]
rates = [v["with_pre"] / v["total"] * 100 for _, v in items]
cnts = [v["total"] for _, v in items]
ax.barh(range(len(names)), rates, 0.6,
        color=["#D9B48F" if "ACS" in n or "Angew" in n else ORANGE for n in names], zorder=2)
ax.axvline(overall, color="#B8793F", ls="--", lw=1.4, zorder=3)
ax.text(overall + 0.1, -0.72, "全样本 %.1f%%" % overall, color="#B8793F", fontsize=9)
ax.set_yticks(range(len(names)))
ax.set_yticklabels(["%s\n(%d 篇)" % (n, c) for n, c in zip(names, cnts)], fontsize=8.5)
for i, v in enumerate(rates):
    ax.text(v + 0.1, i, "%.1f%%" % v, va="center", fontsize=9.5)
ax.set_xlabel("该家族论文中能找到预印本的比例（%）", fontsize=10.5)
ax.set_xlim(0, max(rates) * 1.4)
ax.set_title("① 按期刊家族的预印本配备比例", fontsize=11.5, pad=10)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", color="#ECECEC", zorder=0)

# ② 校正
ax = axes[1]
labels = ["标题匹配实测\n（下界）", "按 %.0f%% 标题改动率\n校正后" % ((1 - tc["same_rate"]) * 100)]
vals = [overall, corrected]
ax.bar([0, 1], vals, 0.45, color=[ORANGE, GREEN], zorder=2)
for i, v in enumerate(vals):
    ax.text(i, v + 0.06, "%.1f%%" % v, ha="center", fontsize=12, fontweight="bold")
ax.set_xticks([0, 1])
ax.set_xticklabels(labels, fontsize=9.5)
ax.set_ylabel("期刊论文中有预印本的比例（%）", fontsize=10.5)
ax.set_ylim(0, max(vals) * 1.5)
ax.set_title("② 标题匹配下界与校正值", fontsize=11.5, pad=10)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", color="#ECECEC", zorder=0)

fig.suptitle("期刊论文的预印本配备率（%d 篇；期刊窗口 2026-10-18..11-17，预印本索引 2026-04..11）"
             % d["total"], fontsize=12, y=0.985)
fig.text(0.5, 0.012,
         "注：匹配为归一化标题精确匹配，是**下界**（更早发布的预印本不在索引内；16% 的论文见刊时改了标题）。"
         "索引仅覆盖 bioRxiv 与 medRxiv，未含 ChemRxiv / SSRN / arXiv，"
         "故化学与社科的【有预印本比例被低估】（即无预印本比例被高估）。"
         "语料含新闻与勘误等非研究条目，无法完全剔除。",
         ha="center", fontsize=7.4, color="#666666", wrap=True)
fig.tight_layout(rect=[0, 0.06, 1, 0.955])
for ext in ("svg",):
    fig.savefig(R / f"fig_preprint_coverage.{ext}")
print("WROTE", R / "fig_preprint_coverage.png")
print("实测 %.2f%% → 校正后 %.2f%%" % (overall, corrected))
