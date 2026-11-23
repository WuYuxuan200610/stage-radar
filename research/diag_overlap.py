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

"""定位「期刊 ∩ EPMC = 0」的真实原因。

已知事实：抽查 13 条期刊语料相关论文，有 9 条能在 EPMC 按标题找到，日期也在窗口内。
所以交集不可能是 0。逐步查出是键的问题、还是取样范围的问题。
"""
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(_REPO))
import benchmark as B  # noqa: E402

OUT = Path(str(_HERE))
print("benchmark.WINDOW:", B.WINDOW_FROM, "..", B.WINDOW_TO)

jc = json.loads(_find("data/benchmark_journal_corpus.json")
                .read_text(encoding="utf-8"))["items"]
ep = json.loads((OUT / "coverage_epmc_titles.json").read_text(encoding="utf-8"))

t = [x for x in B.TOPICS if x["id"] == "spatial-transcriptomics"][0]

jn_titles = {}
for d in jc:
    if B.is_relevant(d, t):
        jn_titles[B._norm(d["title"])] = d["title"]

ep_titles = {}
for d in ep.get(t["id"], []):
    ep_titles[B._norm(d["title"])] = d["title"]

print("\n期刊相关条数 =", len(jn_titles), " EPMC相关条数 =", len(ep_titles))
inter = set(jn_titles) & set(ep_titles)
print("归一化标题交集 =", len(inter))
for k in list(inter)[:5]:
    print("   交集: %s" % jn_titles[k][:70])

# 逐条检查期刊标题是否出现在 EPMC 的【原始结果】里（未过滤相关）
print("\n逐条回查：期刊相关论文是否出现在该课题 EPMC 原始检索结果里")
raw_titles = set()
for term in t["terms"]:
    for d in B.epmc('"%s"' % term, n=50):
        raw_titles.add(B._norm(d["title"]))
print("  EPMC 原始结果去重标题数 =", len(raw_titles))
hit = sum(1 for k in jn_titles if k in raw_titles)
print("  期刊相关论文中，出现在 EPMC 原始结果里的 = %d / %d" % (hit, len(jn_titles)))

miss = [v for k, v in jn_titles.items() if k not in raw_titles]
print("\n  没出现在 EPMC 结果里的期刊论文（前 6 条）：")
for m in miss[:6]:
    print("    - %s" % m[:76])

# 关键检查：EPMC 检索是不是被 n=50 截断了？
print("\n检查 EPMC 各词的命中总数（看是不是窗口没生效或截断太狠）：")
for term in t["terms"]:
    import requests
    expr = '("%s") AND FIRST_PDATE:[%s TO %s] sort_date:y' % (term, B.WINDOW_FROM, B.WINDOW_TO)
    r = requests.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                     params={"query": expr, "format": "json", "pageSize": 1, "resultType": "lite"},
                     headers={"User-Agent": "stage-radar/0.5"}, timeout=40)
    r.raise_for_status()
    print("   %-30s hitCount=%s（我们只取了前 50）" % (term, r.json().get("hitCount")))
