# --- 路径前导（由 _migrate_research.py 注入，使脚本可在任意机器运行）---
# _HERE 本目录；_REPO 本仓库根（含 benchmark.py）；_APP 桌面管线所在仓库（可用环境变量覆盖）
import os as _os
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_REPO = _HERE.parent
_APP = _Path(_os.environ.get("STAGE_RADAR_APP", str(_REPO.parent / "stage-radar-app")))
# --- 前导结束 ---

"""理解层实验的判定记录与指标计算。

判定者：agent 本人（扮演 SKILL §10/§12 规定的审核层）。
**明确标注：单标注者、非双盲**，是案例研究，不是统计结论。

判定规则（照 SKILL）：
  - 必须能说出这篇与**本课题画像**（cap1 methyltransferase / m6A / IVT 加帽效率）的具体关系；
  - 命中无关圈（vaccine / viral / antiviral）的丢弃；
  - 已开题未结题阶段：说不出"为什么可能与你竞争"的，不进候选列表。
"""
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

R = Path(str(_HERE))
data = json.loads((R / "review_input.json").read_text(encoding="utf-8"))
items = {it["n"]: it for it in data["items"]}

# ── 判定结果（n: (决定, 类别, 一句话理由)）────────────────────
KEEP = "保留"
DROP = "丢弃"
JUDGE = {
    1: (KEEP, "背景/机制", "mRNA 重新加帽(recapping)的酶学机制，与加帽酶改造同属一类，可作机制参考；但不构成竞争"),
    2: (KEEP, "强相关", "无活化剂化学合成 5'-5' 三磷酸加帽试剂——IVT 加帽的**化学路线**，与我们的酶法路线直接可比"),
    3: (DROP, "无关圈", "命中画像无关圈 viral；且是病毒 L 蛋白结构，非人源加帽酶改造"),
    4: (DROP, "离题", "非 AUG 翻译起始，与加帽无关"),
    5: (DROP, "不同生物学", "U6 snRNA 的 γ-单甲基磷酸帽，与 mRNA cap1 不是同一套加帽机制"),
    6: (DROP, "不同靶点", "eIF4E（帽结合蛋白）的共价抑制剂，属下游读取端，非加帽酶工程"),
    7: (DROP, "无关圈", "抗病毒药物开发，命中无关圈 antiviral；但见下方重要观察"),
    8: (DROP, "不同靶点", "eIF4E 旁系同源的功能分化，非加帽酶"),
    9: (DROP, "离题", "C9orf72 非 AUG 翻译起始"),
    10: (DROP, "离题", "家禽表观转录组综述，对象与加帽酶无关"),
    11: (DROP, "离题", "Resistin 与海马神经元代谢"),
    12: (DROP, "离题", "白色念珠菌交配型），与加帽无关"),
    13: (DROP, "离题", "真菌胞质分裂"),
    14: (DROP, "离题", "Cul4b 与生发中心 B 细胞"),
    15: (DROP, "离题", "真菌 ADP-核糖基化"),
    16: (DROP, "无关圈", "mRNA 疫苗，命中无关圈 vaccine"),
    17: (DROP, "离题", "非小细胞肺癌抗 PD-1 耐药"),
    18: (DROP, "离题", "亨廷顿病体细胞不稳定"),
    19: (DROP, "离题", "蜜蜂-植物生态网络"),
    20: (DROP, "无关圈", "干扰素抗病毒功能，命中 antiviral"),
    21: (DROP, "离题", "胞内适配体治疗"),
    22: (DROP, "无关圈", "碳纳米管 mRNA 疫苗递送，命中 vaccine"),
    23: (DROP, "离题", "SARS-CoV-2 免疫细胞播散"),
    24: (DROP, "离题", "糖尿病与癌症综述"),
    25: (DROP, "离题", "两栖动物多样性"),
    26: (DROP, "离题", "NLRP12 与 I 型干扰素信号"),
    27: (DROP, "离题", "胶质母细胞瘤 14q 缺失"),
    28: (DROP, "离题", "骨软骨瘤超声诊断"),
    29: (DROP, "缩写误命中", "「CAP」= 睡眠中的周期性交替模式(cyclic alternating pattern)，**纯缩写假阳性**"),
    30: (DROP, "离题", "流感 RNA 感知与免疫病理"),
    31: (DROP, "离题", "FOSL1 与银屑病"),
    32: (DROP, "离题", "空气污染颗粒毒性"),
    33: (DROP, "离题", "脓肿分枝杆菌与囊性纤维化"),
    34: (DROP, "离题", "ICU 肺炎采样"),
    35: (DROP, "离题", "雷公藤红素纳米粒递送"),
    36: (DROP, "离题", "TRIM27 与哮喘"),
    37: (KEEP, "强相关", "**PCIF1 催化的 cap 特异性 N6-腺苷甲基化（m6A）及其在 Cap-1 mRNA 合成中的应用**——正是本课题的两大卖点之一，且面向 mRNA 合成应用"),
    38: (DROP, "离题", "TRAF1 信号"),
    39: (DROP, "离题", "SMRT 测序诊断地贫"),
    40: (DROP, "离题", "结核传播筛查"),
    41: (DROP, "离题", "TCF3 与 H3K4 甲基化"),
    42: (DROP, "离题", "eIF5 模拟蛋白与起始密码子选择"),
    43: (DROP, "离题", "透明带蛋白 2"),
    44: (DROP, "离题", "斑马鱼抗血管生成药物筛选"),
}

assert len(JUDGE) == len(items), "判定条数 %d ≠ 候选条数 %d" % (len(JUDGE), len(items))

kept = [n for n, (d, _, _) in JUDGE.items() if d == KEEP]
gold_rel = [n for n, it in items.items() if it["gold"]]
# gold 漏掉的：人工判定为强相关但 gold 判无关
gold_missed = [n for n in kept if not items[n]["gold"]]
# gold 判相关但审核丢弃的
review_dropped_gold = [n for n in gold_rel if JUDGE[n][0] == DROP]

print("=" * 80)
print("理解层实验：竞品默认输出 → 审核层之后")
print("=" * 80)
print("原始候选（关键词监控会全部推给你）      ：%d 条" % len(items))
print("其中 gold 规则判定相关                  ：%d 条（精度 %.0f%%）" % (len(gold_rel), len(gold_rel) / len(items) * 100))
print("审核层保留                              ：%d 条" % len(kept))
print("→ 用户需要读的量下降                    ：%.0f%%" % ((1 - len(kept) / len(items)) * 100))
print()
print("保留的条目：")
for n in sorted(kept):
    d, cat, why = JUDGE[n]
    g = "gold判相关" if items[n]["gold"] else "**gold 漏判**"
    print("  %2d [%s][%s] %s" % (n, cat, g, items[n]["title"][:76]))
    print("      理由：%s" % why)
print()
print("=" * 80)
print("两个方向的错，都记下来：")
print("=" * 80)
print("A. 审核层丢掉、但 gold 规则判为相关的 %d 条：" % len(review_dropped_gold))
for n in review_dropped_gold:
    print("   %2d [%s] %s" % (n, JUDGE[n][1], items[n]["title"][:72]))
print("   → 说明 gold 测的是「话题相关」，审核测的是「与本课题是否有具体关系」，两者不等价。")
print()
print("B. gold 规则漏判、但审核层认为强相关的 %d 条：" % len(gold_missed))
for n in gold_missed:
    print("   %2d %s" % (n, items[n]["title"][:72]))
print("   → 原因是标题写作「Cap-1」（连字符），而 gold 词表里只有 cap1 / cap 1，**归一化没覆盖连字符变体**。")
print("   → 这是判定规则自身的盲点：规则会漏掉最关键的那一篇，理解层反而抓住了。")

# 类别统计（丢弃原因）
from collections import Counter
cats = Counter(cat for d, cat, _ in JUDGE.values() if d == DROP)
print()
print("丢弃原因分布：")
for c, k in cats.most_common():
    print("   %-14s %d 条" % (c, k))

json.dump({
    "n_raw": len(items), "n_gold_relevant": len(gold_rel), "n_kept": len(kept),
    "reduction_pct": (1 - len(kept) / len(items)) * 100,
    "gold_precision_raw": len(gold_rel) / len(items),
    "gold_precision_after_review": sum(1 for n in kept if items[n]["gold"]) / len(kept),
    "gold_recall_after_review": sum(1 for n in kept if items[n]["gold"]) / len(gold_rel),
    "gold_missed_by_rule": [{"n": n, "title": items[n]["title"]} for n in gold_missed],
    "review_dropped_gold": [{"n": n, "cat": JUDGE[n][1], "title": items[n]["title"]}
                            for n in review_dropped_gold],
    "drop_categories": dict(cats),
    "kept": [{"n": n, "cat": JUDGE[n][1], "why": JUDGE[n][2],
              "title": items[n]["title"], "gold": items[n]["gold"]} for n in sorted(kept)],
    "judgments": {str(n): {"decision": v[0], "cat": v[1], "why": v[2]} for n, v in JUDGE.items()},
}, (R / "review_result.json").open("w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("\n结果写入 review_result.json")
