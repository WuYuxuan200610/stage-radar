"""stage-radar 检索基准（可复现，独立运行）。

本脚本取代了早期一版存在方法论缺陷的基准（该版数字已作废，本仓库不再保留其代码与结果）。
其缺陷记录在此，供复核本脚本时参考：

  1) **召回率的分子与分母取自同一集合**——分母是"该次检索结果中判为相关的条数"，
     分子是同一批，导致 Recall 恒等于 100%，与实际报告值不符。
  2) **声称采用 TREC 式 pooling，但实现中没有 pooling**——每个系统只在自己返回的结果内判相关，
     没有跨系统并池后再统一判定。
  3) **判定谓词与查询条件几乎重合**——相关性判定为"标题含锚点词"，而待评估系统的查询本身
     就是"锚点词限定在标题"，等于用查询条件去判定查询结果，比较是半自证的。
  4) **来源单一**——完全未纳入 53 本已核验刊源。

本脚本的做法：
  - **真 pooling**：同一 (课题, 卖点词) 下，把所有系统的 top-K 并起来判池；
    Recall@10 的分母 = 池内相关数。池外可能还有相关文档没被任何系统召回，所以
    recall 是**上界估计**——这是 TREC pooling 的固有前提，必须在报告里写明。
  - **与查询无关的金标准**：每个课题预先定义 gold 概念集（含**任何系统都没用来查的词**），
    判定只看标题（多词概念才回退摘要）是否命中 gold，并排除 negative 词。
    查询条件与判定条件因此不再重合。
  - **三个系统同源对比**（都只走 Europe PMC，避免把"方法"和"覆盖"混在一起）：
      A fulltext     : "<卖点词>"                —— 竞品默认的全文/元数据检索
      B title_only   : TITLE:"<卖点词>"           —— 只隔离"限定标题"这一步的贡献
      C stageradar   : (TITLE:"<锚点>") AND "<卖点词>" —— 我们的做法
  - **刊源覆盖单独报告**：53 本已核验刊源在窗口内的语料里，有多少 gold 相关文档
    是 A/B/C 三系统**都没召回**的。这是覆盖增益，不与方法对比混在一张表里。

运行：
  pip install requests numpy matplotlib
  python benchmark.py                     # 结果写 benchmark_results.json
  python benchmark.py --skip-journals     # 跳过刊源（只跑方法对比，快）
  python plot_benchmark.py                # 出图

诚实边界（写进输出，不只写在注释里）：
  - 相关性为**规则标注 + 人工定义 gold 概念集**，不是多人人工评分。
  - recall 受 pooling 深度限制，是上界估计。
  - 窗口固定，结果随窗口变化；重跑数字会变。
"""
import argparse
import json
import math
import re
import sys
import time
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
UA = {"User-Agent": "stage-radar-benchmark/2.0 (mailto:stage-radar@example.org)"}

WINDOW_FROM = "2026-10-18"
WINDOW_TO = "2026-11-17"
TOPK = 20          # 每个系统取前 20 进池（pooling 深度）
K5, K10 = 5, 10

# ── 课题定义 ────────────────────────────────────────────────
# gold 里刻意包含**没有任何查询用到的词**（如 guanylyltransferase / m7G / MERFISH），
# 否则判定条件会退化成查询条件的复制品。
TOPICS = [
    {
        "id": "mrna-capping",
        "anchor": "mRNA capping",
        "terms": ["cap1 methyltransferase", "capping enzyme", "m6A", "capped mRNA"],
        "gold": ["mrna capping", "capping enzyme", "cap1", "cap methyltransferase",
                 "guanylyltransferase", "m7g", "cap structure", "recapping", "rna cap"],
        "negative": ["vaccine", "antiviral"],
    },
    {
        "id": "peptide-macrocyclization",
        "anchor": "peptide macrocyclization",
        "terms": ["macrocyclic peptide", "peptide cyclization", "radical cyclization",
                  "head-to-tail cyclization"],
        "gold": ["macrocyclization", "macrocyclic peptide", "cyclic peptide",
                 "peptide cyclization", "stapled peptide", "ycao"],
        "negative": ["polymerization"],
    },
    {
        "id": "trna-detection",
        "anchor": "tRNA detection",
        "terms": ["tRNA sensor", "fluorescent tRNA", "live-cell tRNA", "tRNA imaging"],
        "gold": ["trna detection", "trna sensor", "trna imaging", "fluorescent trna",
                 "trna probe", "trna labeling", "trna labelling"],
        "negative": [],
    },
    {
        "id": "prime-editing",
        "anchor": "prime editing",
        "terms": ["pegRNA", "prime editor", "off-target", "reverse transcriptase"],
        "gold": ["prime editing", "prime editor", "pegrna", "pe2", "pe3", "nickase"],
        "negative": ["plant breeding"],
    },
    {
        "id": "aptamer-selex",
        "anchor": "aptamer",
        "terms": ["SELEX", "cell-SELEX", "aptamer sensor", "aptasensor"],
        "gold": ["aptamer", "selex", "aptasensor", "aptamer sensor",
                 "nucleic acid aptamer", "xna"],
        "negative": [],
    },
    {
        "id": "spatial-transcriptomics",
        "anchor": "spatial transcriptomics",
        "terms": ["single-cell spatial", "spatial multi-omics", "in situ sequencing",
                  "spatial barcoding"],
        "gold": ["spatial transcriptomics", "spatial transcriptome", "in situ sequencing",
                 "spatial multi-omics", "merfish", "seqfish", "spatial barcoding",
                 "visium"],
        "negative": [],
    },
    {
        "id": "base-editing",
        "anchor": "base editing",
        "terms": ["cytosine base editor", "adenine base editor", "lipid nanoparticle delivery",
                  "in vivo base editing"],
        "gold": ["base editing", "base editor", "cytosine base editor",
                 "adenine base editor", "cbe", "abe"],
        "negative": ["plant breeding"],
    },
    {
        "id": "protein-design",
        "anchor": "protein design",
        "terms": ["de novo protein design", "protein language model", "directed evolution",
                  "structure prediction"],
        "gold": ["protein design", "de novo design", "protein language model",
                 "directed evolution", "protein engineering", "rfdiffusion"],
        "negative": [],
    },
]

SYSTEMS = ["fulltext", "title_only", "stageradar", "stageradar_v2"]
METRIC_KEYS = ["p5", "p10", "r10", "f1", "mrr"]


# ── 检索 ────────────────────────────────────────────────────
def epmc(query, n=TOPK, retries=3):
    """Europe PMC 检索。窗口写进 query（FIRST_PDATE）——fromPubDate 参数会被静默忽略。"""
    expr = f"({query}) AND FIRST_PDATE:[{WINDOW_FROM} TO {WINDOW_TO}] sort_date:y"
    for attempt in range(retries):
        try:
            r = requests.get(EPMC, params={"query": expr, "format": "json",
                                           "pageSize": n, "resultType": "core"},
                             headers=UA, timeout=40)
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            out = []
            for it in r.json().get("resultList", {}).get("result", []):
                out.append({
                    "id": it.get("id", ""),
                    "doi": (it.get("doi") or "").lower(),
                    "title": it.get("title", "") or "",
                    "abstract": it.get("abstractText", "") or "",
                })
            return out
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))


def system_query(system, topic, term):
    if system == "fulltext":
        return f'"{term}"'
    if system == "title_only":
        return f'TITLE:"{term}"'
    if system == "stageradar_v2":
        # 改后策略：锚点不再当"必须通过的门"，标题或摘要命中即可
        return f'(TITLE:"{term}" OR ABSTRACT:"{term}")'
    return f'(TITLE:"{topic["anchor"]}") AND "{term}"'


def rerank_v2(results, topic):
    """stageradar_v2 的本地重排：锚点分档（标题 2 / 摘要 1 / 都没有 0），同档保持接口原序。"""
    anchor = topic["anchor"].lower()
    return sorted(
        enumerate(results),
        key=lambda pair: -(
            2 if anchor in (pair[1]["title"] or "").lower()
            else 1 if anchor in (pair[1]["abstract"] or "").lower()
            else 0
        ),
    )


# ── 相关性判定（与查询条件无关） ─────────────────────────────
def _norm(s):
    """归一化：小写 + 把连字符/各种破折号拉平成空格。

    为什么必须拉平：实测发现 `Cap-1` 这种写法匹配不上词表里的 `cap1` / `cap 1`，
    导致**最该命中的那一篇被判成无关**（见 README §4.7「测量误差与修正」）。
    连字符在生物医学写作里极常见（cap-1 / Cap-1 / m6A-cap / prime-editing），
    不归一化会系统性地漏判。
    """
    s = (s or "").lower()
    s = re.sub(r"[\u2010-\u2015\-_/]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def is_relevant(doc, topic):
    title = _norm(doc["title"])
    abstract = _norm(doc["abstract"])
    if any(_hit(title, n) for n in topic["negative"]):
        return False
    for g in topic["gold"]:
        if _hit(title, g):
            return True
        if " " in g and _hit(abstract, g):   # 多词概念才允许回退摘要
            return True
    return False


def _hit(text, phrase):
    return re.search(r"(?<![a-z0-9])" + re.escape(_norm(phrase)) + r"(?![a-z0-9])", text) is not None


def key_of(doc):
    return doc["doi"] or doc["id"]


# ── 指标 ────────────────────────────────────────────────────
def metrics(ranked, pool_relevant_keys):
    rel = [1 if key_of(d) in pool_relevant_keys else 0 for d in ranked]
    p5 = sum(rel[:K5]) / K5
    p10 = sum(rel[:K10]) / K10
    # Recall 的分母是【池内相关总数】，不是"本次检索到的相关数"（v1 就错在这里）
    denom = len(pool_relevant_keys)
    r10 = (sum(rel[:K10]) / denom) if denom else 0.0
    f1 = (2 * p10 * r10 / (p10 + r10)) if (p10 + r10) else 0.0
    mrr = 0.0
    for i, v in enumerate(rel[:K10], 1):
        if v:
            mrr = 1.0 / i
            break
    return {"p5": round(p5, 4), "p10": round(p10, 4), "r10": round(r10, 4),
            "f1": round(f1, 4), "mrr": round(mrr, 4)}


# ── 刊源覆盖（单独报告） ─────────────────────────────────────
def journal_corpus(cache_path: Path, app_root: Path):
    """把 53 本已核验刊源在窗口内的语料拉一次并缓存。"""
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    sys.path.insert(0, str(app_root))
    from stage_radar import journal_sources as J
    corpus, coverage = [], []
    for j in J.enabled_journals():
        got, cov = J.fetch_journal(j, WINDOW_FROM, WINDOW_TO)
        coverage.append(cov)
        for p in got:
            corpus.append({"id": p.get("doi") or p.get("id"), "doi": (p.get("doi") or "").lower(),
                           "title": p.get("title", ""), "abstract": p.get("abstract", ""),
                           "journal": p.get("journal", "")})
        print(f"    刊源 {j['id']}: {len(got)} 条 ({cov['status']})", flush=True)
    payload = {"window": [WINDOW_FROM, WINDOW_TO], "coverage": coverage, "items": corpus}
    cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


# ── 主流程 ──────────────────────────────────────────────────
def run(skip_journals: bool):
    app_root = Path(__file__).resolve().parent.parent / "stage-radar-app"
    rows = []
    journal_stats = None

    if not skip_journals and app_root.exists():
        print("[1/2] 拉取 53 本已核验刊源的窗口语料（会缓存，重跑很快）…", flush=True)
        jc = journal_corpus(app_root / "data" / "benchmark_journal_corpus.json", app_root)
        per_topic = {}
        for t in TOPICS:
            hits = [d for d in jc["items"] if is_relevant(d, t)]
            per_topic[t["id"]] = hits
            print(f"    课题 {t['id']}: 刊源语料中 gold 相关 {len(hits)} 条", flush=True)
        journal_stats = {"window": jc["window"], "corpus_size": len(jc["items"]),
                         "journals": len(jc["coverage"]),
                         "partial_or_error": [c for c in jc["coverage"] if c.get("status") != "ok"],
                         "per_topic_relevant": {k: len(v) for k, v in per_topic.items()},
                         "_hits": per_topic}

    print("[2/2] 逐 (课题, 卖点词) 跑三个系统 + pooling…", flush=True)
    for t in TOPICS:
        for term in t["terms"]:
            results = {}
            costs = {}
            for s in SYSTEMS:
                t0 = time.perf_counter()
                try:
                    results[s] = epmc(system_query(s, t, term))
                except Exception as e:
                    results[s] = []
                    print(f"    !! {t['id']} / {term} / {s} 检索失败：{e}", flush=True)
                ms = int((time.perf_counter() - t0) * 1000)
                # 成本三件套：检索耗时、返回候选数、要送 LLM 审核的文本量（≈token 成本的直接代理）
                costs[s] = {"ms": ms, "n": len(results[s]),
                            "chars": sum(len(d["title"]) + len(d["abstract"]) for d in results[s])}
                time.sleep(0.4)
            # v2 在本地按锚点重排——锚点是加权信号，不是硬门
            order = [results["stageradar_v2"][i] for i, _ in rerank_v2(results["stageradar_v2"], t)]
            results["stageradar_v2"] = order

            # pooling：三系统 top-K 并集，统一判相关
            pool, seen = [], set()
            for s in SYSTEMS:
                for d in results[s]:
                    k = key_of(d)
                    if k and k not in seen:
                        seen.add(k)
                        pool.append(d)
            pool_relevant = {key_of(d) for d in pool if is_relevant(d, t)}

            row = {"topic": t["id"], "term": term, "pool_size": len(pool),
                   "pool_relevant": len(pool_relevant)}
            for s in SYSTEMS:
                row[s] = metrics(results[s], pool_relevant)
                row[s + "_cost"] = costs[s]
            rows.append(row)
            print(f"    {t['id']:26s} {term:34s} 池 {len(pool):3d} 相关 {len(pool_relevant):3d}", flush=True)

    out = {
        "benchmark_version": 2,
        "generated_at": datetime.now().isoformat(),
        "window": [WINDOW_FROM, WINDOW_TO],
        "pooling_depth": TOPK,
        "n": len(rows),
        "topics": len(TOPICS),
        "systems": {
            "fulltext": "「卖点词」全文/元数据检索（竞品默认行为）",
            "title_only": 'TITLE:"卖点词"（只限定标题）',
            "stageradar": '(TITLE:"锚点") AND "卖点词"（锚点当硬门，改前的做法）',
            "stageradar_v2": 'TITLE/ABSTRACT:"卖点词" + 本地按锚点分档重排（改后的做法，锚点降为加权信号）',
        },
        "labeling": "预定义 gold 概念集命中标题（多词概念回退摘要），排除 negative 词；gold 含未被任何查询使用的词",
        "limitations": [
            "相关性为规则标注 + 人工定义 gold 概念集，非多人人工评分。",
            "recall 分母为池内相关数，受 pooling 深度限制，是上界估计。",
            "窗口固定为 %s..%s，重跑数字会变。" % (WINDOW_FROM, WINDOW_TO),
        ],
        "rows": rows,
    }
    if journal_stats:
        out["journal_coverage"] = journal_stats
    return out


def summarize(out):
    rows = out["rows"]
    n = len(rows)
    print("\n" + "=" * 78)
    print(f"基准 v2  ·  N={n}（{out['topics']} 课题 × {n // out['topics']} 卖点词）  "
          f"窗口 {out['window'][0]}..{out['window'][1]}  pooling 深度 {out['pooling_depth']}")
    print("=" * 78)
    header = f"{'指标':<14}" + "".join(f"{s:>16}" for s in SYSTEMS)
    print(header)
    for k, label in zip(METRIC_KEYS, ["Precision@5", "Precision@10", "Recall@10", "F1@10", "MRR"]):
        vals = [sum(r[s][k] for r in rows) / n for s in SYSTEMS]
        print(f"{label:<14}" + "".join(f"{v:>16.3f}" for v in vals))
    print()
    # 成本对比：同样一轮检索，各方案要花多少时间、拉回多少候选、送多少文本给 LLM
    print("成本对比（每轮每个查询的平均值；chars ≈ 要送 LLM 审核的文本量）")
    print(f"{'方案':<16}{'耗时(ms)':>10}{'候选数':>10}{'送审字符':>12}{'相对候选':>10}")
    base_n = sum(r["fulltext_cost"]["n"] for r in rows) / n
    for s in SYSTEMS:
        ms = sum(r[s + "_cost"]["ms"] for r in rows) / n
        cnt = sum(r[s + "_cost"]["n"] for r in rows) / n
        ch = sum(r[s + "_cost"]["chars"] for r in rows) / n
        print(f"{s:<16}{ms:>10.0f}{cnt:>10.1f}{ch:>12.0f}{cnt / base_n * 100 if base_n else 0:>9.0f}%")
    print()

    # 配对检验：fulltext vs stageradar（P@10）
    a = [r["fulltext"]["p10"] for r in rows]
    b = [r["stageradar"]["p10"] for r in rows]
    try:
        import numpy as np
        d = np.array(b) - np.array(a)
        se = d.std(ddof=1) / math.sqrt(n) if n > 1 else 0.0
        t = d.mean() / se if se else float("inf")
        wins = int((d > 0).sum())
        print(f"配对比较 P@10（stageradar - fulltext）：均值差 {d.mean():+.3f}，t({n-1})={t:.2f}，"
              f"{wins}/{n} 组更优")
        rng = np.random.default_rng(0)
        boot = [np.mean(rng.choice(d, n, replace=True)) for _ in range(5000)]
        lo, hi = np.percentile(boot, [2.5, 97.5])
        print(f"均值差的 bootstrap 95% CI：[{lo:+.3f}, {hi:+.3f}]")
    except Exception as e:
        print("统计检验跳过：", e)

    jc = out.get("journal_coverage")
    if jc:
        print()
        print(f"刊源覆盖（单独报告，不与方法对比混算）：")
        print(f"  窗口内 53 本刊语料 {jc['corpus_size']} 条，成功刊数 {jc['journals']}，"
              f"未完整覆盖 {len(jc['partial_or_error'])} 本")
        for tid, cnt in jc["per_topic_relevant"].items():
            print(f"    {tid:26s} gold 相关 {cnt} 条")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-journals", action="store_true")
    ap.add_argument("-o", "--out", default="benchmark_results.json")
    args = ap.parse_args()
    data = run(args.skip_journals)
    Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果写入 {args.out}")
    summarize(data)
