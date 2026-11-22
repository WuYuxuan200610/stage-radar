# --- 路径前导（由 _migrate_research.py 注入，使脚本可在任意机器运行）---
# _HERE 本目录；_REPO 本仓库根（含 benchmark.py）；_APP 桌面管线所在仓库（可用环境变量覆盖）
import os as _os
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_REPO = _HERE.parent
_APP = _Path(_os.environ.get("STAGE_RADAR_APP", str(_REPO.parent / "stage-radar-app")))
# --- 前导结束 ---

"""查清「期刊 ∩ EPMC = 0」：是没被收录，还是时间定义错配？

抽查若干「期刊语料里判为相关」的论文，按标题回查 Europe PMC（**不限时间窗**），
看它是否存在、以及 EPMC 给的首发日期是什么。
"""
import json
import sys
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(_REPO))
import benchmark as B  # noqa: E402

UA = {"User-Agent": "stage-radar/0.5 (mailto:stage-radar@example.org)"}
jc = json.loads(Path(str(_APP / "data" / "benchmark_journal_corpus.json"))
                .read_text(encoding="utf-8"))["items"]


def epmc_any(title, n=3):
    """不限时间窗，按标题找。返回 (hitCount, [(title, firstPublicationDate, doi)])。"""
    q = title[:90].replace('"', " ").strip()
    r = requests.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                     params={"query": 'TITLE:"%s"' % q, "format": "json",
                             "pageSize": n, "resultType": "core"},
                     headers=UA, timeout=40)
    r.raise_for_status()
    j = r.json()
    return j.get("hitCount", 0), [(x.get("title", "")[:60], x.get("firstPublicationDate", ""),
                                   x.get("doi", "")) for x in
                                  j.get("resultList", {}).get("result", [])]


# 取几个课题里判为相关的期刊论文（有摘要优先）
samples = []
for t in B.TOPICS:
    hits = [d for d in jc if B.is_relevant(d, t)]
    for h in hits[:2]:
        samples.append((t["id"], h))
    if len(samples) >= 12:
        break

print("抽查 %d 条「期刊语料判为相关」的论文，去 Europe PMC 按标题回查（不限时间窗）：\n" % len(samples))
exist = miss = 0
for tid, h in samples:
    try:
        cnt, got = epmc_any(h["title"])
    except Exception as e:
        print("[%s] 查询失败：%s" % (tid, e))
        continue
    created = (h.get("created") or "")[:10]
    if cnt:
        exist += 1
        print("[%s] EPMC 命中 %d 条 | 期刊语料 created=%s" % (tid, cnt, created))
        print("    刊源标题: %s" % h["title"][:74])
        for gt, gd, gdoi in got[:1]:
            print("    EPMC  : %s | firstPub=%s | doi=%s" % (gt, gd, gdoi[:34]))
    else:
        miss += 1
        print("[%s] **EPMC 完全找不到** | created=%s" % (tid, created))
        print("    %s" % h["title"][:74])
    print()

print("=" * 76)
print("抽查结果：EPMC 能按标题找到 %d 条，找不到 %d 条" % (exist, miss))
print("→ 若多数能按标题找到，说明「期刊 ∩ EPMC = 0」不是收录问题，而是**时间口径错配**：")
print("   Crossref 的 created 是**入库时间**，Europe PMC 的 FIRST_PDATE 是**首发时间**，")
print("   同一篇论文在两个来源里可能落在不同窗口，跨来源用同一个日期窗比较会系统性错配。")
