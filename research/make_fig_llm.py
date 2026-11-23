# --- 路径前导（由 _migrate_research.py 注入，使脚本可在任意机器运行）---
# _HERE 本目录；_REPO 本仓库根（含 benchmark.py）；_APP 桌面管线所在仓库（可用环境变量覆盖）
import os as _os
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_REPO = _HERE.parent
_APP = _Path(_os.environ.get("STAGE_RADAR_APP", str(_REPO.parent / "stage-radar-app")))
# --- 前导结束 ---

"""理解层实验的对比图：两个真实课题、两个不同阶段。"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

R = Path(str(_HERE))
A = json.loads((R / "review_result.json").read_text(encoding="utf-8"))          # capping-ivt
B = json.loads((R / "review_result_peptide-macrocyclization.json").read_text(encoding="utf-8"))

GREY, ORANGE, GREEN, RED = "#C9CDD2", "#F5B482", "#7FB069", "#D98C8C"
fig, axes = plt.subplots(1, 3, figsize=(13.6, 4.6), dpi=200)

names = ["capping-ivt\n(已开题未结题)", "peptide-macrocyclization\n(选题中)"]
raw = [A["n_raw"], B["n_raw"]]
kept = [A["n_kept"], B["n_kept"]]

# ① 量对比
ax = axes[0]
x = np.arange(2)
ax.bar(x, kept, 0.45, color=GREEN, label="审核层保留", zorder=2)
ax.bar(x, [r - k for r, k in zip(raw, kept)], 0.45,
       bottom=kept, color=GREY, label="审核层丢弃", zorder=2)
for i in range(2):
    ax.text(i, kept[i] / 2, "%d" % kept[i], ha="center", va="center", color="white", fontsize=12)
    ax.text(i, kept[i] + (raw[i] - kept[i]) / 2, "%d" % (raw[i] - kept[i]),
            ha="center", va="center", color="#444", fontsize=12)
    ax.text(i, raw[i] + 1, "原始 %d 条" % raw[i], ha="center", fontsize=10)
ax.set_xticks(x)
ax.set_xticklabels(names, fontsize=9.5)
ax.set_ylabel("条数", fontsize=11)
ax.set_title("① 候选数：原始检索输出 → 审核后", fontsize=11.5, pad=10)
ax.legend(frameon=False, fontsize=9)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", color="#ECECEC", zorder=0)

# ② 保留率：阶段越"探索"，留得越多
ax = axes[1]
rates = [k / r * 100 for k, r in zip(kept, raw)]
bars = ax.bar(x, rates, 0.45, color=[ORANGE, "#8FBF7F"], zorder=2)
for i, v in enumerate(rates):
    ax.text(i, v + 1.4, "%.0f%%" % v, ha="center", fontsize=12, fontweight="bold")
ax.set_xticks(x)
ax.set_xticklabels(names, fontsize=9.5)
ax.set_ylabel("审核保留率（%）", fontsize=11)
ax.set_ylim(0, 60)
ax.set_title("② 保留率：审核标准随阶段变", fontsize=11.5, pad=10)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", color="#ECECEC", zorder=0)

# ③ 两个方向的判定分歧
ax = axes[2]
lab = ["gold 判相关\n但审核丢弃", "gold 漏判\n但审核保留"]
v1 = [len(A["review_dropped_gold"]), len(B["drop_categories"]) and
      sum(1 for n, j in B["judgments"].items() if j["decision"] == "丢弃"
          and any(it["gold"] for it in []) ) or 0]
# 第二个课题的分歧数从结果文件重建
bj = B["judgments"]
b_dropped_gold = sum(1 for n, j in bj.items() if j["decision"] == "丢弃"
                     and int(n) in [k["n"] for k in []])
# 直接用已算好的：peptide 的 gold 相关 12，保留里 gold 相关 8 → 丢弃 4
b_dropped_gold = B["n_gold_relevant"] - sum(1 for k in B["kept"] if k["gold"])
v1 = [len(A["review_dropped_gold"]), b_dropped_gold]
v2 = [len(A["gold_missed_by_rule"]), sum(1 for k in B["kept"] if not k["gold"])]
w = 0.36
ax.bar(np.arange(2) - w / 2, v1, w, color=RED, label="gold 判相关但审核丢弃", zorder=2)
ax.bar(np.arange(2) + w / 2, v2, w, color=GREEN, label="gold 漏判但审核保留", zorder=2)
for i in range(2):
    ax.text(i - w / 2, v1[i] + 0.12, str(v1[i]), ha="center", fontsize=11)
    ax.text(i + w / 2, v2[i] + 0.12, str(v2[i]), ha="center", fontsize=11)
ax.set_xticks(np.arange(2))
ax.set_xticklabels(names, fontsize=9.5)
ax.set_ylabel("条数", fontsize=11)
ax.set_ylim(0, max(v1 + v2) + 1.6)
ax.set_title("③ 规则判定与审核判断的不一致", fontsize=11.5, pad=10)
ax.legend(frameon=False, fontsize=8.5)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", color="#ECECEC", zorder=0)

fig.suptitle("候选审核层实测：两个真实课题（审核由 agent 执行，单标注者、非双盲）",
             fontsize=12.5, y=0.985)
fig.text(0.5, 0.012,
         "注：「原始检索输出」= 单来源关键词检索的原始结果，即关键词监控类工具会直接推送给用户的全部条目；"
         "「审核」按 SKILL 规则执行——说不出与本课题画像的具体关系即丢弃。"
         "两者定义不同，故与规则判定存在双向分歧。",
         ha="center", fontsize=7.4, color="#666666", wrap=True)
fig.tight_layout(rect=[0, 0.05, 1, 0.955])
for ext in ("svg",):
    fig.savefig(R / f"fig_llm_layer.{ext}")
print("WROTE", R / "fig_llm_layer.svg")
print("保留率：capping-ivt %.0f%%，peptide %.0f%%" % (rates[0], rates[1]))
