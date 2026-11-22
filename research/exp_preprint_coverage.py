# --- 路径前导（由 _migrate_research.py 注入，使脚本可在任意机器运行）---
# _HERE 本目录；_REPO 本仓库根（含 benchmark.py）；_APP 桌面管线所在仓库（可用环境变量覆盖）
import os as _os
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_REPO = _HERE.parent
_APP = _Path(_os.environ.get("STAGE_RADAR_APP", str(_REPO.parent / "stage-radar-app")))
# --- 前导结束 ---

"""最终版：期刊论文中「有预印本」的比例。

修掉了两个真实错误：
  ① 归一化不一致——索引把标题做了**全标点剥离**，而 B._norm 只拉平连字符，
     逗号/句号/冒号/撇号都留着 → 两边字符串对不上，匹配率被凭空压低。
     现在两边统一用 index_style_norm。
  ② 人群混杂——Nature/Science/PNAS 是**跨学科**刊，语料里混着化学、材料、物理、地学、
     社科、勘误、新闻，这些领域预印本文化本就薄弱。所以除了全样本，还按家族分开报。

窗口与其余实验一致：期刊 2026-10-18..11-17；预印本索引 2026-04..11。
匹配率是**下界**（更早挂出的预印本不在索引里）。
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(_REPO))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

R = Path(str(_HERE))
CAT = json.loads(Path(str(_APP / "sources_catalog.json"))
                 .read_text(encoding="utf-8"))
CHEM = {"acs", "wiley"}


def nk(t):
    """与 build_preprint_index.py 完全一致的归一化：剥掉所有非字母数字。"""
    t = (t or "").lower()
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def main():
    idx = json.loads((R / "preprint_index.json").read_text(encoding="utf-8"))
    pre = {e["k"] for e in idx["entries"]}
    print("预印本索引：%d 条，去重标题 %d 个（2026-04 .. 2026-11）" % (len(idx["entries"]), len(pre)))

    jc = json.loads(Path(str(_APP / "data" / "benchmark_journal_corpus.json"))
                    .read_text(encoding="utf-8"))["items"]
    # 基准语料只带刊名、没有 journal_id，所以按刊名反查家族
    fam_of = {j["id"]: j["familyId"] for j in CAT["journals"]}
    fam_by_name = {j["name"]: j["familyId"] for j in CAT["journals"]}
    fam_name = {f["id"]: f["nameZh"] for f in CAT["families"]}
    print("期刊语料：%d 条（窗口 2026-10-18..11-17）" % len(jc))

    by_fam = defaultdict(lambda: {"total": 0, "with_pre": 0})
    seen = set()
    for d in jc:
        k = nk(d.get("title"))
        if len(k) < 20 or k in seen:
            continue
        seen.add(k)
        f = fam_by_name.get(d.get("journal", ""), "?")
        by_fam[f]["total"] += 1
        if k in pre:
            by_fam[f]["with_pre"] += 1

    tot = sum(v["total"] for v in by_fam.values())
    wp = sum(v["with_pre"] for v in by_fam.values())

    print()
    print("=" * 80)
    print("期刊论文中能找到对应预印本的比例（统一归一化后）")
    print("=" * 80)
    print("%-24s %9s %11s %10s" % ("家族", "论文数", "有预印本", "比例"))
    for f, v in sorted(by_fam.items(), key=lambda kv: -kv[1]["total"]):
        if not v["total"]:
            continue
        print("%-24s %9d %11d %9.1f%%"
              % (fam_name.get(f, f), v["total"], v["with_pre"], v["with_pre"] / v["total"] * 100))
    print("-" * 80)
    print("%-24s %9d %11d %9.1f%%" % ("全样本", tot, wp, wp / tot * 100))

    chem = sum(v["total"] for f, v in by_fam.items() if f in CHEM)
    cp = sum(v["with_pre"] for f, v in by_fam.items() if f in CHEM)
    bio, bp = tot - chem, wp - cp
    print()
    print("按学科粗分：")
    print("  化学刊（ACS + Angew）        ：%5d 篇，有预印本 %4d → **%.1f%%**"
          % (chem, cp, cp / chem * 100 if chem else 0))
    print("  其余（Nature/Cell/Science/PNAS/Vita，**含大量跨学科**）：%5d 篇，有预印本 %4d → **%.1f%%**"
          % (bio, bp, bp / bio * 100 if bio else 0))
    print()
    print("→ 全样本 **%.1f%%** 的期刊论文能找到对应预印本。"
          % (wp / tot * 100))
    print("→ 也就是说：**只盯预印本，绝大多数正式发表的工作根本看不到。**")

    json.dump({"window": "2026-10-18..11-17", "index": "2026-04..2026-11",
               "by_family": {fam_name.get(k, k): v for k, v in by_fam.items()},
               "total": tot, "with_preprint": wp,
               "chem": {"total": chem, "with_preprint": cp},
               "bio": {"total": bio, "with_preprint": bp}},
              (R / "preprint_coverage_summary.json").open("w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("\n写入 preprint_coverage_summary.json")


if __name__ == "__main__":
    main()
