"""按 benchmark v2 的结果绘制两张矢量图（三系统：fulltext / title_only / stageradar）。

v1 的绘图脚本读的是 rows[].baseline/after，v2 结构已变，故重写。
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from matplotlib.patches import Patch

matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

METRICS = ["Precision@5", "Precision@10", "Recall@10", "F1@10", "MRR"]
KEYS = ["p5", "p10", "r10", "f1", "mrr"]
SYSTEMS = ["fulltext", "title_only", "stageradar", "stageradar_v2"]
LABELS = {
    "fulltext": "A 全文关键词检索",
    "title_only": "B 仅标题检索",
    "stageradar": "C 锚点硬门",
    "stageradar_v2": "D 标题/摘要 + 锚点加权（本项目采用）",
}
COLORS = {"fulltext": "#9AA0A6", "title_only": "#C9CDD2",
          "stageradar": "#E8D5C0", "stageradar_v2": "#F5B482"}
EDGES = {"fulltext": "#6B7075", "title_only": "#9AA0A6",
         "stageradar": "#C0A98E", "stageradar_v2": "#B8793F"}
EXTS = ("svg", "pdf", "png")


def load(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = data["rows"]
    n = len(rows)
    series = {s: {k: np.array([r[s][k] for r in rows], dtype=float) for k in KEYS} for s in SYSTEMS}
    return series, n, data


def bar_chart(series, n, data, outdir):
    x = np.arange(len(METRICS))
    width = 0.20
    fig, ax = plt.subplots(figsize=(10.2, 5.6), dpi=200)
    err_kw = dict(elinewidth=1.0, capsize=3.2, capthick=1.0)
    k = len(SYSTEMS)
    for i, s in enumerate(SYSTEMS):
        means = [series[s][key].mean() for key in KEYS]
        sems = [series[s][key].std(ddof=1) / np.sqrt(n) for key in KEYS]
        ax.bar(x + (i - (k - 1) / 2) * width, means, width, color=COLORS[s], edgecolor="white",
               linewidth=0.6, label=LABELS[s], yerr=sems, error_kw=err_kw, zorder=2)
    ax.set_xticks(x)
    ax.set_xticklabels(METRICS, fontsize=10)
    ax.set_ylabel("分数（0–1）", fontsize=11)
    ax.set_ylim(0, 1.0)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(0.2))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    n_terms = n // data["topics"] if data.get("topics") else n
    ax.set_title("检索质量对比（N=32 = 8 课题 × 4 卖点词，均值 ± SEM）\n"
                 "数据源：Europe PMC；判定：预定义相关概念集", fontsize=11, pad=10)
    ax.grid(axis="y", color="#ECECEC", linewidth=0.6, zorder=0)
    fig.tight_layout()
    for ext in EXTS:
        fig.savefig(outdir / f"benchmark_summary.{ext}")
    print(f"柱状图：{outdir / 'benchmark_summary.svg'} / .pdf / .png")


def box_plot(series, n, data, outdir):
    x = np.arange(len(METRICS))
    k = len(SYSTEMS)
    width = 0.20
    fig, ax = plt.subplots(figsize=(10.2, 5.6), dpi=200)
    rng = np.random.default_rng(0)
    for i, key in enumerate(KEYS):
        for j, s in enumerate(SYSTEMS):
            vals = series[s][key]
            pos = x[i] + (j - (k - 1) / 2) * width
            ax.boxplot(vals, positions=[pos], widths=width * 0.82, patch_artist=True,
                       medianprops=dict(color="#333", linewidth=1.0),
                       boxprops=dict(facecolor=COLORS[s], color=EDGES[s]),
                       whiskerprops=dict(color=EDGES[s]), capprops=dict(color=EDGES[s]),
                       flierprops=dict(marker="o", markersize=2.2, alpha=0.3))
            jx = pos + rng.normal(0, width * 0.09, len(vals))
            ax.scatter(jx, vals, color=EDGES[s], s=11, zorder=3, alpha=0.5, linewidths=0)
    ax.set_xticks(x)
    ax.set_xticklabels(METRICS, fontsize=10)
    ax.set_ylabel("分数（0–1）", fontsize=11)
    # 坐标范围刻意放大：数据集中在 0–0.8，留足边距让须与离群点都在图内
    ax.set_ylim(-0.25, 1.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="#ECECEC", linewidth=0.6, zorder=0)
    ax.legend(handles=[Patch(facecolor=COLORS[s], edgecolor=EDGES[s], label=LABELS[s]) for s in SYSTEMS],
              frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title(f"分布对比（N={n}，箱线 + 散点；每组卖点词为一个点）\n"
                 "数据源：Europe PMC", fontsize=11, pad=10)
    fig.tight_layout()
    for ext in EXTS:
        fig.savefig(outdir / f"benchmark_boxplot.{ext}")
    print(f"箱线图：{outdir / 'benchmark_boxplot.svg'} / .pdf / .png")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "benchmark_results.json"
    outdir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
    series, n, data = load(path)
    bar_chart(series, n, data, outdir)
    # 箱线图已移除：README 只保留柱状图（读者看均值 ± SEM 已足够，
    # 箱线图与柱状图讲的是同一件事）。box_plot() 仍保留供单独调用。
    if "--with-boxplot" in sys.argv:
        box_plot(series, n, data, outdir)


if __name__ == "__main__":
    main()
