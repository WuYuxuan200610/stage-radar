# --- 路径前导（由 _migrate_research.py 注入，使脚本可在任意机器运行）---
# _HERE 本目录；_REPO 本仓库根（含 benchmark.py）；_APP 桌面管线所在仓库（可用环境变量覆盖）
import os as _os
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_REPO = _HERE.parent
_APP = _Path(_os.environ.get("STAGE_RADAR_APP", str(_REPO.parent / "stage-radar-app")))
# --- 前导结束 ---

"""查 LLM 是否真的可调用（不打印任何密钥内容，只报存在性与一次真实调用结果）。

核心实验（LLM 理解层的增量）能不能做，取决于这里。
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(_APP))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

env = Path(str(_APP / ".env"))
print("查找 .env：", env.exists())
if env.exists():
    for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip()
        # 只报键名与长度，绝不打印值
        print("  %-28s = <%d 字符>" % (k, len(v)))

from stage_radar import cli, llm  # noqa: E402

print()
print("PRESETS:", llm.PRESETS)
print("DEFAULT_MODELS:", cli.DEFAULT_MODELS)

for provider in ("deepseek", "kimi", "boler"):
    try:
        client = cli.build_client(provider)
    except Exception as e:
        print("%-9s 构建失败：%s" % (provider, type(e).__name__))
        continue
    if client is None:
        print("%-9s 无 key，不可用" % provider)
        continue
    print("%-9s base=%s model=%s" % (provider, client.base_url, client.model))
    try:
        out = llm.chat(client, "只回复两个字：可用", max_tokens=16)
        print("          真实调用成功，返回：%r" % (out or "")[:60])
    except Exception as e:
        print("          真实调用失败：%s: %s" % (type(e).__name__, str(e)[:120]))
