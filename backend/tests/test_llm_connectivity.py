from __future__ import annotations

import argparse
import asyncio
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

# 设置 Python 路径以确保可以导入 app
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import _load_env_file
from app.core.llm_config import LLMFeatureConfig
from app.services.llm.registry import llm_registry
from app.services.llm.schemas import LLMMessage, LLMRequest


STATUS_ICON = {"success": "🟢", "failure": "🔴", "warning": "🟠"}
RESULT_TEXT = {"success": "成功", "failure": "失败", "warning": "异常"}


@dataclass(frozen=True)
class ConnectivityResult:
    level: str
    platform: str
    model: str
    result: str
    detail: str
    reply: str | None = None


def get_visual_width(text: str) -> int:
    """计算字符串在终端中的视觉宽度（考虑中文字符占2格）。"""
    width = 0
    for char in text:
        if unicodedata.east_asian_width(char) in ("W", "F", "A"):
            width += 2
        else:
            width += 1
    return width


def visual_ljust(text: str, width: int) -> str:
    """根据视觉宽度进行左对齐填充。"""
    current_width = get_visual_width(text)
    return text + " " * max(0, width - current_width)


def format_row(result: ConnectivityResult) -> str:
    icon = STATUS_ICON[result.level]
    c_icon = visual_ljust(icon, 4)
    c_platform = visual_ljust(result.platform[:14], 14)
    c_model = visual_ljust(result.model[:36], 36)
    c_result = visual_ljust(result.result, 8)
    return f"| {c_icon} | {c_platform} | {c_model} | {c_result} | {result.detail}"


async def test_model_connectivity(model_key: str, model_entry, timeout_seconds: float) -> ConnectivityResult:
    if not model_entry.enabled:
        return ConnectivityResult("warning", model_entry.platform, model_entry.model_id, RESULT_TEXT["warning"], "disabled")

    start = time.perf_counter()
    # 打印进度，方便定位卡在哪
    # print(f"正在测试: {model_key} ({model_entry.model_id})...", file=sys.stderr)
    
    try:
        # 使用 asyncio.wait_for 强制执行硬超时
        async with asyncio.timeout(timeout_seconds):
            provider = llm_registry._get_provider(model_entry.platform)
            feature = LLMFeatureConfig(model_key=model_key, max_tokens=10, temperature=0)
            request = LLMRequest(messages=[LLMMessage(role="user", content="Reply with exactly OK.")])
            
            response = await provider.generate("connectivity_test", feature, model_key, model_entry, request)
            
            elapsed_ms = round((time.perf_counter() - start) * 1000)
            content = response.message.content.strip()
            
            if content:
                return ConnectivityResult("success", model_entry.platform, model_entry.model_id, RESULT_TEXT["success"], f"{elapsed_ms}ms", reply=content)
            return ConnectivityResult("warning", model_entry.platform, model_entry.model_id, RESULT_TEXT["warning"], "empty response")
            
    except asyncio.TimeoutError:
        return ConnectivityResult("failure", model_entry.platform, model_entry.model_id, RESULT_TEXT["failure"], "测试硬超时 (30s)")
    except Exception as exc:
        error_msg = str(exc).split("\n")[0][:60]
        return ConnectivityResult("failure", model_entry.platform, model_entry.model_id, RESULT_TEXT["failure"], error_msg)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test LLM connectivity using the app registry (Agno).")
    parser.add_argument("--platform", action="append", default=[], help="Only test specific platform names.")
    parser.add_argument("--model-key", action="append", default=[], help="Only test specific model keys.")
    parser.add_argument("--include-disabled", action="store_true", help="Include disabled model entries.")
    parser.add_argument("--timeout", type=float, default=30.0, help="Hard timeout per model in seconds.")
    return parser.parse_args()


async def main() -> int:
    _load_env_file()
    args = parse_args()
    
    try:
        all_models = llm_registry.list_models(enabled_only=not args.include_disabled)
    except Exception as e:
        print(f"🔴 加载配置文件失败: {e}")
        return 1
    
    selected_platforms = set(args.platform)
    selected_model_keys = set(args.model_key)
    
    test_tasks = []
    for model_key, model_entry in all_models.items():
        if selected_model_keys and model_key not in selected_model_keys:
            continue
        if selected_platforms and model_entry.platform not in selected_platforms:
            continue
        test_tasks.append(test_model_connectivity(model_key, model_entry, args.timeout))

    if not test_tasks:
        print("没有匹配到可测试的模型。")
        return 1

    print(f"开始测试 {len(test_tasks)} 个模型...")
    results = await asyncio.gather(*test_tasks)

    # 打印表格
    h_status = visual_ljust("状态", 4)
    h_platform = visual_ljust("平台", 14)
    h_model = visual_ljust("模型", 36)
    h_result = visual_ljust("结果", 8)
    h_detail = "耗时/原因"

    header_str = f"| {h_status} | {h_platform} | {h_model} | {h_result} | {h_detail}"
    sep = f"|{'-'*6}|{'-'*16}|{'-'*38}|{'-'*10}|{'-'*30}"
    
    print(sep)
    print(header_str)
    print(sep)
    for result in results:
        print(format_row(result))
    print(sep)

    return 0 if all(result.level == "success" for result in results) else 2


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n用户中断测试。")
        sys.exit(1)
