"""放大样本测图版可达率：走**真实检索路径**（Europe PMC / PubMed / Crossref 刊源），
统计每条来源里"能合法取到 Fig.1"的比例。

为什么必须分来源：三类来源的图版可达率**结构上不同**——
  - Europe PMC / PubMed：OA 且被 PMC 收录的才有 PMCID，才可能取到图；
  - bioRxiv / medRxiv：不进 PMC，但正文图公开可访问（需另写解析）；
  - Crossref 刊源：只给元数据，**任何情况下都没有图**。
所以"整体可达率"会被来源构成严重稀释，必须分开报。
"""
import re
import sys
import time
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UA = {"User-Agent": "stage-radar/0.5 (mailto:stage-radar@example.org)"}
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"

# 真实课题查询词（取自两个课题的画像）
QUERIES = [
    'TITLE:"mRNA capping"', 'TITLE:"cap1 methyltransferase"', 'TITLE:"m6A"',
    'TITLE:"macrocyclic peptide"', 'TITLE:"peptide cyclization"',
    'TITLE:"DNA-encoded library"', 'TITLE:"spatial transcriptomics"',
    'TITLE:"prime editing"',
]

print("=== 一、Europe PMC 返回的条目里，带 PMCID 的比例 ===")
tot = pmc = 0
samples = []
for q in QUERIES:
    expr = '(%s) AND FIRST_PDATE:[2026-10-01 TO 2026-11-18] sort_date:y' % q
    try:
        r = requests.get(EPMC + "/search",
                         params={"query": expr, "format": "json", "pageSize": 15,
                                 "resultType": "core"}, headers=UA, timeout=30)
        res = r.json().get("resultList", {}).get("result", [])
    except Exception as e:
        print("  %-34s 查询失败 %s" % (q, type(e).__name__))
        continue
    n_pmc = sum(1 for x in res if x.get("pmcid"))
    tot += len(res)
    pmc += n_pmc
    print("  %-34s 返回 %2d 条，带 PMCID %2d 条（%3.0f%%）"
          % (q, len(res), n_pmc, n_pmc / len(res) * 100 if res else 0))
    samples.extend([x for x in res if x.get("pmcid")][:3])
    time.sleep(0.3)

print()
print("Europe PMC 合计：%d 条中 %d 条带 PMCID → **%.0f%%**" % (tot, pmc, pmc / tot * 100 if tot else 0))

print()
print("=== 二、带 PMCID 的条目里，能取到 <fig> 的比例 ===")
ok = figged = 0
for x in samples[:24]:
    pmcid = x.get("pmcid")
    try:
        r = requests.get("%s/%s/fullTextXML" % (EPMC, pmcid), headers=UA, timeout=40)
        if r.status_code != 200:
            ok += 1
            continue
        ok += 1
        n = len(re.findall(r"<fig\b", r.text))
        if n:
            figged += 1
    except Exception:
        pass
    time.sleep(0.3)
print("  抽查 %d 条：全文可取 %d 条，其中含 <fig> 的 %d 条 → **%.0f%%**"
      % (len(samples[:24]), ok, figged, figged / max(ok, 1) * 100))

print()
print("=== 三、另外两类来源的结构性上限 ===")
print("  bioRxiv / medRxiv 预印本：不进 PMC，EPMC 记录里没有 pmcid")
try:
    r = requests.get(EPMC + "/search",
                     params={"query": '(TITLE:"macrocyclic peptide") AND SRC:PPR '
                                      'AND FIRST_PDATE:[2026-10-01 TO 2026-11-18]',
                             "format": "json", "pageSize": 15, "resultType": "core"},
                     headers=UA, timeout=30)
    res = r.json().get("resultList", {}).get("result", [])
    n_pmc = sum(1 for x in res if x.get("pmcid"))
    print("    预印本样本 %d 条，带 PMCID %d 条 → **%.0f%%**"
          % (len(res), n_pmc, n_pmc / len(res) * 100 if res else 0))
except Exception as e:
    print("    查询失败 %s" % type(e).__name__)
print("  Crossref 刊源（51 本）：只返回元数据，**结构上 0%**，无全文入口")
