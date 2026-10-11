"""DeepSeek 适配器冒烟测试。

目的：用项目自身的代码路径（DeepSeekAdapter -> OpenAICompatibleAdapter.query）
对配置的代理端点发一次真实请求，验证 key / base_url / model 是否可用。

副作用说明（保持只读验证，不污染项目）：
- 不写数据库：usage_logger 后台线程在独立脚本中未启动，log() 会直接丢弃记录
  （见 app/usage_logger.py:108）；usage_context 为空，配额检查会直接返回。
- 不修改任何现有文件、不改 .env、不改业务代码。

用法（必须在 backend 目录下执行，settings 才能加载到 .env）：
    python scripts/smoke_deepseek.py --new-key sk-xxxxxxxx
    # 或
    set DEEPSEEK_NEW_KEY=sk-xxxxxxxx && python scripts/smoke_deepseek.py

安全提示：新 key 不硬编码在本文件，避免误提交到 git。
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings  # noqa: E402
from app.adapters.deepseek import DeepSeekAdapter  # noqa: E402

QUESTION = "你好，请只回复两个字：pong"


def mask(key: str) -> str:
    if not key:
        return "(空)"
    if len(key) <= 12:
        return "***"
    return f"{key[:7]}...{key[-4:]}"


def run_case(label: str, api_key: str) -> dict:
    print("-" * 64)
    print(f"[{label}] key={mask(api_key)}")
    print(f"  base_url = {settings.DEEPSEEK_BASE_URL}")
    print(f"  model    = {settings.DEEPSEEK_MODEL}")

    if not api_key:
        print("  跳过：key 为空")
        return {"label": label, "ok": False, "skipped": True}

    adapter = DeepSeekAdapter(
        api_key=api_key,
        base_url=settings.DEEPSEEK_BASE_URL,
        model=settings.DEEPSEEK_MODEL,
        temperature=settings.MONITOR_TEMPERATURE,
        max_tokens=settings.MONITOR_MAX_TOKENS,
    )

    started = time.perf_counter()
    try:
        result = adapter.query(QUESTION)
    except Exception as exc:  # query() 本身会吞异常，这里只兜底
        dt = round((time.perf_counter() - started) * 1000)
        print(f"  EXCEPTION: {type(exc).__name__}: {exc}")
        return {"label": label, "ok": False, "latency_ms": dt, "error": str(exc)}

    dt = round((time.perf_counter() - started) * 1000)
    print(f"  success  = {result.success}")
    print(f"  latency  = {dt} ms")
    print(f"  tokens   = {result.total_tokens} "
          f"(in={result.prompt_tokens}, out={result.completion_tokens})")
    if result.success:
        print(f"  answer   = {result.answer!r}")
    else:
        print(f"  error    = {result.error}")
    return {
        "label": label,
        "ok": bool(result.success),
        "latency_ms": dt,
        "tokens": result.total_tokens,
        "error": result.error,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="DeepSeek 适配器冒烟测试")
    parser.add_argument("--new-key", default=os.environ.get("DEEPSEEK_NEW_KEY", ""),
                        help="待验证的新 key；也可用环境变量 DEEPSEEK_NEW_KEY")
    parser.add_argument("--skip-env-key", action="store_true",
                        help="只测新 key，不测 .env 里现有的 key")
    args = parser.parse_args()

    print("=" * 64)
    print("DeepSeek 适配器冒烟测试（只读验证，不写库）")
    print(f"APP_ENV  = {settings.APP_ENV}")
    print(f"model    = {settings.DEEPSEEK_MODEL}")
    print("=" * 64)

    results = []
    if not args.skip_env_key:
        results.append(run_case(".env 现有 key", settings.DEEPSEEK_API_KEY))
    results.append(run_case("你提供的新 key", args.new_key))

    print("-" * 64)
    print("汇总：")
    for r in results:
        if r.get("skipped"):
            status = "SKIP"
        else:
            status = "OK" if r["ok"] else "FAIL"
        extra = r.get("error") or ""
        print(f"  [{status:4}] {r['label']}  {extra[:120]}")

    any_ok = any(r.get("ok") for r in results)
    return 0 if any_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
