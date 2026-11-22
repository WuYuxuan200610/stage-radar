# --- 路径前导（由 _migrate_research.py 注入，使脚本可在任意机器运行）---
# _HERE 本目录；_REPO 本仓库根（含 benchmark.py）；_APP 桌面管线所在仓库（可用环境变量覆盖）
import os as _os
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_REPO = _HERE.parent
_APP = _Path(_os.environ.get("STAGE_RADAR_APP", str(_REPO.parent / "stage-radar-app")))
# --- 前导结束 ---

"""专项核查 Nature / Cell / Science 子集的预印本比例（生命科学里预印本本应很常见）。

同时打印抽样标题，确认抽到的到底是不是研究论文。
"""
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

R = Path(str(_HERE))
UA = {"User-Agent": "stage-radar/0.5 (mailto:stage-radar@example.org)"}
PRE = ("10.1101/", "10.64898/", "10.21203/")
BIO_FAMILIES = {"nature", "cell", "aaas", "pnas", "vita"}

cat = json.loads(Path(str(_APP / "sources_catalog.json"))
                 .read_text(encoding="utf-8"))
fam = {j["id"]: j["familyId"] for j in cat["journals"]}

jc = json.loads((R / "journal_titles_for_preprint_check.json").read_text(encoding="utf-8"))
pool = [d for d in jc
        if fam.get(d.get("journal_id", ""), "") in BIO_FAMILIES
        and len(d.get("title") or "") > 25]
print("生物/综合家族（Nature/Cell/Science/PNAS/Vita）条目：%d 条" % len(pool))

random.seed(11)
sample = random.sample(pool, 18)
print("随机抽 18 条，去 Europe PMC 查预印本版本：\n")

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
           if (x.get("doi", "") or "").lower().startswith(PRE) or x.get("source") == "PPR"]
    if pre:
        found += 1
    print("%2d. [%s][%s] %s" % (i, "有预印本" if pre else "  无  ",
                                d.get("journal_id"), d["title"][:60]))
    for x in res[:2]:
        print("      src=%-4s %s" % (x.get("source"), (x.get("title") or "")[:56]))
    time.sleep(0.35)

print()
print("=" * 72)
print("生物/综合家族抽样：%d 篇中 %d 篇有预印本 → **%.0f%%**"
      % (len(sample), found, found / len(sample) * 100))
print("（自建索引对全体的匹配率是 1.9%；若这里明显更高，说明差别主要在学科构成）")
