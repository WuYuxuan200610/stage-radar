# --- 路径前导（由 _migrate_research.py 注入，使脚本可在任意机器运行）---
# _HERE 本目录；_REPO 本仓库根（含 benchmark.py）；_APP 桌面管线所在仓库（可用环境变量覆盖）
import os as _os
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_REPO = _HERE.parent
_APP = _Path(_os.environ.get("STAGE_RADAR_APP", str(_REPO.parent / "stage-radar-app")))
# --- 前导结束 ---

"""实验：竞品默认形态（关键词监控）每天推给你的东西，有多少是噪音。

做法：对基准的每个 (课题, 卖点词)，按**全文关键词**检索（这就是竞品默认行为），
取前 20 条，用同一套相关概念规则判定，统计"推给你的条数 vs 真正相关的条数"。

再对比同一批结果经过我们的排序/过滤后，用户实际要读多少。

产出：控制台表格 + 图。
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_HERE))
import benchmark as B  # noqa: E402

OUT = Path(str(_HERE))
OUT.mkdir(parents=True, exist_ok=True)
CACHE = OUT / "keyword_noise.json"


def collect():
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    rows = []
    for t in B.TOPICS:
        for term in t["terms"]:
            items = B.epmc(B.system_query("fulltext", t, term), n=20)
            rel = [1 if B.is_relevant(d, t) else 0 for d in items]
            rows.append({"topic": t["id"], "term": term, "n": len(items),
                         "relevant": int(sum(rel)), "flags": rel,
                         "titles": [d["title"][:80] for d in items]})
            print("  %-26s %-32s 推 %2d 条，相关 %2d 条" % (t["id"], term, len(items), sum(rel)),
                  flush=True)
    CACHE.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows


def main():
    rows = collect()
    n = len(rows)
    delivered = sum(r["n"] for r in rows)
    relevant = sum(r["relevant"] for r in rows)
    print()
    print("=" * 70)
    print("关键词监控（竞品默认形态）：N=%d 组查询" % n)
    print("=" * 70)
    print("总共推给你        ：%d 条" % delivered)
    print("其中真正相关      ：%d 条" % relevant)
    print("与你课题无关      ：%d 条" % (delivered - relevant))
    print("→ **噪音率 %.0f%%**（每推 10 条，约 %.1f 条是无关的）"
          % ((delivered - relevant) / delivered * 100,
             (delivered - relevant) / delivered * 10))
    print("→ 平均每组查询要读 %.1f 条，才等到 %.1f 条有用的"
          % (delivered / n, relevant / n))

    empty = sum(1 for r in rows if r["n"] == 0)
    print("→ 另有 %d/%d 组查询返回 0 条（关键词太窄就什么都收不到）" % (empty, n))

    # 前 5 条里的噪音：用户最可能只扫前面几条
    d5 = sum(min(r["n"], 5) for r in rows)
    r5 = sum(sum(r["flags"][:5]) for r in rows)
    print("\n只扫前 5 条时：推给你 %d 条，其中相关 %d 条 → 噪音率 %.0f%%"
          % (d5, r5, (d5 - r5) / d5 * 100 if d5 else 0))

    json.dump({"n": n, "delivered": delivered, "relevant": relevant,
               "noise_rate": (delivered - relevant) / delivered if delivered else 0,
               "top5_delivered": d5, "top5_relevant": r5,
               "empty_queries": empty,
               "per_topic": {t["id"]: {"delivered": sum(r["n"] for r in rows if r["topic"] == t["id"]),
                                       "relevant": sum(r["relevant"] for r in rows if r["topic"] == t["id"])}
                             for t in B.TOPICS}},
              (OUT / "keyword_noise_summary.json").open("w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
