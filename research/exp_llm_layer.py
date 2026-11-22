# --- 路径前导（由 _migrate_research.py 注入，使脚本可在任意机器运行）---
# _HERE 本目录；_REPO 本仓库根（含 benchmark.py）；_APP 桌面管线所在仓库（可用环境变量覆盖）
import os as _os
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_REPO = _HERE.parent
_APP = _Path(_os.environ.get("STAGE_RADAR_APP", str(_REPO.parent / "stage-radar-app")))
# --- 前导结束 ---

"""实验：LLM 理解层的增量（agent-as-judge + 独立 gold 规则）。

背景：没有 LLM API key，真实调用跑不起来。但 SKILL 规定的审核层在 DSH 里本来就是**agent 本人**做的。
所以由 agent 扮演审核层，并明确标注为**单标注者、非双盲**的案例研究。

要避免的自证陷阱：判定相关性的 gold 规则必须**独立于**审核层的判断。
  - gold：课题画像的词表（**包含查询没用过的词**），客观规则，先定后用；
  - 审核：agent 只能依据"能否说出这篇与**本课题画像**的具体关系"来保留/丢弃。
两者相关但不同一，因此 precision 的变化有信息量。

输出：把原始候选（竞品默认会推的东西）连同 gold 标注、摘要片段一起打印出来，供 agent 逐条判定。
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
WINDOW = ("2026-10-18", "2026-11-17")

# 先定金标准（此时还没看检索结果）：画像词 + 该领域公认的同义概念，
# 其中 guanylyltransferase / m7G / vaccinia / 2'-O-methyltransferase 都**不在查询词里**，
# 这样判定就不会退化成"查询条件的复制品"。
GOLD = [
    "mrna capping", "capping enzyme", "cap1", "cap 1", "cap methyltransferase",
    "guanylyltransferase", "m7g", "cap structure", "recapping", "rna cap",
    "capped mrna", "vaccinia capping", "2'-o-methyltransferase", "n7-methyltransferase",
    "cap-specific", "mrna cap",
]


def norm(s):
    return re.sub(r"\s+", " ", (s or "").lower())


def hit(text, phrase):
    return re.search(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", text) is not None


def gold_relevant(doc, negatives):
    title, ab = norm(doc["title"]), norm(doc["abstract"])
    if any(hit(title, n) or hit(ab, n) for n in negatives):
        return False
    return any(hit(title, g) or hit(ab, g) for g in GOLD)


def main():
    reg = json.loads(REG.read_text(encoding="utf-8"))
    proj = [p for p in reg["projects"] if p["project_id"] == "capping-ivt"][0]
    prof = proj.get("previously_confirmed_profile") or {}
    ignore = [t.lower() for t in (prof.get("ignore_terms") or [])]
    print("课题：%s（stage=%s）" % (proj["project_id"], proj["stage"]))
    print("画像：novelty=%s" % prof.get("novelty_points"))
    print("      engineering=%s" % prof.get("engineering_points"))
    print("      无关圈=%s" % ignore)
    print("查询词（竞品形态）：%s" % proj["inputs"])
    print("gold 词表（含未被查询用到的词）：%s" % GOLD)
    print()

    # 竞品默认形态：全文关键词，每个 input 取前 20
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
        d["_gold"] = gold_relevant(d, ignore)

    payload = [{"n": i + 1, "doi": d.get("doi", ""), "date": d.get("date", ""),
                "term": d["_hit_term"], "gold": d["_gold"],
                "title": d["title"], "abs": (d["abstract"] or "")[:260]}
               for i, d in enumerate(raw)]
    (OUT / "review_input.json").write_text(
        json.dumps({"project": proj["project_id"], "gold": GOLD, "ignore": ignore,
                    "items": payload}, ensure_ascii=False, indent=2), encoding="utf-8")

    rel = sum(1 for d in raw if d["_gold"])
    print("=" * 78)
    print("竞品默认形态的原始输出：%d 条（去重后），其中 gold 相关 %d 条 → 精度 %.0f%%"
          % (len(raw), rel, rel / len(raw) * 100 if raw else 0))
    print("=" * 78)
    for d in payload:
        flag = "相关" if d["gold"] else "无关"
        print("\n%2d. [%s] %s  (%s)" % (d["n"], flag, d["title"][:88], d["date"]))
        print("    命中词=%s | doi=%s" % (d["term"], d["doi"][:44]))
        if d["abs"]:
            print("    摘要: %s" % d["abs"][:170].replace("\n", " "))


if __name__ == "__main__":
    main()
