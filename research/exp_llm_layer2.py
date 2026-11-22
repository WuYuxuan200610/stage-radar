# --- 路径前导（由 _migrate_research.py 注入，使脚本可在任意机器运行）---
# _HERE 本目录；_REPO 本仓库根（含 benchmark.py）；_APP 桌面管线所在仓库（可用环境变量覆盖）
import os as _os
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_REPO = _HERE.parent
_APP = _Path(_os.environ.get("STAGE_RADAR_APP", str(_REPO.parent / "stage-radar-app")))
# --- 前导结束 ---

"""理解层实验（通用版）：对任意真实课题跑「竞品默认输出 → agent 审核」。

用法：python exp_llm_layer2.py <project_id>
产出：_research/review_input_<project_id>.json
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
# 主档路径不含任何个人目录：默认取当前用户的 DSH 存储位置，可用环境变量覆盖
REG = Path(os.environ.get("STAGE_RADAR_REGISTRY",
           Path.home() / ".dsh" / "storages" / "stage-radar" / "project-registry.json"))

# 每个课题的 gold 词表（先定后用；故意包含**查询词里没有的**概念，避免判定退化成查询的复制品）
GOLD = {
    "peptide-macrocyclization": [
        "macrocyclization", "macrocyclic peptide", "cyclic peptide", "peptide cyclization",
        "stapled peptide", "head-to-tail", "ycao", "lanthipeptide", "cyclotide",
        "ripp", "n-to-c", "macrolactam", "cyclization",
    ],
    "trna-live-detection": [
        "trna detection", "trna sensor", "trna imaging", "fluorescent trna",
        "trna probe", "trna labeling", "trna labelling", "spinach", "fluorogenic",
        "molecular beacon", "trna modification",
    ],
}
NEGATIVE = {
    "peptide-macrocyclization": ["polymerization"],
    "trna-live-detection": [],
}


def norm(s):
    s = (s or "").lower()
    s = re.sub(r"[\u2010-\u2015\-_/]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def hit(text, phrase):
    return re.search(r"(?<![a-z0-9])" + re.escape(norm(phrase)) + r"(?![a-z0-9])", text) is not None


def main():
    pid = sys.argv[1]
    reg = json.loads(REG.read_text(encoding="utf-8"))
    proj = [p for p in reg["projects"] if p["project_id"] == pid][0]
    prof = proj.get("previously_confirmed_profile") or {}
    negs = NEGATIVE.get(pid, [])
    gold = GOLD[pid]

    print("课题：%s（stage=%s）" % (pid, proj["stage"]))
    print("画像：%s" % (prof or "（无）"))
    print("查询词：%s" % proj["inputs"])
    print("gold（含未用于查询的词）：%s" % gold)
    print()

    seen, raw = set(), []
    for term in proj["inputs"]:
        try:
            items = B.epmc(f'"{term}"', n=20)
        except Exception as e:
            print("  查询 %r 失败：%s" % (term, e))
            continue
        for d in items:
            k = (d.get("doi") or "").lower() or d.get("id")
            if k and k not in seen:
                seen.add(k)
                d["_hit_term"] = term
                raw.append(d)

    for d in raw:
        t, a = norm(d["title"]), norm(d["abstract"])
        if any(hit(t, n) or hit(a, n) for n in negs):
            d["_gold"] = False
        else:
            d["_gold"] = any(hit(t, g) or hit(a, g) for g in gold)

    payload = [{"n": i + 1, "doi": d.get("doi", ""), "date": d.get("date", ""),
                "term": d["_hit_term"], "gold": d["_gold"],
                "title": d["title"], "abs": (d["abstract"] or "")[:300]}
               for i, d in enumerate(raw)]
    (OUT / ("review_input_%s.json" % pid)).write_text(
        json.dumps({"project": pid, "stage": proj["stage"], "profile": prof,
                    "gold": gold, "negative": negs, "items": payload},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    rel = sum(1 for d in raw if d["_gold"])
    print("=" * 78)
    print("竞品默认形态原始输出：%d 条（去重），gold 相关 %d 条 → 精度 %.0f%%"
          % (len(raw), rel, rel / len(raw) * 100 if raw else 0))
    print("=" * 78)
    for d in payload:
        print("\n%2d. [%s] %s  (%s)" % (d["n"], "相关" if d["gold"] else "无关",
                                        d["title"][:84], d["date"]))
        print("    命中=%s | doi=%s" % (d["term"], d["doi"][:40]))
        if d["abs"]:
            print("    %s" % d["abs"][:150].replace("\n", " "))


if __name__ == "__main__":
    main()
