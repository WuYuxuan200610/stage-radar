# --- 路径前导（由 _migrate_research.py 注入，使脚本可在任意机器运行）---
# _HERE 本目录；_REPO 本仓库根（含 benchmark.py）；_APP 桌面管线所在仓库（可用环境变量覆盖）
import os as _os
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_REPO = _HERE.parent
_APP = _Path(_os.environ.get("STAGE_RADAR_APP", str(_REPO.parent / "stage-radar-app")))
# --- 前导结束 ---

"""构建「滞后窗口」的预印本标题索引，用于回答：期刊论文中有多少根本没有预印本。

为什么必须滞后：实测预印本比见刊中位早 85 天。
所以"2026 年 10 月见刊的论文"对应的预印本多在 7 月前后，用同一窗口必然匹配不到
（第一版就是这么错的：同窗口只匹配到 1/1402）。

索引存盘缓存，重跑很快。按天分段取，避免接口掐连接。
"""
import json
import re
import sys
import time
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = Path(str(_HERE / "preprint_index.json"))
UA = {"User-Agent": "stage-radar/0.5 (mailto:stage-radar@example.org)"}
WINDOWS = [("2026-04-01", "2026-04-30"), ("2026-05-01", "2026-05-31"),
           ("2026-06-01", "2026-06-30"), ("2026-07-01", "2026-07-31"),
           ("2026-08-01", "2026-08-31"), ("2026-09-01", "2026-09-30"),
           ("2026-10-01", "2026-10-31"), ("2026-11-01", "2026-11-17")]


def norm(t):
    t = (t or "").lower()
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


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


def fetch(server, start, end):
    """按 7 天分段取，避免长窗口掐连接。"""
    import datetime as dt
    s, u = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    out = []
    cur = s
    while cur <= u:
        seg_end = min(cur + dt.timedelta(days=6), u)
        cursor = 0
        for _ in range(80):
            url = ("https://api.biorxiv.org/details/%s/%s/%s/%d"
                   % (server, cur.isoformat(), seg_end.isoformat(), cursor))
            try:
                data = get(url)
            except Exception as e:
                print("    %s %s..%s 中断于 cursor=%d：%s"
                      % (server, cur, seg_end, cursor, type(e).__name__), flush=True)
                break
            batch = data.get("collection", [])
            if not batch:
                break
            for it in batch:
                t = norm(it.get("title"))
                if len(t) > 20:
                    out.append({"k": t, "date": it.get("date", ""),
                                "published": (it.get("published") or "").strip(),
                                "doi": it.get("doi", ""), "server": server,
                                "title": (it.get("title") or "")[:90]})
            total = int((data.get("messages") or [{}])[0].get("total") or 0)
            cursor += 30
            if cursor >= total:
                break
        cur = seg_end + dt.timedelta(days=1)
    return out


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    index = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"entries": [], "done": []}
    done = set(index.get("done", []))
    for start, end in WINDOWS:
        for server in ("biorxiv", "medrxiv"):
            tag = "%s|%s..%s" % (server, start, end)
            if tag in done:
                print("跳过（已缓存）", tag, flush=True)
                continue
            t0 = time.time()
            got = fetch(server, start, end)
            index["entries"].extend(got)
            done.add(tag)
            index["done"] = sorted(done)
            OUT.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
            print("完成 %-28s %5d 条  %.0f 秒  累计 %d 条"
                  % (tag, len(got), time.time() - t0, len(index["entries"])), flush=True)
    keys = {e["k"] for e in index["entries"]}
    print("\n索引完成：%d 条（去重标题 %d）" % (len(index["entries"]), len(keys)))


if __name__ == "__main__":
    main()
