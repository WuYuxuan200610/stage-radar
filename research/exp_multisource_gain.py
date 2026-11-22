# --- 路径前导（由 _migrate_research.py 注入，使脚本可在任意机器运行）---
# _HERE 本目录；_REPO 本仓库根（含 benchmark.py）；_APP 桌面管线所在仓库（可用环境变量覆盖）
import os as _os
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_REPO = _HERE.parent
_APP = _Path(_os.environ.get("STAGE_RADAR_APP", str(_REPO.parent / "stage-radar-app")))
# --- 前导结束 ---

"""实验：多源相比单源，多找到多少相关论文。

基准里的 Recall 只算了 Europe PMC **单一来源内部**。真实系统还查 53 本已核验刊 + 预印本。
这里量化：改用全源之后，能多看到多少相关论文（且这些在单源里根本找不到）。

竞品大多只有一个来源（arXiv 或 PubMed 或某本刊），这个差值就是它们的结构性缺口。
"""
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_APP))
import benchmark as B  # noqa: E402

OUT = Path(str(_HERE))
CACHE = OUT / "multisource_gain.json"
WINDOW = ("2026-10-18", "2026-11-17")


def epmc_dois(topic):
    """Europe PMC 单源能看到的相关论文 DOI 集合（宽口径：全文检索，避免低估它）。"""
    seen = set()
    for term in topic["terms"]:
        for d in B.epmc(f'"{term}"', n=50):
            if B.is_relevant(d, topic):
                k = (d.get("doi") or "").lower() or d.get("id")
                if k:
                    seen.add(k)
    return seen


def journal_relevant(topic_id):
    """从 benchmark 结果里取「53 刊语料中该课题的相关论文」（已缓存，不重新抓）。"""
    p = Path(str(_REPO / "benchmark_results.json"))
    data = json.loads(p.read_text(encoding="utf-8"))
    jc = data.get("journal_coverage") or {}
    hits = (jc.get("_hits") or {}).get(topic_id, [])
    return [(h.get("doi") or "").lower() or h.get("id") for h in hits]


def main():
    if CACHE.exists():
        res = json.loads(CACHE.read_text(encoding="utf-8"))
    else:
        res = {}
        for t in B.TOPICS:
            print("  课题 %s …" % t["id"], flush=True)
            ep = epmc_dois(t)
            jn = set(journal_relevant(t["id"]))
            res[t["id"]] = {"epmc": sorted(ep), "journal": sorted(jn)}
        CACHE.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")

    print()
    print("=" * 78)
    print("多源 vs 单源：能多看到多少相关论文（窗口 %s..%s）" % WINDOW)
    print("=" * 78)
    print("%-26s %10s %10s %12s %12s" % ("课题", "仅EPMC", "仅期刊", "两源合计", "期刊新增占比"))
    tot_ep = tot_jn = tot_new = 0
    for tid, v in res.items():
        ep, jn = set(v["epmc"]), set(v["journal"])
        new = jn - ep
        tot_ep += len(ep)
        tot_jn += len(jn)
        tot_new += len(new)
        pct = (len(new) / len(jn) * 100) if jn else 0
        print("%-26s %10d %10d %12d %11.0f%%" % (tid, len(ep), len(jn), len(ep | jn), pct))
    union = tot_ep + tot_new
    print("-" * 78)
    print("合计：Europe PMC 单源相关 %d 条；53 刊额外带来 %d 条**在单源里找不到**的相关论文"
          % (tot_ep, tot_new))
    print("→ 只盯单源会漏掉 %.0f%%" % (tot_new / union * 100 if union else 0))
    json.dump({"per_topic": res, "totals": {"epmc": tot_ep, "journal": tot_jn, "new": tot_new}},
              (OUT / "multisource_gain_summary.json").open("w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
