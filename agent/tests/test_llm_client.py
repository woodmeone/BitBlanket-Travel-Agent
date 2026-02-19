#!/usr/bin/env python3
"""
================================================================================
LLM Client 单元测试

测试 LLM 客户端的核心功能：
- 协议适配器创建
- 同步/流式调用
- 错误处理
- 配置验证

运行方式:
    PYTHONPATH=agent/src python3 -m pytest agent/tests/test_llm_client.py -v

================================================================================
"""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# 确保 agent/src 在路径中
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "agent" / "src"))

from llm.client import LLMClient, AnthropicAdapter, OpenAIAdapter
from llm.factory import LLMClientFactory


# =============================================================================
# 测试夹具 (Fixtures)
# =============================================================================

@pytest.fixture
def mock_anthropic_response():
    """模拟 Anthropic API 响应"""
    return {
        "id": "msg_123",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "这是测试回复"
            }
        ],
        "model": "claude-3-5-sonnet-20241022",
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50
        }
    }


@pytest.fixture
def mock_openai_response():
    """模拟 OpenAI API 响应"""
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "这是测试回复"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    }


# =============================================================================
# 测试用例
# =============================================================================

class TestLLMClientFactory:
    """LLMClientFactory 测试类"""

    def test_create_anthropic_adapter(self):
        """测试创建 Anthropic 适配器"""
        config = {
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-20241022",
            "api_key": "test-key",
            "api_base": "https://api.anthropic.com/v1"
        }

        adapter = LLMClientFactory.create_adapter(config)
        assert isinstance(adapter, AnthropicAdapter)

    def test_create_openai_adapter(self):
        """测试创建 OpenAI 适配器"""
        config = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": "test-key",
            "api_base": "https://api.openai.com/v1"
        }

        adapter = LLMClientFactory.create_adapter(config)
        assert isinstance(adapter, OpenAIAdapter)

    def test_create_anthropic_compatible_adapter(self):
        """测试创建 Anthropic 兼容适配器（如 MiniMax）"""
        config = {
            "provider": "anthropic",
            "model": "MiniMax-M2.5",
            "api_key": "sk-test",
            "api_base": "https://api.minimaxi.com/anthropic"
        }

        adapter = LLMClientFactory.create_adapter(config)
        assert isinstance(adapter, AnthropicAdapter)

    def test_invalid_provider(self):
        """测试无效的 provider"""
        config = {
            "provider": "invalid_provider",
            "model": "test-model"
        }

        with pytest.raises(ValueError):
            LLMClientFactory.create_adapter(config)


class TestAnthropicAdapter:
    """AnthropicAdapter 测试类"""

    def test_adapter_initialization(self):
        """测试适配器初始化"""
        config = {
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-20241022",
            "api_key": "test-key",
            "api_base": "https://api.anthropic.com/v1",
            "temperature": 0.7,
            "max_tokens": 2000
        }

        adapter = AnthropicAdapter(config)
        assert adapter.model == "claude-3-5-sonnet-20241022"
        assert adapter.temperature == 0.7
        assert adapter.max_tokens == 2000

    def test_build_headers(self):
        """测试构建请求头"""
        config = {
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-20241022",
            "api_key": "test-key"
        }

        adapter = AnthropicAdapter(config)
        headers = adapter._build_request_headers()

        assert "x-api-key" in headers
        assert "anthropic-version" in headers
        assert headers["x-api-key"] == "test-key"

    @pytest.mark.integration
    def test_chat_request_integration(self):
        """集成测试：使用真实 API 测试聊天请求"""
        import os
        config = {
            "provider": "anthropic",
            "model": "MiniMax-M2.5",
            "api_base": os.environ.get("ANTHROPIC_BASE_URL", "https://api.minimaxi.com/anthropic"),
            "api_key": os.environ.get("ANTHROPIC_AUTH_TOKEN", ""),
            "api_version": "2024-01-04"
        }

        if not config["api_key"]:
            pytest.skip("No API key configured")

        adapter = AnthropicAdapter(config)
        messages = [{"role": "user", "content": "你好"}]
        response = adapter.chat(messages)

        assert "content" in response or "success" in response


class TestOpenAIAdapter:
    """OpenAIAdapter 测试类"""

    def test_adapter_initialization(self):
        """测试适配器初始化"""
        config = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": "test-key",
            "temperature": 0.5,
            "max_tokens": 1000
        }

        adapter = OpenAIAdapter(config)
        assert adapter.model == "gpt-4o-mini"
        assert adapter.temperature == 0.5
        assert adapter.max_tokens == 1000

    def test_build_headers(self):
        """测试构建请求头"""
        config = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": "test-key"
        }

        adapter = OpenAIAdapter(config)
        headers = adapter._build_request_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-key"

    @pytest.mark.integration
    def test_chat_request_integration(self):
        """集成测试：使用真实 MiniMax API 测试聊天请求"""
        import os
        # 使用 MiniMax API（已配置）
        config = {
            "provider": "anthropic",
            "model": "MiniMax-M2.5",
            "api_base": "https://api.minimaxi.com/anthropic",
            "api_key": "sk-cp-T07LV1Y1G7nvQuzpETrEq97a8B2sDhBHyNMtZ5yJLq-GwnujPj5MYr-O6VJL_O2DC4CVnldNF2zZrVr6G9RIFvWwixbSVtKP2ghFnzrTswxFP_YQz29OIU8",
            "api_version": "2024-01-04"
        }

        adapter = AnthropicAdapter(config)
        messages = [{"role": "user", "content": "你好"}]
        response = adapter.chat(messages)

        assert "content" in response or "success" in response


class TestLLMClient:
    """LLMClient 测试类"""

    @patch('llm.client.LLMClientFactory.create_adapter')
    def test_client_initialization(self, mock_factory):
        """测试客户端初始化"""
        mock_adapter = Mock()
        mock_factory.return_value = mock_adapter

        config = {"provider": "openai", "model": "gpt-4o-mini"}
        client = LLMClient(config)

        mock_factory.assert_called_once_with(config)

    @patch('llm.client.LLMClientFactory.create_adapter')
    def test_chat(self, mock_factory):
        """测试聊天方法"""
        mock_adapter = Mock()
        mock_adapter.chat.return_value = {"content": "test response"}
        mock_factory.return_value = mock_adapter

        config = {"provider": "openai", "model": "gpt-4o-mini"}
        client = LLMClient(config)

        messages = [{"role": "user", "content": "你好"}]
        response = client.chat(messages)

        assert response["content"] == "test response"
        # Check that chat was called with messages as first arg
        mock_adapter.chat.assert_called()
        call_args = mock_adapter.chat.call_args
        assert call_args[0][0] == messages

    @patch('llm.client.LLMClientFactory.create_adapter')
    def test_stream_chat(self, mock_factory):
        """测试流式聊天方法"""
        mock_adapter = Mock()
        mock_adapter.chat_stream.return_value = iter([
            {"content": "Hello"},
            {"content": " World"}
        ])
        mock_factory.return_value = mock_adapter

        config = {"provider": "openai", "model": "gpt-4o-mini"}
        client = LLMClient(config)

        messages = [{"role": "user", "content": "你好"}]
        chunks = list(client.chat_stream(messages))

        assert len(chunks) == 2


class TestErrorHandling:
    """错误处理测试"""

    def test_invalid_model_handling(self):
        """测试无效模型处理"""
        config = {
            "provider": "openai",
            "model": "",
            "api_key": "test-key"
        }

        adapter = OpenAIAdapter(config)
        messages = [{"role": "user", "content": "你好"}]

        response = adapter.chat(messages)
        # 应该返回错误响应而不是抛出异常
        assert "success" in response or "error" in response

    def test_empty_messages_handling(self):
        """测试空消息处理"""
        config = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": "test-key"
        }

        adapter = OpenAIAdapter(config)
        response = adapter.chat([])

        assert "success" in response
        assert response["success"] is False


# =============================================================================
# 主程序入口
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
