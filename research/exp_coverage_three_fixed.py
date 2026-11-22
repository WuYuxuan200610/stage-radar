# --- 路径前导（由 _migrate_research.py 注入，使脚本可在任意机器运行）---
# _HERE 本目录；_REPO 本仓库根（含 benchmark.py）；_APP 桌面管线所在仓库（可用环境变量覆盖）
import os as _os
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_REPO = _HERE.parent
_APP = _Path(_os.environ.get("STAGE_RADAR_APP", str(_REPO.parent / "stage-radar-app")))
# --- 前导结束 ---

"""三路来源覆盖对比（修正版：**按归一化标题**匹配，而不是 DOI）。

为什么要改：同一项工作在预印本平台和期刊上是**两套 DOI**
（bioRxiv 的 10.1101/… vs 期刊的 10.1038/…），按 DOI 去重去不掉，
会把同一篇算成两篇，从而把"只盯某一路会漏掉多少"系统性夸大。
第一版就出现了"三路共同拥有 0 条"这种不可能的结果，说明键选错了。

这里改用归一化标题作为匹配键（标题一致即为同一项工作），并同时报告 DOI 口径作为对照。
"""
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(_REPO))
import benchmark as B  # noqa: E402

OUT = Path(str(_HERE))
EPMC_CACHE = OUT / "coverage_epmc_titles.json"


def tkey(title, doi=""):
    t = B._norm(title)
    if len(t) > 25:
        return "t:" + t
    return "d:" + (doi or "").lower()


def load_epmc():
    if EPMC_CACHE.exists():
        return json.loads(EPMC_CACHE.read_text(encoding="utf-8"))
    res = {}
    for t in B.TOPICS:
        hits = []
        for term in t["terms"]:
            for d in B.epmc('"%s"' % term, n=50):
                if B.is_relevant(d, t):
                    hits.append({"title": d["title"], "doi": (d.get("doi") or "").lower()})
        res[t["id"]] = hits
        print("  EPMC %-26s 相关 %d" % (t["id"], len(hits)), flush=True)
    EPMC_CACHE.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    return res


def main():
    pre = json.loads((OUT / "coverage_preprints.json").read_text(encoding="utf-8"))
    jc = json.loads(Path(str(_APP / "data" / "benchmark_journal_corpus.json"))
                    .read_text(encoding="utf-8"))["items"]
    ep = load_epmc()

    print()
    print("=" * 88)
    print("三路来源覆盖对比（按**归一化标题**匹配，窗口 2026-10-18..11-17）")
    print("=" * 88)
    print("%-26s %9s %9s %9s %11s %11s"
          % ("课题", "预印本", "期刊", "EPMC", "全源(去重)", "单EPMC漏"))
    TP, TJ, TE = set(), set(), set()
    rows = []
    for t in B.TOPICS:
        tid = t["id"]
        P = {tkey(d["title"], d.get("doi")) for d in pre if B.is_relevant(d, t)}
        J = {tkey(d["title"], d.get("doi")) for d in jc if B.is_relevant(d, t)}
        E = {tkey(d["title"], d.get("doi")) for d in ep.get(tid, [])}
        TP |= P
        TJ |= J
        TE |= E
        U = P | J | E
        miss = (len(U) - len(E)) / len(U) * 100 if U else 0
        rows.append((tid, len(P), len(J), len(E), len(U), miss))
        print("%-26s %9d %9d %9d %11d %10.0f%%"
              % (tid, len(P), len(J), len(E), len(U), miss))

    U = TP | TJ | TE
    print("-" * 88)
    print("全源相关论文总数（按标题去重）：**%d 条**" % len(U))
    print()
    print("%-20s %10s %12s %12s" % ("来源策略", "能看到", "漏掉比例", "漏掉条数"))
    for name, s in [("只盯预印本", TP), ("只盯期刊", TJ), ("只看 Europe PMC", TE), ("三路全要", U)]:
        miss = len(U - s)
        print("%-20s %10d %11.0f%% %12d"
              % (name, len(s), miss / len(U) * 100 if U else 0, miss))

    print()
    print("各路的**独有贡献**（只有这一路能看到的相关论文）：")
    print("  预印本独有：%3d 条（%.0f%%）" % (len(TP - TJ - TE), len(TP - TJ - TE) / len(U) * 100))
    print("  期刊独有  ：%3d 条（%.0f%%）" % (len(TJ - TP - TE), len(TJ - TP - TE) / len(U) * 100))
    print("  EPMC 独有 ：%3d 条（%.0f%%）" % (len(TE - TP - TJ), len(TE - TP - TJ) / len(U) * 100))
    print()
    print("两两重叠：")
    print("  预印本 ∩ 期刊 ：%d 条  ← 同一项工作同时有两套记录" % len(TP & TJ))
    print("  预印本 ∩ EPMC ：%d 条" % len(TP & TE))
    print("  期刊   ∩ EPMC ：%d 条" % len(TJ & TE))
    print("  三路都有      ：%d 条" % len(TP & TJ & TE))

    json.dump({"rows": rows, "union": len(U),
               "only_preprint": len(TP), "only_journal": len(TJ), "only_epmc": len(TE),
               "unique_preprint": len(TP - TJ - TE), "unique_journal": len(TJ - TP - TE),
               "unique_epmc": len(TE - TP - TJ),
               "overlap_pj": len(TP & TJ), "overlap_pe": len(TP & TE),
               "overlap_je": len(TJ & TE), "overlap_all": len(TP & TJ & TE)},
              (OUT / "coverage_three_summary.json").open("w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
