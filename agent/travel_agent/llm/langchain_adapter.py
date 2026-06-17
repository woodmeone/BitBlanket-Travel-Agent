"""
LLM 适配器（LangChain Adapter）

将现有的 LLM 配置适配到 LangChain 框架，封装不同大模型 API 的调用方式。
支持多种 Provider，保留现有的配置结构，对上层调用者屏蔽底层差异。

LangChain 概念说明：
  - BaseChatModel：LangChain 中聊天模型的基类，定义了 invoke/stream/ainvoke/astream 等接口
  - ChatOpenAI：LangChain 对 OpenAI API 的封装，也兼容所有 OpenAI 格式的 API
  - ChatAnthropic：LangChain 对 Anthropic Claude API 的封装
  - BaseMessage：LangChain 消息基类，子类包括 HumanMessage（用户消息）、AIMessage（AI回复）、SystemMessage（系统提示）
  - provider：大模型服务提供商，如 "openai"、"anthropic" 等

支持的 Provider：
  - openai：标准 OpenAI API（如 GPT-4）
  - openai-compatible：兼容 OpenAI 格式的 API（如硅基流动、zhiercourse 等国内中转服务）
  - anthropic：标准 Anthropic Claude API
  - anthropic-compatible：兼容 Anthropic 格式的 API（如 MiniMax）

旅行场景举例：
  用户问"成都3日游" → Agent 需要调用 LLM 生成行程
  → 通过本适配器，根据配置选择 OpenAI 或 Anthropic 的 API
  → 统一返回 LangChain 的 BaseMessage 格式，下游无需关心具体 Provider
"""

import os
from typing import Optional, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

# LangChain 1.0+ 的核心类型导入
# BaseChatModel：所有聊天模型的抽象基类，定义了 invoke/stream 等标准接口
from langchain_core.language_models.chat_models import BaseChatModel

from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.callbacks import CallbackManagerForLLMRun

# LangChain 模型：按需导入，未安装时设为 None 避免导入错误
try:
    from langchain_openai import ChatOpenAI  # OpenAI 及兼容 API 的聊天模型封装
except ImportError:
    ChatOpenAI = None

try:
    from langchain_anthropic import ChatAnthropic  # Anthropic Claude 的聊天模型封装
except ImportError:
    ChatAnthropic = None


class LangChainLLMAdapter:
    """【核心】LLM 适配器，将现有配置转换为 LangChain 的 ChatModel。

    支持多种 provider，保留现有的配置结构，对上层屏蔽底层 API 差异。
    """

    def __init__(self, config: dict):
        """
        初始化适配器

        Args:
            config: LLM 配置字典，应包含:
                - provider: 提供商类型（"openai" / "openai-compatible" / "anthropic" / "anthropic-compatible"）
                - model: 模型名称（如 "gpt-4o-mini"、"claude-3-sonnet"）
                - api_key: API 密钥
                - api_base: API 基础 URL（兼容模式必需）
                - temperature: 温度参数（0~2，越高越随机）
                - max_tokens: 最大生成 token 数
                - timeout: 请求超时时间（秒）
        """
        self.config = config
        self._chat_model = self._create_chat_model()

    def _create_chat_model(self) -> BaseChatModel:
        """【核心】根据配置创建对应的 ChatModel 实例。

        根据 provider 字段选择不同的 LangChain 聊天模型类：
          - "openai" → ChatOpenAI（标准 OpenAI API）
          - "openai-compatible" → ChatOpenAI + base_url（兼容 OpenAI 格式的第三方 API）
          - "anthropic" → ChatAnthropic（标准 Anthropic Claude API）
          - "anthropic-compatible" → ChatAnthropic + base_url（兼容 Anthropic 格式的第三方 API）
        """
        provider = self.config.get('provider', 'openai-compatible')  # 提供商类型
        model = self.config.get('model', 'gpt-4o-mini')  # 模型名称
        api_key = self.config.get('api_key', '')  # API 密钥
        api_base = self.config.get('api_base', '')  # API 基础 URL
        temperature = self.config.get('temperature', 0.7)  # 温度参数：控制生成随机性，0=确定性，2=高随机
        max_tokens = self.config.get('max_tokens', 2000)  # 最大生成 token 数
        timeout = self.config.get('timeout', 60)  # 请求超时时间（秒）

        # 构建通用参数（OpenAI 和兼容模式共用）
        common_kwargs = {
            'model': model,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'timeout': timeout,
        }

        # 添加 API 密钥（如果提供）
        if api_key:
            common_kwargs['api_key'] = api_key

        if provider == 'openai':
            # 标准 OpenAI API（如官方 GPT-4）
            if ChatOpenAI is None:
                raise ImportError("langchain-openai not installed")
            return ChatOpenAI(**common_kwargs)

        elif provider == 'openai-compatible':
            # 兼容 OpenAI 格式的第三方 API
            # 如硅基流动（https://api.siliconflow.cn/v1）、zhiercourse 等
            if ChatOpenAI is None:
                raise ImportError("langchain-openai not installed")
            if api_base:
                common_kwargs['base_url'] = api_base  # 设置自定义 API 地址
            return ChatOpenAI(**common_kwargs)

        elif provider == 'anthropic':
            # 标准 Anthropic Claude API
            if ChatAnthropic is None:
                raise ImportError("langchain-anthropic not installed")
            # Anthropic 使用不同的参数名：anthropic_api_key 而非 api_key
            anthropic_kwargs = {
                'model': model.replace('claude-', 'claude-'),
                'anthropic_api_key': api_key,  # Anthropic 的 API 密钥参数名
                'temperature': temperature,
                'max_tokens': max_tokens,
            }
            if api_base:
                anthropic_kwargs['base_url'] = api_base
            return ChatAnthropic(**anthropic_kwargs)

        elif provider == 'anthropic-compatible':
            # 兼容 Anthropic 格式的第三方 API（如 MiniMax）
            if ChatAnthropic is None:
                raise ImportError("langchain-anthropic not installed")
            anthropic_kwargs = {
                'model': model,
                'anthropic_api_key': api_key,
                'base_url': api_base,  # 兼容模式必须提供 base_url
                'temperature': temperature,
                'max_tokens': max_tokens,
            }
            return ChatAnthropic(**anthropic_kwargs)

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    @property
    def chat_model(self) -> BaseChatModel:
        """获取底层的 ChatModel 实例，可用于直接调用 LangChain 原生接口。"""
        return self._chat_model

    def invoke(self, messages: list[BaseMessage], **kwargs) -> BaseMessage:
        """同步调用 LLM，等待完整响应后返回。

        Args:
            messages: 消息列表，通常包含 SystemMessage + HumanMessage 的对话历史
            **kwargs: 传递给底层模型的其他参数

        Returns:
            AI 响应消息（AIMessage 实例）

        旅行场景举例：
          messages = [SystemMessage("你是旅行助手"), HumanMessage("成都3日游怎么安排？")]
          response = adapter.invoke(messages)
          # response.content = "第一天：宽窄巷子..."
        """
        return self._chat_model.invoke(messages, **kwargs)

    def stream(self, messages: list[BaseMessage], **kwargs):
        """流式调用 LLM，逐块返回响应（适合实时展示生成过程）。

        Args:
            messages: 消息列表
            **kwargs: 传递给底层模型的其他参数

        Yields:
            响应块（AIMessageChunk 实例），每个块包含一小段文本

        旅行场景举例：
          for chunk in adapter.stream(messages):
              print(chunk.content, end="")  # 逐字输出："第""一""天""：""宽""窄""巷""子""..."
        """
        return self._chat_model.stream(messages, **kwargs)

    async def ainvoke(self, messages: list[BaseMessage], **kwargs) -> BaseMessage:
        """异步调用 LLM，不阻塞事件循环，适合并发场景。

        Args:
            messages: 消息列表
            **kwargs: 传递给底层模型的其他参数

        Returns:
            AI 响应消息（AIMessage 实例）
        """
        return await self._chat_model.ainvoke(messages, **kwargs)

    async def astream(self, messages: list[BaseMessage], **kwargs):
        """异步流式调用 LLM，结合了异步和流式的优势。

        Args:
            messages: 消息列表
            **kwargs: 传递给底层模型的其他参数

        Yields:
            响应块（AIMessageChunk 实例）
        """
        async for chunk in self._chat_model.astream(messages, **kwargs):
            yield chunk


def create_langchain_llm(config: dict) -> LangChainLLMAdapter:
    """工厂函数：创建 LangChain LLM 适配器。

    Args:
        config: LLM 配置字典

    Returns:
        LangChainLLMAdapter 实例
    """
    return LangChainLLMAdapter(config)


def create_from_yaml_config(config_path: str) -> LangChainLLMAdapter:
    """从 YAML 配置文件创建适配器。

    YAML 文件应包含 models 字典和 default_model 字段，
    根据 default_model 指定的名称从 models 中选取对应配置。

    Args:
        config_path: YAML 配置文件路径

    Returns:
        LangChainLLMAdapter 实例

    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 默认模型配置未找到
    """
    import yaml
    from pathlib import Path

    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_file, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)

    # 获取默认模型名称，然后从 models 字典中查找对应配置
    default_model = config_data.get('default_model', 'gpt-4o-mini')  # 默认模型名称
    model_config = config_data.get('models', {}).get(default_model, {})  # 模型配置字典

    if not model_config:
        raise ValueError(f"Model config not found for: {default_model}")

    return create_langchain_llm(model_config)
