"""
聊天端点请求模型 —— 定义 /api/chat 接口的请求体结构

【基础知识】
- Pydantic BaseModel：FastAPI 使用 Pydantic 模型进行请求体校验和序列化，
  自动生成 OpenAPI 文档，并在校验失败时返回 422 错误。

- ChatMode：聊天模式枚举，支持三种模式：
  - direct：直接调用 LLM，不经过 Agent 推理
  - react：ReAct 推理模式，Agent 思考-行动-观察循环
  - plan：规划模式，先生成计划再逐步执行
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..validation import SESSION_ID_PATTERN


ChatMode = Literal["direct", "react", "plan"]  # 聊天模式：direct=直接, react=推理, plan=规划


class ChatRequest(BaseModel):
    """聊天流式接口的请求体模型。

    字段说明：
    - message：用户消息内容，必填，1~5000字符
    - display_message：前端展示用的消息文本（可与 message 不同，如隐藏了系统提示）
    - session_id：会话ID，可选，不传则创建新会话
    - mode：聊天模式，默认 react
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)  # 禁止额外字段，自动去除字符串首尾空白

    message: str = Field(min_length=1, max_length=5000)  # 用户消息，1~5000字符
    display_message: str | None = Field(default=None, max_length=5000)  # 前端展示消息，可选
    session_id: str | None = Field(default=None, min_length=1, max_length=128, pattern=SESSION_ID_PATTERN)  # 会话ID，需匹配正则
    mode: ChatMode = "react"  # 默认使用 ReAct 推理模式

    @field_validator("display_message", "session_id", mode="after")
    @classmethod
    def _empty_string_to_none(cls, value: str | None) -> str | None:
        """将空白可选字段转为 None，避免空字符串进入业务逻辑。

        例：用户提交 session_id="" 时，转为 None 表示"不指定会话"，
        而非尝试查找 ID 为空的会话。
        """

        return value or None
