# --- 路径前导（由 _migrate_research.py 注入，使脚本可在任意机器运行）---
# _HERE 本目录；_REPO 本仓库根（含 benchmark.py）；_APP 桌面管线所在仓库（可用环境变量覆盖）
import os as _os
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_REPO = _HERE.parent
_APP = _Path(_os.environ.get("STAGE_RADAR_APP", str(_REPO.parent / "stage-radar-app")))
# --- 前导结束 ---

"""产出「stage-radar 与竞品关系」的实测图。

数据来源全部是真实实测：
  - keyword_noise_summary.json    关键词监控（竞品默认形态）的噪音率
  - multisource_gain_summary.json 多源 vs 单源的相关论文覆盖
  - benchmark_results.json        四方案检索质量与成本
  - preprint_lead_summary.json    预印本 → 见刊 的时间差
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

R = Path(str(_HERE))
B = Path(str(_REPO))
GREY, GREY_D, ORANGE, ORANGE_D = "#C9CDD2", "#7A7A7A", "#F5B482", "#B8793F"
GREEN = "#7FB069"


def load(p, default=None):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


# 预印本领先时间（实测：各取 120 条已发表的预印本，DOI 去 Crossref 查见刊日期）
LEAD = {
    "biorxiv": {"n": 120, "p25": 40, "p50": 85, "p75": 111, "p90": 127, "over30": 82},
    "medrxiv": {"n": 120, "p25": 44, "p50": 79, "p75": 110, "p90": 145, "over30": 84},
}


def fig_overview():
    noise = load(R / "keyword_noise_summary.json")
    gain = load(R / "multisource_gain_summary.json")
    bench = load(B / "benchmark_results.json")
    rows = bench["rows"]
    n = len(rows)
    sysnames = ["fulltext", "title_only", "stageradar", "stageradar_v2"]
    labels = ["全文检索\n(竞品默认)", "仅标题", "锚点硬门", "本项目采用"]

    fig, axes = plt.subplots(2, 2, figsize=(12.4, 8.6), dpi=200)

    # (a) 关键词监控：推给你 vs 真正相关
    ax = axes[0][0]
    d, rel = noise["delivered"], noise["relevant"]
    ax.bar([0], [rel], 0.5, color=GREEN, label="真正相关", zorder=2)
    ax.bar([0], [d - rel], 0.5, bottom=[rel], color=GREY, label="与你课题无关", zorder=2)
    ax.text(0, rel / 2, "%d 条" % rel, ha="center", va="center", color="white", fontsize=11)
    ax.text(0, rel + (d - rel) / 2, "%d 条" % (d - rel), ha="center", va="center",
            color="#444", fontsize=11)
    ax.set_xticks([0])
    ax.set_xticklabels(["关键词监控\n（%d 组查询累计）" % noise["n"]], fontsize=10)
    ax.set_ylabel("推送条数", fontsize=11)
    ax.set_title("① 关键词监控的推送构成\n（单来源关键词检索，命中即推；噪音率 %.0f%%）"
                 % (noise["noise_rate"] * 100), fontsize=11.5, pad=10)
    ax.legend(frameon=False, fontsize=9)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#ECECEC", zorder=0)

    # (b) 多源 vs 单源
    ax = axes[0][1]
    t = gain["totals"]
    ax.bar([0], [t["epmc"]], 0.5, color=GREY_D, label="Europe PMC 单源", zorder=2)
    ax.bar([0], [t["new"]], 0.5, bottom=[t["epmc"]], color=ORANGE, label="53 刊额外带来", zorder=2)
    ax.text(0, t["epmc"] / 2, "%d 条" % t["epmc"], ha="center", va="center",
            color="white", fontsize=11)
    ax.text(0, t["epmc"] + t["new"] / 2, "+%d 条" % t["new"], ha="center", va="center",
            color="#6B4A22", fontsize=11, fontweight="bold")
    ax.set_xticks([0])
    ax.set_xticklabels(["相关论文覆盖\n（8 课题，同一窗口）"], fontsize=10)
    ax.set_ylabel("相关论文条数", fontsize=11)
    ax.set_title("② 单来源覆盖：Europe PMC 关键词检索 vs 另加 51 本已核验刊\n"
                 "（8 课题，同一窗口）", fontsize=11.5, pad=10)
    ax.legend(frameon=False, fontsize=9)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#ECECEC", zorder=0)

    # (c) 检索质量
    ax = axes[1][0]
    x = np.arange(3)
    metrics = ["p5", "p10", "mrr"]
    mnames = ["Precision@5", "Precision@10", "MRR"]
    w = 0.2
    colors = [GREY, "#E0E3E6", "#E8D5C0", ORANGE]
    labels = ["A 简单 Prompt\n（全文关键词）", "B 仅标题", "C 锚点硬门", "D 本项目采用"]
    for i, (s, lab) in enumerate(zip(sysnames, labels)):
        vals = [sum(r[s][m] for r in rows) / n for m in metrics]
        ax.bar(x + (i - 1.5) * w, vals, w, color=colors[i], edgecolor="white",
               linewidth=0.5, label=lab, zorder=2)
    # 白板对照：不接任何工具/Skill 的 agent，检索能力为 0
    ax.axhline(0, color="#B3261E", lw=2.2, zorder=4)
    ax.text(2.42, 0.012, "白板 Agent（无工具 / 无 Skill）= 0", color="#B3261E",
            fontsize=9, ha="right", va="bottom", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(mnames, fontsize=10)
    ax.set_ylabel("分数（0–1）", fontsize=11)
    ax.set_title("③ 四种检索方式的检索质量\n（Europe PMC，N=32）", fontsize=11.5, pad=10)
    ax.legend(frameon=False, fontsize=7.5, ncol=2, loc="upper left")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#ECECEC", zorder=0)

    # (d) 成本
    ax = axes[1][1]
    chars = [sum(r[s + "_cost"]["chars"] for r in rows) / n for s in sysnames]
    cnt = [sum(r[s + "_cost"]["n"] for r in rows) / n for s in sysnames]
    ax.scatter(cnt, chars, s=140, c=colors, edgecolors=[GREY_D, GREY_D, ORANGE_D, ORANGE_D],
               linewidths=1.4, zorder=3)
    for i, lab in enumerate(["A 全文关键词检索", "B 仅标题检索", "C 锚点硬门", "D 本项目采用"]):
        ax.annotate(lab, (cnt[i], chars[i]), textcoords="offset points", xytext=(8, 6),
                    fontsize=9)
    ax.set_xlabel("每轮平均候选条数", fontsize=11)
    ax.set_ylabel("送 LLM 审核的文本量（字符）", fontsize=11)
    ax.set_title("④ 单轮检索成本（Europe PMC，每查询均值）", fontsize=11.5, pad=10)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(color="#ECECEC", zorder=0)

    fig.suptitle("stage-radar 检索与覆盖实测（窗口 2026-10-18..11-17）", fontsize=13, y=0.985)
    fig.text(0.5, 0.012,
             "注：① 的「关键词监控」指 Google Scholar Alerts、Litmaps Monitor、Semantic Scholar Alerts 一类只做关键词提醒的工具；"
             "② 的「Europe PMC」为单来源对照；③④ 的 A 同时充当「简单 Prompt」对照组；"
             "「白板 Agent」（无工具、无 Skill）检索能力为 0，未单列柱。",
             ha="center", fontsize=7.6, color="#666666", wrap=True)
    fig.tight_layout(rect=[0, 0.045, 1, 0.962])
    for ext in ("svg",):
        fig.savefig(R / f"fig_competitor_overview.{ext}")
    print("WROTE", R / "fig_competitor_overview.png")


def fig_timeliness():
    fig, ax = plt.subplots(figsize=(8.6, 3.6), dpi=200)
    ypos = [0, 1]
    for i, (srv, s) in enumerate(LEAD.items()):
        q = [s["p25"], s["p50"], s["p75"], s["p90"]]
        ax.plot(q, [i] * 4, "-", color=ORANGE, lw=3, solid_capstyle="round", zorder=2)
        ax.scatter(q, [i] * 4, s=46, color=ORANGE_D, zorder=3)
        ax.scatter([s["p50"]], [i], s=170, marker="D", color="white",
                   edgecolors=ORANGE_D, linewidths=2, zorder=4)
        for qq, lab in zip(q, ["25%", "中位", "75%", "90%"]):
            ax.annotate(lab if qq == s["p50"] else "", (qq, i), textcoords="offset points",
                        xytext=(0, 14), ha="center", fontsize=9,
                        color=ORANGE_D, fontweight="bold")
        ax.text(-6, i, "%s\n(n=%d)" % (srv, s["n"]), ha="right", va="center", fontsize=10)
    ax.axvline(0, color=GREY_D, ls=":", lw=1)
    ax.set_yticks([])
    ax.set_xlim(-10, 170)
    ax.set_ylim(-0.6, 1.5)
    ax.set_xlabel("预印本发布 → 正式见刊 的间隔（天）", fontsize=11)
    ax.set_title("及时性：抢发信号在预印本上就出现了，比见刊早约 3 个月", fontsize=12, pad=12)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", color="#ECECEC", zorder=0)
    fig.tight_layout()
    for ext in ("svg",):
        fig.savefig(R / f"fig_timeliness.{ext}")
    print("WROTE", R / "fig_timeliness.png")


if __name__ == "__main__":
    fig_overview()
    fig_timeliness()
