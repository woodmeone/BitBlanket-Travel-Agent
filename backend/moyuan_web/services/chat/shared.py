"""聊天服务内部共享工具函数。

本模块提供跨 Mixin 和协作组件共用的工具函数，
避免代码重复，确保行为一致。
"""

from __future__ import annotations

from typing import Any, Optional


def merge_artifact_payload(
    base: Optional[dict[str, Any]],
    patch: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """【核心】深度合并产物片段，确保预览、补丁和最终快照保持一致。

    递归合并两个字典，对于嵌套字典进行深度合并，非字典值直接覆盖。
    这种子 Agent 各自产出部分产物、最终合并为完整旅行计划的场景非常常见。

    应用场景：
        酒店子 Agent 产出 {"hotel": {"name": "三亚湾酒店"}},
        景点子 Agent 产出 {"hotel": {"price": 500}, "attractions": [...]},
        合并后得到 {"hotel": {"name": "三亚湾酒店", "price": 500}, "attractions": [...]}

    Args:
        base: 基础产物字典，作为合并起点
        patch: 补丁产物字典，其值覆盖或合并到 base 中

    Returns:
        合并后的新字典，不修改原始 base 和 patch
    """
    merged = dict(base or {})
    if not isinstance(patch, dict):
        return merged

    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_artifact_payload(merged.get(key), value)  # 嵌套字典递归合并
            continue
        merged[key] = value  # 非字典值直接覆盖
    return merged
