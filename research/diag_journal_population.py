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

"""查清期刊语料里到底混了多少非研究内容——这决定了"缺预印本比例"测的是谁。

Nature/Science 在 Crossref 里的 deposits 包含大量新闻、编者按、简报、书评，
这些东西**永远不会有预印本**，混进来会把比例压得极低。
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

R = Path(str(_HERE))
jc = json.loads((R / "journal_titles_for_preprint_check.json").read_text(encoding="utf-8"))
full = json.loads(_find("data/benchmark_journal_corpus.json")
                  .read_text(encoding="utf-8"))["items"]

print("期刊语料：%d 条（完整字段），%d 条（含标题+期刊 id）" % (len(full), len(jc)))
print("完整语料的字段：%s" % sorted(full[0].keys()))
print()

has_abs = sum(1 for d in full if (d.get("abstract") or "").strip())
print("有摘要的条目：%d / %d = %.0f%%" % (has_abs, len(full), has_abs / len(full) * 100))
print()

# 按期刊看"有摘要"比例，判断哪些刊混了新闻
by_j = Counter()
by_j_abs = Counter()
for d in full:
    j = d.get("journal_id", "?")
    by_j[j] += 1
    if (d.get("abstract") or "").strip():
        by_j_abs[j] += 1
print("%-22s %8s %10s %8s" % ("期刊", "条目", "有摘要", "比例"))
for j, n in by_j.most_common(14):
    a = by_j_abs[j]
    print("%-22s %8d %10d %7.0f%%" % (j, n, a, a / n * 100))

print()
NEWSY = re.compile(r"^(briefing|news|editorial|correspondence|career|books?|podcast|"
                   r"how to|q&a|obituary|spotlight|technology feature|world view|"
                   r"news feature|research highlight|nature index)", re.I)
newsy = [d for d in full if NEWSY.match(d["title"] or "")]
print("标题疑似新闻/编者按的：%d 条（%.0f%%）" % (len(newsy), len(newsy) / len(full) * 100))
for d in newsy[:8]:
    print("   [%s] %s" % (d.get("journal_id"), d["title"][:78]))

print()
# 用"有摘要"当研究论文的近似判据，重估人群规模
research = [d for d in full if (d.get("abstract") or "").strip()]
print("若以「有摘要」近似研究论文：%d 条" % len(research))
titles = {re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", (d["title"] or "").lower())).strip()
          for d in research}
idx = json.loads((R / "preprint_index.json").read_text(encoding="utf-8"))
pre = {e["k"] for e in idx["entries"]}
titles = {t for t in titles if len(t) > 20}
hit = len(titles & pre)
print("其中能找到预印本的：%d → **%.1f%%**" % (hit, hit / len(titles) * 100 if titles else 0))
