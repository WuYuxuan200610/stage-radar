# --- 路径前导（由 _migrate_research.py 注入，使脚本可在任意机器运行）---
# _HERE 本目录；_REPO 本仓库根（含 benchmark.py）；_APP 桌面管线所在仓库（可用环境变量覆盖）
import os as _os
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_REPO = _HERE.parent
_APP = _Path(_os.environ.get("STAGE_RADAR_APP", str(_REPO.parent / "stage-radar-app")))
# --- 前导结束 ---

"""定向验证：拿几篇**确知有预印本**的论文，去索引里找。判明是索引缺内容还是匹配坏了。"""
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

R = Path(str(_HERE))
idx = json.loads((R / "preprint_index.json").read_text(encoding="utf-8"))
entries = idx["entries"]
keys = {e["k"] for e in entries}


def nk(t):
    t = (t or "").lower()
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# 已知有预印本的标题（来自前面 EPMC 结果里的 bioRxiv DOI 记录 + 期刊语料中的同名论文）
CASES = [
    "Visual LLM-guided consensus spatial domain detection with L-STAR",
    "Benchmarking segmentation methods for spatial transcriptomics",
    "An activator-free method for the synthesis of nucleotide 5'-5' triphosphate mRNA capping agent",
    "SuFEx Cyclization Enables DNA-Encoded Macrocyclic Peptide Libraries for Drug Discovery",
]

print("索引规模：%d 条，去重键 %d 个" % (len(entries), len(keys)))
print()
for c in CASES:
    k = nk(c)
    print("标题: %s" % c[:76])
    print("  键: %s" % k[:100])
    print("  精确命中索引？ %s" % (k in keys))
    # 模糊找：看索引里有没有前 40 字符相同的
    pre = k[:40]
    near = [e["k"] for e in entries if e["k"].startswith(pre)]
    print("  前缀 40 字符近邻：%d 个 %s" % (len(near), near[:2]))
    print()

# 索引里随机抽样，看看都是什么内容
print("索引随机抽样 6 条：")
rng = list(range(0, len(entries), max(1, len(entries) // 6)))[:6]
for i in rng:
    e = entries[i]
    print("  [%s] %s" % (e.get("server"), e["title"][:72]))

# 统计索引里 2026-08-25 那天的条目，看看有没有 L-STAR
aug25 = [e for e in entries if e.get("date") == "2026-08-25"]
print()
print("索引里 date=2026-08-25 的条目：%d 条" % len(aug25))
hits = [e for e in entries if "l star" in e["k"] or "consensus spatial" in e["k"]]
print("含 'consensus spatial' 或 'l star' 的条目：%d 条" % len(hits))
for e in hits[:3]:
    print("   %s | %s" % (e.get("date"), e["title"][:70]))
