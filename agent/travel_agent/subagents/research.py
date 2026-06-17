"""研究子代理（Research Subagent）模块。

职责：收集目的地证据和旅行信号。
    research 子代理是旅行规划的"信息采集员"，负责：
    - 搜索目的地景点、美食、交通等信息
    - 查询天气、签证政策等旅行条件
    - 收集价格信号供 budget 子代理使用

    类比旅行社：research 子代理就是"调研专员"，
    在客户确定行程前，先去收集各种目的地的实用信息。
"""

from __future__ import annotations

from typing import Any, Optional

from .base import BaseSubagent


class ResearchSubagent(BaseSubagent):
    """研究子代理，基于现有旅行工具和技能实现。

    覆写基类的 artifact_patch_from_done 方法，
    从完成事件中提取研究证据和工具使用记录。
    """

    def artifact_patch_from_done(
        self,
        done_event: dict[str, Any],  # 完成事件，包含 tools_used、intent 等结果数据
        *,
        user_message: str,  # 用户原始消息
        session_id: str,  # 会话ID
        chat_mode: Optional[str],  # 对话模式
    ) -> dict[str, Any]:
        """【核心】从完成事件构建研究产物补丁。

        只在本次执行中实际使用了本子代理的工具时才生成产物，
        否则返回空字典（表示本子代理未参与此次执行）。

        旅行场景举例：
            用户说"查一下东京有什么好玩的"，research 子代理调用了
            search_attractions 和 search_restaurants 两个工具，
            产物中记录了工具使用情况和收集到的证据。
        """
        _ = (session_id, chat_mode)
        # 筛选出本次执行中属于本子代理的工具（排除其他子代理的工具）
        tool_names = [name for name in done_event.get("tools_used", []) if name in self.tool_names()]
        if not tool_names:
            return {}  # 本子代理未使用任何工具，不生成产物

        intent = str(done_event.get("intent") or "general")  # 用户意图，如 "景点探索"、"美食推荐"
        return {
            "research": {
                "summary": f"Collected {len(tool_names)} research signal(s) for intent={intent}.",
                "source_tools": tool_names,  # 使用的工具列表（snake_case）
                "sourceTools": tool_names,  # camelCase 版本，兼容前端
                "destinations": [],  # 目的地列表，后续由具体工具结果填充
                "evidence": [  # 证据列表，每条记录对应一个工具的采集结果
                    {
                        "tool": tool_name,  # 工具名称，如 "search_attractions"
                        "status": "collected",  # 采集状态: "collected"(已采集)
                        "query": user_message,  # 原始查询文本
                    }
                    for tool_name in tool_names
                ],
            },
            "metadata": {
                "research_subagent_completed": True,  # 标记研究子代理已完成
            },
        }
