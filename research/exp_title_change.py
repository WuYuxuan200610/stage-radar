# --- 路径前导（由 _migrate_research.py 注入，使脚本可在任意机器运行）---
# _HERE 本目录；_REPO 本仓库根（含 benchmark.py）；_APP 桌面管线所在仓库（可用环境变量覆盖）
import os as _os
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_REPO = _HERE.parent
_APP = _Path(_os.environ.get("STAGE_RADAR_APP", str(_REPO.parent / "stage-radar-app")))
# --- 前导结束 ---

"""量化标题匹配的偏差：预印本 → 见刊，标题会不会改？

如果标题会改，靠"标题一致"匹配就会漏掉这些论文，把"有预印本比例"压低。
用 bioRxiv 的 published 字段（给出见刊版 DOI）去 Crossref 取见刊版标题，与预印本标题比对。
"""
import json
import random
import re
import sys
import time
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

R = Path(str(_HERE))
UA = {"User-Agent": "stage-radar/0.5 (mailto:stage-radar@example.org)"}


def nk(t):
    t = (t or "").lower()
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


idx = json.loads((R / "preprint_index.json").read_text(encoding="utf-8"))
pub = [e for e in idx["entries"]
       if e.get("published") and e["published"] != "NA" and "10." in e["published"]]
print("索引中「已给出见刊 DOI」的预印本：%d 条" % len(pub))

random.seed(3)
sample = random.sample(pub, 45)
same = diff = fail = 0
examples = []
for e in sample:
    doi = e["published"].split()[0]
    try:
        r = requests.get("https://api.crossref.org/works/%s" % doi,
                         params={"mailto": "stage-radar@example.org"},
                         headers=UA, timeout=30)
        if r.status_code != 200:
            fail += 1
            continue
        titles = r.json()["message"].get("title") or []
        jt = nk(titles[0] if titles else "")
    except Exception:
        fail += 1
        continue
    if not jt:
        fail += 1
        continue
    if jt == e["k"]:
        same += 1
    else:
        diff += 1
        if len(examples) < 4:
            examples.append((e["title"][:64], (titles[0] if titles else "")[:64]))
    time.sleep(0.15)

n = same + diff
print()
print("=" * 74)
print("预印本 → 见刊 的**标题一致性**（抽样 %d 条，成功 %d 条，失败 %d）" % (len(sample), n, fail))
print("=" * 74)
print("标题完全一致：%d 条 → **%.0f%%**" % (same, same / n * 100 if n else 0))
print("标题有改动  ：%d 条 → %.0f%%" % (diff, diff / n * 100 if n else 0))
if examples:
    print("\n改动的例子：")
    for a, b in examples:
        print("  预印本: %s" % a)
        print("  见刊版: %s" % b)
print()
print("→ 结论：靠标题匹配会漏掉约 %.0f%% 的配对，所以 2.3%% 是**下界**。"
      % (diff / n * 100 if n else 0))

json.dump({"sampled": len(sample), "checked": n, "same_title": same,
           "different_title": diff, "failed": fail,
           "same_rate": same / n if n else 0},
          (R / "title_change_summary.json").open("w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
