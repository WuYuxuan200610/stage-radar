# --- 路径前导（由 _migrate_research.py 注入，使脚本可在任意机器运行）---
# _HERE 本目录；_REPO 本仓库根（含 benchmark.py）；_APP 桌面管线所在仓库（可用环境变量覆盖）
import os as _os
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_REPO = _HERE.parent
_APP = _Path(_os.environ.get("STAGE_RADAR_APP", str(_REPO.parent / "stage-radar-app")))
# --- 前导结束 ---

"""实验：三路来源的覆盖对比（只盯预印本 / 只盯期刊 / 只看聚合库 / 全源）。

基准窗口与检索基准一致（2026-10-18..11-17），判定规则复用 benchmark.is_relevant（已修正连字符归一化）。
产出每路能找到的相关论文 DOI 集合，用于算交并集与"谁会漏掉谁"。
"""
import json
import sys
import time
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(_REPO))
import benchmark as B  # noqa: E402

OUT = Path(str(_HERE))
CACHE = OUT / "coverage_by_source.json"
UA = {"User-Agent": "stage-radar/0.5 (mailto:stage-radar@example.org)"}


def get(url, tries=6):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=90)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise last


def preprint_window(server):
    """按天分段抓基准窗口的预印本（含标题与摘要）。"""
    import datetime as dt
    s = dt.date(2026, 10, 18)
    u = dt.date(2026, 11, 17)
    out = []
    cur = s
    while cur <= u:
        end = min(cur + dt.timedelta(days=6), u)
        cursor = 0
        for _ in range(80):
            try:
                data = get("https://api.biorxiv.org/details/%s/%s/%s/%d"
                           % (server, cur.isoformat(), end.isoformat(), cursor))
            except Exception as e:
                print("    %s %s..%s 中断：%s" % (server, cur, end, type(e).__name__), flush=True)
                break
            batch = data.get("collection", [])
            if not batch:
                break
            for it in batch:
                out.append({"doi": (it.get("doi") or "").lower(),
                            "title": it.get("title") or "",
                            "abstract": it.get("abstract") or ""})
            total = int((data.get("messages") or [{}])[0].get("total") or 0)
            cursor += 30
            if cursor >= total:
                break
        cur = end + dt.timedelta(days=1)
    return out


def main():
    pre_cache = OUT / "coverage_preprints.json"
    if pre_cache.exists():
        pre = json.loads(pre_cache.read_text(encoding="utf-8"))
        print("预印本 %d 条（缓存）" % len(pre), flush=True)
    else:
        print("抓取预印本（基准窗口）…", flush=True)
        pre = preprint_window("biorxiv") + preprint_window("medrxiv")
        pre_cache.write_text(json.dumps(pre, ensure_ascii=False), encoding="utf-8")
        print("  预印本 %d 条（已缓存）" % len(pre), flush=True)

    if CACHE.exists():
        res = json.loads(CACHE.read_text(encoding="utf-8"))
    else:
        jc_path = Path(str(_APP / "data" / "benchmark_journal_corpus.json"))
        jc = json.loads(jc_path.read_text(encoding="utf-8"))
        print("  期刊语料 %d 条（缓存）" % len(jc["items"]), flush=True)

        res = {"per_topic": {}}
        for t in B.TOPICS:
            pre_hits = [d for d in pre if B.is_relevant(d, t)]
            jn_hits = [d for d in jc["items"] if B.is_relevant(d, t)]
            ep_hits = []
            for term in t["terms"]:
                for d in B.epmc('"%s"' % term, n=50):
                    if B.is_relevant(d, t):
                        ep_hits.append(d)
            def keys(ds):
                return sorted({(d.get("doi") or "").lower() or d.get("id") for d in ds if d})
            res["per_topic"][t["id"]] = {"preprint": keys(pre_hits),
                                         "journal": keys(jn_hits),
                                         "epmc": keys(ep_hits)}
            print("  %-26s 预印本 %3d | 期刊 %3d | EPMC %3d"
                  % (t["id"], len(keys(pre_hits)), len(keys(jn_hits)), len(keys(ep_hits))),
                  flush=True)
        CACHE.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")

    print()
    print("=" * 84)
    print("三路来源的覆盖对比（窗口 2026-10-18..11-17）")
    print("=" * 84)
    print("%-26s %8s %8s %8s %10s %12s" % ("课题", "预印本", "期刊", "EPMC", "全源并集", "单EPMC漏"))
    T = {"preprint": set(), "journal": set(), "epmc": set()}
    for tid, v in res["per_topic"].items():
        P, J, E = set(v["preprint"]), set(v["journal"]), set(v["epmc"])
        T["preprint"] |= P
        T["journal"] |= J
        T["epmc"] |= E
        U = P | J | E
        miss = (len(U) - len(E)) / len(U) * 100 if U else 0
        print("%-26s %8d %8d %8d %10d %11.0f%%"
              % (tid, len(P), len(J), len(E), len(U), miss))

    U = T["preprint"] | T["journal"] | T["epmc"]
    print("-" * 84)
    print("全源相关论文总数（去重）        ：%d 条" % len(U))
    for name, s in [("只盯预印本", T["preprint"]), ("只盯期刊", T["journal"]),
                    ("只看 Europe PMC", T["epmc"])]:
        miss = len(U - s) / len(U) * 100 if U else 0
        uniq = len(s - (T["preprint"] | T["journal"] | T["epmc"] - s))
        print("  %-16s 看到 %4d 条 → **漏掉 %.0f%%**（%d 条）"
              % (name, len(s), miss, len(U - s)))
    print()
    print("各路的独有贡献（只有这一路能看到的相关论文）：")
    print("  预印本独有：%d 条" % len(T["preprint"] - T["journal"] - T["epmc"]))
    print("  期刊独有  ：%d 条" % len(T["journal"] - T["preprint"] - T["epmc"]))
    print("  EPMC 独有 ：%d 条" % len(T["epmc"] - T["preprint"] - T["journal"]))
    print("  三路都有的：%d 条" % len(T["preprint"] & T["journal"] & T["epmc"]))

    json.dump({k: sorted(v) for k, v in T.items()} | {"union_size": len(U)},
              (OUT / "coverage_totals.json").open("w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
