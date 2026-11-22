# --- 路径前导（由 _migrate_research.py 注入，使脚本可在任意机器运行）---
# _HERE 本目录；_REPO 本仓库根（含 benchmark.py）；_APP 桌面管线所在仓库（可用环境变量覆盖）
import os as _os
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_REPO = _HERE.parent
_APP = _Path(_os.environ.get("STAGE_RADAR_APP", str(_REPO.parent / "stage-radar-app")))
# --- 前导结束 ---

"""第二个课题的判定记录：peptide-macrocyclization（stage=topic_selection）。

与 capping-ivt（active / 防抢发）对比，用来展示**理解层的判定标准随阶段变**：
  - 防抢发：说不出"为什么可能与你竞争"就不进列表 → 极严
  - 选题中：目标是"大范围铺开、覆盖多个可能选题" → 明显更宽
"""
import json
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

R = Path(str(_HERE))
PID = "peptide-macrocyclization"
data = json.loads((R / ("review_input_%s.json" % PID)).read_text(encoding="utf-8"))
items = {it["n"]: it for it in data["items"]}

KEEP, DROP = "保留", "丢弃"
JUDGE = {
    1: (KEEP, "强相关", "膦接力实现裂解-环化一体化，直接是 head-to-tail 大环化**方法学**"),
    2: (DROP, "离题", "阴离子路易斯碱催化，与多肽环化无关"),
    3: (DROP, "离题", "蝶豆植物药理资源"),
    4: (KEEP, "强相关", "可见光驱动多肽大环化（乙烯基→α-硒酮），**方法学**"),
    5: (DROP, "不同层面", "PCSK9 抑制剂 Enlicitide 的临床疗效 GRADE 评价——是药物临床，不是合成方法"),
    6: (DROP, "不同层面", "Enlicitide 的食物影响药代——临床层面"),
    7: (KEEP, "背景", "未保护肽的后期催化硼化——同属多肽后期化学，可迁移到环化策略"),
    8: (KEEP, "强相关", "SuFEx 环化构建 DNA 编码大环肽库，**方法学**"),
    9: (DROP, "不同层面", "IL-23 通路药物综述，临床应用"),
    10: (DROP, "离题", "PCSK9 变体动力学的计算模拟"),
    11: (DROP, "不同方法", "约束肽的生成式计算建模——是**计算设计**路线，与本课题的合成方法学不同层"),
    12: (DROP, "离题", "肿瘤放射性配体治疗综述"),
    13: (KEEP, "背景", "NRAS 选择性大环肽的发现——展示大环肽的应用场景与需求"),
    14: (KEEP, "背景", "de novo 大环肽发现平台（GPCR 配体）——是发现平台，与合成方法学相邻"),
    15: (DROP, "离题", "蝎毒来源补体抑制肽"),
    16: (KEEP, "背景", "CAIX 探针的环肽 linker 优化——含环化连接子层面的优化"),
    17: (DROP, "离题", "抗菌肽数据库与预测工具"),
    18: (KEEP, "强相关", "黑皮素类似物的硫醚/内酰胺环化降环策略，**方法学**"),
}

assert len(JUDGE) == len(items), "判定 %d ≠ 候选 %d" % (len(JUDGE), len(items))

kept = sorted(n for n, (d, _, _) in JUDGE.items() if d == KEEP)
gold_rel = [n for n, it in items.items() if it["gold"]]

print("=" * 80)
print("课题 %s（stage=%s）" % (PID, data["stage"]))
print("=" * 80)
print("竞品默认原始输出            ：%d 条" % len(items))
print("其中 gold 判相关            ：%d 条（精度 %.0f%%）" % (len(gold_rel), len(gold_rel) / len(items) * 100))
print("审核层保留                  ：%d 条" % len(kept))
print("→ 要读的量下降              ：%.0f%%" % ((1 - len(kept) / len(items)) * 100))
print()
for n in kept:
    print("  %2d [%s] %s" % (n, JUDGE[n][1], items[n]["title"][:78]))
    print("      %s" % JUDGE[n][2])

cats = Counter(cat for d, cat, _ in JUDGE.values() if d == DROP)
print()
print("丢弃原因：%s" % dict(cats))

gold_in_kept = sum(1 for n in kept if items[n]["gold"])
print()
print("交叉核对：")
print("  保留条目里 gold 判相关的：%d/%d" % (gold_in_kept, len(kept)))
print("  审核丢弃但 gold 判相关的：%d 条" % len([n for n in gold_rel if JUDGE[n][0] == DROP]))
print("  gold 漏判但审核保留的    ：%d 条" % len([n for n in kept if not items[n]["gold"]]))

json.dump({
    "project": PID, "stage": data["stage"],
    "n_raw": len(items), "n_gold_relevant": len(gold_rel), "n_kept": len(kept),
    "reduction_pct": (1 - len(kept) / len(items)) * 100,
    "drop_categories": dict(cats),
    "kept": [{"n": n, "cat": JUDGE[n][1], "why": JUDGE[n][2],
              "title": items[n]["title"], "gold": items[n]["gold"]} for n in kept],
    "judgments": {str(n): {"decision": v[0], "cat": v[1], "why": v[2]} for n, v in JUDGE.items()},
}, (R / ("review_result_%s.json" % PID)).open("w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("\n写入 review_result_%s.json" % PID)
