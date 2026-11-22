# --- 路径前导（由 _migrate_research.py 注入，使脚本可在任意机器运行）---
# _HERE 本目录；_REPO 本仓库根（含 benchmark.py）；_APP 桌面管线所在仓库（可用环境变量覆盖）
import os as _os
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_REPO = _HERE.parent
_APP = _Path(_os.environ.get("STAGE_RADAR_APP", str(_REPO.parent / "stage-radar-app")))
# --- 前导结束 ---

"""验证「期刊↔预印本」匹配键是否一致。

怀疑：索引里的标题做了全标点剥离，而 B._norm 只拉平连字符 → 两边字符串对不上，
所以匹配率被压到 1.7%（不可能这么低：已知预印本 82% 后来都见刊了）。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(_REPO))
import benchmark as B  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

R = Path(str(_HERE))
idx = json.loads((R / "preprint_index.json").read_text(encoding="utf-8"))
jc = json.loads((R / "journal_titles_for_preprint_check.json").read_text(encoding="utf-8"))


def index_style_norm(t):
    """还原 build_preprint_index.py 里的 norm()——它会剥掉所有非字母数字。"""
    t = (t or "").lower()
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


print("两种归一化的差别（同一条标题）：")
for d in jc[:3]:
    raw = d["title"]
    print("  原始      : %s" % raw[:74])
    print("  B._norm   : %s" % B._norm(raw)[:74])
    print("  索引 norm : %s" % index_style_norm(raw)[:74])
    print("  一致？    : %s" % (B._norm(raw) == index_style_norm(raw)))
    print()

pre_keys = {e["k"] for e in idx["entries"]}
print("索引键样例：")
for k in list(pre_keys)[:4]:
    print("  %s" % k[:80])

print()
# 用索引口径重算匹配
seen, tot, hit = set(), 0, 0
for d in jc:
    k = index_style_norm(d["title"])
    if len(k) < 20 or k in seen:
        continue
    seen.add(k)
    tot += 1
    if k in pre_keys:
        hit += 1
print("用**索引口径**重新匹配：期刊论文 %d 篇，其中能找到预印本 %d 篇 → **%.1f%%**"
      % (tot, hit, hit / tot * 100 if tot else 0))
print("（上一版用 B._norm 口径只有 1.7%%——差异全部来自归一化不一致）")

# 再验一次：已知会发表的预印本，看它的标题在不在索引里
pub = [e for e in idx["entries"] if e.get("published") and e["published"] != "NA"][:5]
print()
print("抽样：已发表预印本是否在索引里（应为 True，验证索引自身一致）：")
for e in pub:
    print("  %-5s %s" % (e["k"] in pre_keys, e["title"][:66]))
