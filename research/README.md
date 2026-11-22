# research/ — 对照实验与实测数据

本目录是主 README §9 的实验代码与结果。所有数字均来自真实调用，脚本可重跑。

---

## 实验一览

| 脚本 | 回答的问题 | 主要产出 |
|:---|:---|:---|
| `exp_keyword_noise.py` | 单来源关键词检索、命中即推送时，推送内容中有多少与课题无关 | `keyword_noise_summary.json` |
| `exp_coverage_three.py` / `exp_coverage_three_fixed.py` | 只查预印本 / 只查聚合库 / 只查期刊，各自能覆盖多少相关论文 | `coverage_three_summary.json` |
| `build_preprint_index.py` | 构建滞后预印本标题索引（预印本比见刊早约 85 天，必须滞后匹配） | `preprint_index.json`（缓存，不入库） |
| `exp_preprint_coverage.py` | 期刊论文中能找到对应预印本的比例 | `preprint_coverage_summary.json` |
| `exp_title_change.py` | 预印本见刊时标题被修改的比例（用于校正上式） | `title_change_summary.json` |
| `exp_llm_layer2.py` + `exp_review_judge*.py` | 候选经"能否说明与本课题画像的具体关系"审查后的保留情况 | `review_result*.json` |
| `make_figures.py` / `make_fig_*.py` | 出图 | `fig_*.{png,svg,pdf}` |

诊断脚本（`diag_*.py`、`probe_*.py`）记录了实验过程中定位到的四个测量错误，见下节。

---

## 运行

```bash
pip install requests numpy matplotlib
python exp_keyword_noise.py          # 例：复现关键词监控噪音率
python make_figures.py               # 出图
```

**路径约定**：脚本用文件自身位置定位目录，不依赖绝对路径。

- `_HERE`：本目录（`research/`）
- `_REPO`：仓库根（`benchmark.py` 所在处）
- `_APP`：桌面管线所在仓库。默认取 `../stage-radar-app`，可用环境变量覆盖：

```bash
export STAGE_RADAR_APP=/path/to/stage-radar-app
```

**未随仓库发布的大缓存**（可重新生成，`.gitignore` 已排除）：

| 文件 | 体积 | 重建方式 |
|:---|---:|:---|
| `preprint_index.json` | ~19 MB | `python build_preprint_index.py`（约 1.5–2 小时，会按块缓存，可中断续跑） |
| `coverage_preprints.json` | ~16 MB | `python exp_coverage_three.py`（约 20 分钟） |
| `journal_titles_for_preprint_check.json` | ~0.9 MB | `python exp_preprint_coverage.py`（会自动拉取） |

> 不发布这些缓存的原因是体积与可重建性——把它们放进仓库会显著拖慢 clone，且它们是**数据快照而非代码**。

---

## 关于测量误差

这些实验在测量过程中修正过四处误差（连字符归一化、同窗口匹配、两侧归一化口径不一致、跨学科刊混杂），
每一处都曾导致**看似合理但错误**的结论。

**完整的误差分析、全部实测数字、以及与之对应的产品选择，见主 README 的
[§9 我们的 skill 为什么选择这些思路](../README.md)。** 本目录只保留脚本与数据。

---

## 局限（务必与结论一并阅读）

- **相关性为规则标注**（预定义概念集），非多人独立人工评分；候选审核为**单标注者、非双盲**的案例研究。
- **预印本配备率为下界**：更早发布的预印本不在索引内，且 16% 的论文见刊时修改了标题。
- **索引仅覆盖 bioRxiv 与 medRxiv**，未含 ChemRxiv / SSRN / arXiv，
  故化学与社科的**无预印本比例被高估**（等价说法：**有预印本比例被低估**）。
- **三种取数方式比较的是来源策略，不是排序算法**——预印本平台与期刊不提供主题检索，只能整窗扫描；聚合库只能按关键词查询。
