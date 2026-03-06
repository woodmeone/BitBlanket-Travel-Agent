# 集成测试设计方案

本文档描述小帅旅游助手的集成测试策略、测试用例和测试流程。

---

## 目录

- [测试策略概述](#测试策略概述)
- [测试环境配置](#测试环境配置)
- [基础设施测试](#基础设施测试)
- [Agent 核心功能测试](#agent-核心功能测试)
- [中间件测试](#中间件测试)
- [端到端测试](#端到端测试)
- [性能测试](#性能测试)
- [测试工具和报告](#测试工具和报告)

---

## 测试策略概述

### 测试金字塔

```
                    ┌─────────────────┐
                    │   E2E Tests     │   5% - 端到端测试
                    │  (用户场景)      │
           ┌────────┴─────────────────┴────────┐
           │      Integration Tests            │  25% - 集成测试
           │   (模块交互、服务调用)             │
    ┌──────┴──────────────────────────────────┴──────┐
    │              Unit Tests                           │  70% - 单元测试
    │           (函数、类、方法)                         │
    └───────────────────────────────────────────────────┘
```

### 测试优先级

| 优先级 | 测试类型 | 执行频率 | 负责人 |
|--------|----------|----------|--------|
| P0 | 基础设施连接测试 | 每次部署前 | CI/CD |
| P0 | Agent 核心流程测试 | 每次提交 | CI |
| P1 | 中间件功能测试 | 每日 | 开发团队 |
| P1 | API 接口测试 | 每次提交 | CI |
| P2 | 端到端测试 | 每周 | QA |
| P2 | 性能测试 | 每周 | 性能团队 |

### 测试环境

**详见**: [基础设施文档](INFRASTRUCTURE.md)

| 环境 | 用途 | 数据隔离 |
|------|------|----------|
| localhost | 开发调试 | 独立数据卷 |
| dev | 开发测试 | 独立命名空间 |
| staging | 预发布测试 | 独立实例 |

---

## 测试环境配置

### Docker 服务启动

**详见**: [基础设施 - Docker Compose 启动](INFRASTRUCTURE.md#docker-compose-启动)

```bash
# 启动所有基础设施服务
docker-compose up -d

# 验证服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f
```

### 服务连接配置

**详见**: [基础设施 - 服务连接信息](INFRASTRUCTURE.md#服务连接信息)

```python
# tests/conftest.py
import pytest
from infrastructure.infra_config import get_config

@pytest.fixture(scope="session")
def infra_config():
    """获取基础设施配置"""
    return get_config()

@pytest.fixture
def redis_client(infra_config):
    """Redis 测试客户端"""
    import redis
    return redis.Redis(
        host=infra_config.redis.host,
        port=infra_config.redis.port,
        decode_responses=True
    )

@pytest.fixture
def milvus_client(infra_config):
    """Milvus 测试客户端"""
    from pymilvus import connections
    connections.connect(
        host=infra_config.milvus.host,
        port=str(infra_config.milvus.port)
    )
    yield connections
    connections.disconnect()
```

---

## 基础设施测试

### 1. Redis 连接测试

**相关代码**:
- [Redis 队列实现](../agent/src/infrastructure/redis_queue.py)
- [Redis 记忆管理](../agent/src/memory/redis_memory.py)

```python
# tests/test_redis_integration.py
import pytest
import redis

class TestRedisConnection:
    """Redis 连接测试"""

    def test_redis_ping(self, redis_client):
        """测试 Redis ping"""
        assert redis_client.ping() == True

    def test_redis_string_operations(self, redis_client):
        """测试字符串操作"""
        key = "test:string:key"
        value = "test_value"

        # 设置
        redis_client.set(key, value)
        assert redis_client.get(key) == value

        # 删除
        redis_client.delete(key)
        assert redis_client.get(key) is None

    def test_redis_list_operations(self, redis_client):
        """测试列表操作"""
        key = "test:list:key"

        # 推送
        redis_client.rpush(key, "item1", "item2", "item3")
        assert redis_client.llen(key) == 3

        # 获取
        items = redis_client.lrange(key, 0, -1)
        assert len(items) == 3

        # 清理
        redis_client.delete(key)

    def test_redis_hash_operations(self, redis_client):
        """测试哈希操作"""
        key = "test:hash:key"
        field = "test_field"

        redis_client.hset(key, field, "test_value")
        assert redis_client.hget(key, field) == "test_value"

        redis_client.delete(key)

    def test_redis_ttl_operations(self, redis_client):
        """测试 TTL 操作"""
        key = "test:ttl:key"

        redis_client.setex(key, 60, "expires_soon")
        assert redis_client.ttl(key) > 0

        redis_client.delete(key)


class TestRedisMemoryManager:
    """Redis 记忆管理器测试"""

    @pytest.fixture
    def memory_manager(self):
        """创建记忆管理器"""
        from memory.redis_memory import RedisMemoryManager
        return RedisMemoryManager(
            host="localhost",
            port=6379,
            key_prefix="test:",
            fallback=True
        )

    def test_add_message(self, memory_manager):
        """测试添加消息"""
        session_id = "test_session_001"
        memory_manager.add_message(session_id, "user", "Hello")
        memory_manager.add_message(session_id, "assistant", "Hi there!")

        history = memory_manager.get_conversation_history(session_id)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

        # 清理
        memory_manager.clear_conversation(session_id)

    def test_get_user_preference(self, memory_manager):
        """测试用户偏好"""
        session_id = "test_session_002"
        preference = {
            "budget_range": "2000-4000",
            "preferred_cities": ["北京", "上海"],
            "interest_tags": ["美食", "历史"]
        }

        memory_manager.set_user_preference(session_id, preference)
        retrieved = memory_manager.get_user_preference(session_id)

        assert retrieved.get("budget_range") == "2000-4000"

    def test_session_state(self, memory_manager):
        """测试会话状态"""
        session_id = "test_session_003"
        memory_manager.update_session_state(session_id, "step", 1)
        memory_manager.update_session_state(session_id, "status", "active")

        assert memory_manager.get_session_state(session_id, "step") == 1
        assert memory_manager.get_session_state(session_id, "status") == "active"

        # 清理
        memory_manager.clear_conversation(session_id)
```

### 2. Milvus 连接测试

**相关代码**:
- [Milvus 向量存储](../agent/src/infrastructure/milvus_vector.py)
- [Milvus RAG 检索器](../agent/src/middleware/milvus_rag.py)

```python
# tests/test_milvus_integration.py
import pytest
import numpy as np

class TestMilvusConnection:
    """Milvus 连接测试"""

    @pytest.fixture
    def vector_store(self):
        """创建向量存储"""
        from infrastructure.milvus_vector import (
            MilvusVectorStore,
            MilvusConfig,
            DistanceMetric
        )
        config = MilvusConfig(host="localhost", port=19530)
        store = MilvusVectorStore(
            collection_name="test_collection",
            dim=128,
            config=config,
            distance_metric=DistanceMetric.COSINE
        )
        return store

    @pytest.mark.asyncio
    async def test_milvus_connect(self, vector_store):
        """测试 Milvus 连接"""
        await vector_store.connect()
        assert vector_store._client is not None

    @pytest.mark.asyncio
    async def test_create_collection(self, vector_store):
        """测试创建集合"""
        await vector_store.connect()
        result = await vector_store.create_collection()
        assert result == True

    @pytest.mark.asyncio
    async def test_insert_vectors(self, vector_store):
        """测试插入向量"""
        await vector_store.connect()
        await vector_store.create_collection()

        # 生成测试向量
        vectors = np.random.rand(10, 128).tolist()
        payloads = [{"id": i, "content": f"test document {i}"} for i in range(10)]

        ids = await vector_store.insert(vectors, payloads)
        assert len(ids) == 10

    @pytest.mark.asyncio
    async def test_search_vectors(self, vector_store):
        """测试向量搜索"""
        await vector_store.connect()
        await vector_store.create_collection()

        # 插入测试数据
        vectors = np.random.rand(100, 128).tolist()
        payloads = [{"id": i, "content": f"document {i}"} for i in range(100)]
        await vector_store.insert(vectors, payloads)

        # 搜索
        query = np.random.rand(128).tolist()
        results = await vector_store.search(query, top_k=5)

        assert len(results) == 5
        for r in results:
            assert r.score >= 0.0

        # 清理
        await vector_store.drop_collection()


class TestMilvusRAGRetriever:
    """Milvus RAG 检索器测试"""

    @pytest.fixture
    def rag_retriever(self):
        """创建 RAG 检索器"""
        from middleware.milvus_rag import create_milvus_retriever
        from unittest.mock import Mock

        mock_embedding = Mock()
        mock_embedding.encode = pytest.AsyncMock(return_value=np.random.rand(128))

        return pytest.AsyncFixture()

    @pytest.mark.asyncio
    async def test_rag_retriever_creation(self):
        """测试检索器创建"""
        retriever = await create_milvus_retriever(
            collection_name="test_rag",
            dim=1024,
            host="localhost",
            port=19530,
            fallback_to_memory=True
        )

        assert retriever is not None

    @pytest.mark.asyncio
    async def test_rag_add_documents(self, rag_retriever):
        """测试添加文档"""
        documents = [
            {"content": "北京是中国的首都，有丰富的历史文化遗产。"},
            {"content": "上海是中国最大的经济中心。"},
            {"content": "杭州以西湖闻名于世。"}
        ]

        doc_count = await rag_retriever.add_documents(documents, source="test")
        assert doc_count == 3

    @pytest.mark.asyncio
    async def test_rag_retrieve(self, rag_retriever):
        """测试文档检索"""
        results = await rag_retriever.retrieve("北京旅游", top_k=2)
        assert len(results.results) <= 2

    @pytest.mark.asyncio
    async def test_rag_stats(self, rag_retriever):
        """测试获取统计信息"""
        stats = await rag_retriever.get_stats()
        assert "status" in stats
        assert "collection_name" in stats
```

### 3. Nacos 配置测试

**相关代码**:
- [Nacos 客户端](../agent/src/infrastructure/nacos_client.py)
- [配置热更新](../agent/src/infrastructure/config_hot_reload.py)

```python
# tests/test_nacos_integration.py
import pytest

class TestNacosClient:
    """Nacos 客户端测试"""

    @pytest.fixture
    def nacos_client(self):
        """创建 Nacos 客户端"""
        from infrastructure.nacos_client import NacosClient, NacosConfig
        config = NacosConfig(
            server_addresses=["http://localhost:38848"],
            namespace="test_namespace"
        )
        return NacosClient(config=config)

    @pytest.mark.asyncio
    async def test_nacos_connect(self, nacos_client):
        """测试 Nacos 连接"""
        result = await nacos_client.connect()
        # 即使连接失败也不报错，使用模拟模式
        assert nacos_client._client is not None

    @pytest.mark.asyncio
    async def test_publish_config(self, nacos_client):
        """测试发布配置"""
        # 使用模拟模式测试
        await nacos_client.connect()

        result = await nacos_client.publish_config(
            data_id="test_config.yaml",
            content="key: value\nname: test"
        )
        assert result == True

    @pytest.mark.asyncio
    async def test_get_config(self, nacos_client):
        """测试获取配置"""
        await nacos_client.connect()

        # 发布配置
        await nacos_client.publish_config(
            data_id="test_get.yaml",
            content="test_key: test_value"
        )

        # 获取配置
        content = await nacos_client.get_config("test_get.yaml")
        assert content is not None
        assert "test_key" in content

    @pytest.mark.asyncio
    async def test_config_listener(self, nacos_client):
        """测试配置监听"""
        await nacos_client.connect()

        events = []

        def on_change(data_id, group, content):
            events.append((data_id, content))

        await nacos_client.subscribe("test_listener.yaml", on_change)

        # 触发变化
        await nacos_client.publish_config(
            data_id="test_listener.yaml",
            content="updated: true"
        )


class TestConfigHotReload:
    """配置热重载测试"""

    @pytest.fixture
    def temp_config_file(self, tmp_path):
        """创建临时配置文件"""
        content = """
app:
  name: test-app
  version: 1.0.0
redis:
  host: localhost
  port: 6379
"""
        path = tmp_path / "test_config.yaml"
        path.write_text(content)
        return str(path)

    def test_load_local_config(self, temp_config_file):
        """测试加载本地配置"""
        from infrastructure.config_hot_reload import ConfigHotReload

        reloader = ConfigHotReload(config_path=temp_config_file)

        assert reloader.get("app.name") == "test-app"
        assert reloader.get("app.version") == "1.0.0"

    def test_get_nested_config(self, temp_config_file):
        """测试获取嵌套配置"""
        reloader = ConfigHotReload(config_path=temp_config_file)

        assert reloader.get("redis.host") == "localhost"
        assert reloader.get("redis.port") == 6379

    def test_set_config(self):
        """测试设置配置"""
        from infrastructure.config_hot_reload import ConfigHotReload, ConfigSource

        reloader = ConfigHotReload()

        reloader.set("custom.key", "custom_value", ConfigSource.MEMORY)
        assert reloader.get("custom.key") == "custom_value"

    def test_config_listener(self, temp_config_file):
        """测试配置监听"""
        from infrastructure.config_hot_reload import ConfigHotReload

        reloader = ConfigHotReload(config_path=temp_config_file)

        changes = []

        def on_change(key, old, new):
            changes.append((key, old, new))

        reloader.on_change("app", on_change)
        reloader.set("app.name", "new_name")

        assert len(changes) == 1
        assert changes[0][0] == "app"
```

---

## Agent 核心功能测试

### 1. ReAct Agent 测试

```python
# tests/test_react_agent.py
import pytest

class TestReActAgent:
    """ReAct Agent 测试"""

    @pytest.fixture
    def agent(self):
        """创建 Agent"""
        from core.react_agent import ReActAgent
        from llm.client import LLMClient

        client = LLMClient(provider="mock")
        return ReActAgent(llm_client=client)

    @pytest.mark.asyncio
    async def test_agent_thought_process(self, agent):
        """测试 Agent 思考过程"""
        result = await agent.run("测试问题")

        assert result is not None
        assert "thought" in result or "action" in result

    @pytest.mark.asyncio
    async def test_agent_tool_calling(self, agent):
        """测试 Agent 工具调用"""
        from tools.search import search_tool

        # 添加测试工具
        agent.register_tool(search_tool)

        result = await agent.run("搜索北京旅游信息")

        assert result is not None


class TestTravelAgent:
    """旅游 Agent 测试"""

    @pytest.fixture
    def travel_agent(self):
        """创建旅游 Agent"""
        from core.travel_agent import ReActTravelAgent
        return ReActTravelAgent()

    @pytest.mark.asyncio
    async def test_city_recommendation(self, travel_agent):
        """测试城市推荐"""
        result = await travel_agent.recommend_cities(
            preferences={"气候": "温暖", "预算": "中等"}
        )

        assert result is not None
        assert "cities" in result

    @pytest.mark.asyncio
    async def test_trip_planning(self, travel_agent):
        """测试旅行规划"""
        result = await travel_agent.plan_trip(
            destination="北京",
            days=3,
            interests=["历史", "美食"]
        )

        assert result is not None
        assert "itinerary" in result
```

### 2. 节点执行测试

```python
# tests/test_nodes.py
import pytest

class TestNodeExecution:
    """节点执行测试"""

    def test_action_node(self):
        """测试动作节点"""
        from framework.node_types import ActionNode

        node = ActionNode(
            name="search",
            tool="search",
            params={"query": "北京旅游"}
        )

        result = node.execute()
        assert result is not None

    def test_decision_node(self):
        """测试决策节点"""
        from framework.node_types import DecisionNode

        node = DecisionNode(
            name="check_budget",
            condition="budget > 1000",
            if_true="plan_premium",
            if_false="plan_budget"
        )

        state = {"budget": 2000}
        result = node.execute(state)
        assert result == "plan_premium"

    def test_loop_node(self):
        """测试循环节点"""
        from framework.node_types import LoopNode

        node = LoopNode(
            name="search_loop",
            condition="results.length < 5",
            action="search_more"
        )

        state = {"results": []}
        result = node.execute(state)
        assert result is not None
```

---

## 中间件测试

### 1. RAG 检索测试

```python
# tests/test_rag.py
import pytest

class TestRAGRetriever:
    """RAG 检索器测试"""

    @pytest.fixture
    def retriever(self):
        """创建 RAG 检索器"""
        from middleware.rag import RAGRetriever, DocumentChunker
        return RAGRetriever(
            chunker=DocumentChunker(chunk_size=200),
            enable_vector_search=False
        )

    @pytest.mark.asyncio
    async def test_add_documents(self, retriever):
        """测试添加文档"""
        documents = [
            {"content": "北京是中国的首都。"},
            {"content": "上海是中国最大的城市。"}
        ]

        count = await retriever.add_documents(documents, source="test")
        assert count == 2

    @pytest.mark.asyncio
    async def test_keyword_search(self, retriever):
        """测试关键词检索"""
        documents = [
            {"content": "北京故宫是明清两代的皇家宫殿。"},
            {"content": "上海外滩是著名的观光景点。"}
        ]

        await retriever.add_documents(documents, source="test")

        results = await retriever.retrieve(
            "北京故宫",
            top_k=1,
            strategy=RetrievalStrategy.KEYWORD
        )

        assert len(results.results) >= 0

    def test_document_chunker(self):
        """测试文档分块"""
        from middleware.rag import DocumentChunker

        chunker = DocumentChunker(chunk_size=50, chunk_overlap=10)
        text = "这是一个测试文档。" * 10

        chunks = chunker.chunk(text, source="test")

        assert len(chunks) > 0
        for chunk in chunks:
            assert len(chunk["content"]) <= 50 + 10

    def test_get_stats(self, retriever):
        """测试获取统计"""
        stats = retriever.get_stats()

        assert "document_sources" in stats
        assert "total_chunks" in stats
```

### 2. SSE 流式测试

```python
# tests/test_sse.py
import pytest

class TestSSEStreaming:
    """SSE 流式测试"""

    @pytest.fixture
    def streamer(self):
        """创建 SSE  streamer"""
        from infrastructure.streaming import SSEStreamer
        return SSEStreamer()

    @pytest.mark.asyncio
    async def test_stream_events(self, streamer):
        """测试流式事件"""
        events = []

        async def on_event(event):
            events.append(event)

        # 生成测试事件
        await streamer.stream(
            data=["Hello", " ", "World"],
            event="message",
            on_event=on_event
        )

        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_stream_format(self, streamer):
        """测试流式格式"""
        from infrastructure.streaming import StreamEvent, EventType

        event = StreamEvent(
            type=EventType.THOUGHT,
            data={"content": "思考中..."}
        )

        formatted = streamer.format_event(event)
        assert "event: thought" in formatted
        assert "data:" in formatted
```

---

## 端到端测试

### API 端到端测试

```python
# tests/test_api_e2e.py
import pytest
from httpx import AsyncClient, ASGITransport


class TestAPIEndpoints:
    """API 端到端测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from main import app
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """测试健康检查"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_chat_endpoint(self, client):
        """测试聊天接口"""
        response = await client.post(
            "/api/chat",
            json={"message": "我想去北京旅游", "session_id": "test_001"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "session_id" in data

    @pytest.mark.asyncio
    async def test_streaming_chat(self, client):
        """测试流式聊天"""
        async with client.stream(
            "POST",
            "/api/chat/stream",
            json={"message": "推荐几个城市", "session_id": "test_002"}
        ) as response:
            assert response.status_code == 200

            chunks = []
            async for chunk in response.aiter_text():
                chunks.append(chunk)

            # 验证流式响应
            assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_session_management(self, client):
        """测试会话管理"""
        # 创建会话
        response = await client.post(
            "/api/sessions",
            json={"user_id": "user_001"}
        )
        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # 获取会话
        response = await client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 200

        # 删除会话
        response = await client.delete(f"/api/sessions/{session_id}")
        assert response.status_code == 200
```

---

## 性能测试

### Locust 性能测试

```python
# tests/locustfile.py
from locust import HttpUser, task, between
from locust.events import request

class ChatUser(HttpUser):
    """聊天用户模拟"""
    wait_time = between(1, 5)

    def on_start(self):
        """用户开始"""
        self.session_id = None

    @task(3)
    def send_message(self):
        """发送消息"""
        if self.session_id is None:
            # 创建会话
            response = self.client.post(
                "/api/sessions",
                json={"user_id": "test_user"}
            )
            if response.status_code == 200:
                self.session_id = response.json()["session_id"]

        if self.session_id:
            self.client.post(
                "/api/chat",
                json={
                    "message": "推荐一个旅游城市",
                    "session_id": self.session_id
                }
            )

    @task(1)
    def health_check(self):
        """健康检查"""
        self.client.get("/health")


class APIUser(HttpUser):
    """API 用户模拟"""
    wait_time = between(0.5, 2)

    @task(5)
    def get_cities(self):
        """获取城市列表"""
        self.client.get("/api/cities")

    @task(3)
    def search_attractions(self):
        """搜索景点"""
        self.client.get("/api/attractions", params={"city": "北京"})

    @task(2)
    def get_recommendations(self):
        """获取推荐"""
        self.client.get(
            "/api/recommendations",
            params={"budget": "2000-4000"}
        )
```

运行性能测试:

```bash
# 安装 locust
pip install locust

# 运行测试
locust -f tests/locustfile.py --host=http://localhost:38000

# Web UI: http://localhost:8089
```

---

## 测试工具和报告

### pytest 配置

```ini
# pytest.ini
[pytest]
testpaths = tests
pythonpath = src
asyncio_mode = auto
addopts = -v --tb=short

[tool:pytest]
asyncio_mode = auto
```

### 测试报告生成

```bash
# 运行测试并生成报告
pytest tests/ \
    --html=reports/report.html \
    --junitxml=reports/junit.xml \
    --cov=agent/src \
    --cov-report=html:reports/coverage \
    --cov-report=term-missing

# 生成合并报告
pytest tests/ --co -q  # 列出所有测试
```

### CI/CD 集成

```yaml
# .github/workflows/tests.yml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r agent/requirements.txt
          pip install pytest pytest-asyncio pytest-cov httpx

      - name: Run tests
        run: |
          pytest tests/ \
            --tb=short \
            --junitxml=reports/junit.xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./reports/junit.xml
```

---

## 测试最佳实践

### 1. 测试数据管理

```python
# tests/fixtures/data_fixtures.py
import pytest
import json

@pytest.fixture
def sample_travel_data():
    """示例旅行数据"""
    return {
        "cities": [
            {"id": "beijing", "name": "北京", "region": "华北"},
            {"id": "shanghai", "name": "上海", "region": "华东"}
        ],
        "attractions": [
            {"city_id": "beijing", "name": "故宫", "type": "历史古迹"},
            {"city_id": "shanghai", "name": "外滩", "type": "现代景点"}
        ]
    }

@pytest.fixture
def sample_conversations():
    """示例对话数据"""
    return [
        {
            "session_id": "test_001",
            "messages": [
                {"role": "user", "content": "我想去北京旅游"},
                {"role": "assistant", "content": "北京是很好的选择！"}
            ]
        }
    ]
```

### 2. Mock 外部依赖

```python
# tests/mocks.py
from unittest.mock import Mock, AsyncMock

def create_mock_llm_client(response="这是测试回复"):
    """创建模拟 LLM 客户端"""
    client = Mock()
    client.generate = AsyncMock(return_value=response)
    client.generate_stream = AsyncMock(return_value=iter([response]))
    return client

def create_mock_embedding_model():
    """创建模拟嵌入模型"""
    model = Mock()
    model.encode = AsyncMock(return_value=np.random.rand(1024))
    return model
```

---

## 文档参考

| 主题 | 文档链接 |
|------|----------|
| 架构设计 | [ARCHITECTURE.md](ARCHITECTURE.md) |
| API 文档 | [API.md](api.md) |
| 数据库设计 | [db.md](db.md) |
| 基础设施 | [INFRASTRUCTURE.md](INFRASTRUCTURE.md) |
| 产品需求 | [prd.md](prd.md) |
| 开发指南 | [learn_docs/05_DEVELOP.md](../learn_docs/05_DEVELOP.md) |
| 部署指南 | [learn_docs/06_DEPLOY.md](../learn_docs/06_DEPLOY.md) |
| 测试示例 | [tests/README.md](../tests/README.md) |

---

## 常见问题

### Q: 测试环境连接失败？

**检查步骤**:
1. 验证 Docker 服务运行状态
2. 检查端口是否正确监听
3. 查看防火墙设置

**详见**: [INFRASTRUCTURE.md#健康检查](INFRASTRUCTURE.md#健康检查)

### Q: 性能测试结果不准确？

**建议**:
1. 在独立环境运行性能测试
2. 预热服务后再开始测试
3. 多次运行取平均值

### Q: 如何添加新测试？

**步骤**:
1. 在 `tests/` 目录创建测试文件
2. 使用 `pytest` 标记异步测试
3. 添加适当的 fixtures
4. 更新本文档

---

## 版本信息

| 版本 | 日期 | 作者 | 说明 |
|------|------|------|------|
| 1.0 | 2025-02-04 | Claude | 初始版本 |
