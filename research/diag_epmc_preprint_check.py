# --- 路径前导（由 _migrate_research.py 注入，使脚本可在任意机器运行）---
# _HERE 本目录；_REPO 本仓库根（含 benchmark.py）；_APP 桌面管线所在仓库（可用环境变量覆盖）
import os as _os
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_REPO = _HERE.parent
_APP = _Path(_os.environ.get("STAGE_RADAR_APP", str(_REPO.parent / "stage-radar-app")))

def _find(rel):
    """优先在本仓找输入文件，找不到再回退到实现仓（_APP）。

    发布这两个文件是为了让 §9 的实验**在只克隆本仓时也能复现**；
    保留 _APP 回退是为了不破坏原开发环境。
    """
    for base in (_REPO, _APP):
        p = base / rel
        if p.exists():
            return p
    raise FileNotFoundError(
        "缺少 %s。它随本仓发布（若你手动克隆，请确认没有用 --filter 之类跳过）；"
        "也可用 STAGE_RADAR_APP 指向实现仓。" % rel)

# --- 前导结束 ---

"""独立验证「期刊论文有多少有预印本」——不依赖我自建的索引。

方法：抽 20 篇期刊论文（有摘要的），到 Europe PMC 按标题查，
看返回结果里有没有**预印本版本**（DOI 前缀 10.1101 / 10.64898，或 source 为 PPR）。

这条路径与自建索引完全独立，可以用来判断 1.9% 是真实的还是索引漏了。
"""
import json
import random
import sys
import time
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

R = Path(str(_HERE))
UA = {"User-Agent": "stage-radar/0.5 (mailto:stage-radar@example.org)"}
PREPRINT_PREFIXES = ("10.1101/", "10.64898/", "10.21203/", "10.31219/")

full = json.loads(_find("data/benchmark_journal_corpus.json")
                  .read_text(encoding="utf-8"))["items"]
pool = [d for d in full if (d.get("abstract") or "").strip() and len(d.get("title") or "") > 25]
random.seed(7)
sample = random.sample(pool, 20)

print("从「有摘要」的期刊论文里随机抽 %d 篇，用 Europe PMC 独立核查预印本存在性\n" % len(sample))

found = 0
for i, d in enumerate(sample, 1):
    q = d["title"][:95].replace('"', " ").strip()
    try:
        r = requests.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                         params={"query": 'TITLE:"%s"' % q, "format": "json",
                                 "pageSize": 10, "resultType": "core"},
                         headers=UA, timeout=40)
        r.raise_for_status()
        res = r.json().get("resultList", {}).get("result", [])
    except Exception as e:
        print("%2d. 查询失败 %s" % (i, type(e).__name__))
        continue

    pre = [x for x in res
           if (x.get("doi", "") or "").lower().startswith(PREPRINT_PREFIXES)
           or x.get("source") == "PPR"]
    tag = "有预印本" if pre else "无"
    if pre:
        found += 1
    print("%2d. [%s] %s" % (i, tag, d["title"][:66]))
    print("      EPMC 命中 %d 条" % len(res))
    for x in res[:2]:
        print("        - src=%-4s doi=%-30s %s" % (x.get("source"), (x.get("doi") or "")[:30],
                                                   (x.get("title") or "")[:52]))
    time.sleep(0.35)

print()
print("=" * 70)
print("独立核查结果：抽取 %d 篇，其中 Europe PMC 显示**存在预印本版本**的 %d 篇 → **%.0f%%**"
      % (len(sample), found, found / len(sample) * 100))
print("对比：我自建索引的匹配率是 1.9%")
print("若两者差距很大 → 说明我的索引或匹配仍有问题；若接近 → 说明这个比例本身就很低。")
