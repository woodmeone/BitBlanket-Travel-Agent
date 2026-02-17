# 开发指南

本指南面向开发者，介绍项目结构、开发环境搭建、代码规范、调试技巧等内容。

---

## 1. 开发环境搭建

### 1.1 前置条件

| 工具 | 版本要求 | 说明 |
|------|----------|------|
| Python | 3.10+ | 后端开发 |
| Node.js | 18+ | 前端开发 |
| npm | 9+ | 包管理 |
| Git | 2.0+ | 版本控制 |

### 1.2 克隆项目

```bash
git clone https://github.com/your-repo/ShuaiTravelAgent.git
cd ShuaiTravelAgent
```

### 1.3 安装后端依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 1.4 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

### 1.5 配置环境变量

创建 `config/config.json`:

```json
{
  "agent_name": "TravelAssistantAgent",
  "version": "1.0.0",
  "llm": {
    "provider_type": "openai",
    "api_base": "https://api.openai.com/v1",
    "api_key": "YOUR_API_KEY_HERE",
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "web": {
    "host": "0.0.0.0",
    "port": 48081,
    "debug": true
  }
}
```

创建 `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_BASE=http://localhost:48081
```

---

## 2. 项目结构

### 2.1 目录概览

```
ShuaiTravelAgent/
├── agent/           # AI Agent 模块
├── web/             # Web API 模块
├── shared/          # 共享模块
├── frontend/        # Next.js 前端
├── config/          # 配置文件
├── data/            # 数据存储
├── scripts/         # 脚本工具
└── tests/           # 测试文件
```

### 2.2 模块职责

```
agent/    - AI推理引擎、工具调用、LLM交互
web/      - HTTP API、路由、会话管理
frontend/ - 用户界面、状态管理、API调用
shared/   - 类型定义、常量、协议定义
```

---

## 3. 开发工作流

### 3.1 日常开发

**终端1 - 启动后端（热重载）**

```bash
# 方式1: 使用 run_api.py
python run_api.py

# 方式2: 使用 uvicorn 直接
cd web/src
uvicorn main:app --reload --host 0.0.0.0 --port 48081
```

**终端2 - 启动前端（热更新）**

```bash
cd frontend
npm run dev
```

**终端3 - 运行测试（可选）**

```bash
# 后端测试
python -m pytest src/tests/ -v

# 前端测试
cd frontend
npm run test:run
```

### 3.2 代码修改流程

```
1. 创建功能分支
   git checkout -b feature/your-feature

2. 编写代码
   - 修改相关模块
   - 遵循代码规范

3. 添加测试
   - 单元测试
   - 集成测试

4. 运行测试
   - 确保全部通过

5. 提交代码
   git add .
   git commit -m "feat: 添加新功能"

6. 推送并创建 PR
```

---

## 4. 代码规范

### 4.1 Python 代码规范

**命名约定**

```python
# 包名: 小写简短
import utils
from core import agent

# 类名: PascalCase
class SessionManager:
    ...

# 函数/变量: snake_case
def get_session_id():
    session_count = 0

# 常量: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3

# 私有方法/变量: 前缀_
class UserService:
    def _private_method(self):
        ...
    _private_var = 42
```

**类型注解**

```python
from typing import Dict, List, Optional, Any

def process_message(
    message: str,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    ...
```

**文档字符串**

```python
class SessionManager:
    """管理用户会话的生命周期。

    负责会话的创建、更新、删除和持久化。
    """

    def create_session(self, name: str) -> str:
        """创建新会话。

        Args:
            name: 会话名称

        Returns:
            新创建的会话ID

        Raises:
            ValueError: 会话名称为空
        """
        ...
```

### 4.2 TypeScript 代码规范

**命名约定**

```typescript
// 文件名: kebab-case
chat-service.ts
session-store.ts

// 类/接口: PascalCase
interface SessionState {
    id: string;
    name: string;
}

// 函数/变量: camelCase
function createSession(name: string): string {
    const sessionId = generateId();
    return sessionId;
}

// 常量: UPPER_SNAKE_CASE 或 camelCase
const MAX_SESSION_COUNT = 100;
const defaultSessionName = '新会话';
```

**类型定义**

```typescript
// 接口定义
interface Message {
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp?: string;
    reasoning?: string;
}

// 类型别名
type SessionStatus = 'active' | 'inactive' | 'expired';

// 函数类型
type ChatHandler = (message: string) => Promise<string>;
```

### 4.3 代码格式化

**Python (Ruff)**

```bash
# 检查代码
ruff check .

# 自动修复
ruff check --fix .
```

**TypeScript (ESLint + Prettier)**

```bash
# 检查代码
npm run lint

# 修复
npm run lint:fix
```

---

## 5. 调试技巧

### 5.1 后端调试

**日志输出**

```python
import logging

logger = logging.getLogger(__name__)

def my_function():
    logger.info("函数开始执行")
    logger.debug(f"调试信息: {variable}")
    logger.warning("警告信息")
    logger.error("错误信息")
```

**断点调试**

```bash
# 使用 Python debugger
python -m pdb script.py

# 或使用 VS Code
# 1. F5 启动调试
# 2. 设置断点
# 3. 查看变量
```

**API 测试**

使用 Swagger 文档: http://localhost:48081/docs

### 5.2 前端调试

**浏览器开发者工具**

```javascript
// console.log 调试
console.log('变量值:', variable);
console.error('错误:', error);

// 调试组件
console.trace();
```

**React DevTools**

- 安装 Chrome/Firefox 扩展
- 查看组件树
- 检查 state/props

**网络请求**

- Network 面板查看 API 请求
- 检查 SSE 流式响应

### 5.3 常见问题排查

| 问题 | 解决方案 |
|------|----------|
| 后端启动失败 | 检查 config.json 是否存在，API Key 是否配置 |
| 前端无法连接后端 | 检查 NEXT_PUBLIC_API_BASE 环境变量 |
| 端口被占用 | 修改端口或杀死占用进程 |
| 依赖安装失败 | 检查 Python/Node 版本，清理缓存 |

---

## 6. 添加新功能

### 6.1 添加新工具（Agent模块）

**步骤1: 定义工具**

```python
# agent/src/tools/travel_tools.py
from .base import Tool, ToolResult

class CitySearchTool(Tool):
    """城市搜索工具"""

    @property
    def name(self) -> str:
        return "search_cities"

    @property
    def description(self) -> str:
        return "根据条件搜索城市"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "region": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}}
            }
        }

    async def execute(self, region: str = None, tags: List[str] = None) -> ToolResult:
        # 实现搜索逻辑
        return ToolResult(success=True, data={...})
```

**步骤2: 注册工具**

```python
# agent/src/core/travel_agent.py
def _register_tools(self) -> None:
    tools = [
        # ... 现有工具
        (CitySearchTool(), self._search_cities),
    ]
    for tool_info, executor in tools:
        self.react_agent.register_tool(tool_info, executor)
```

**步骤3: 添加工具执行函数**

```python
def _search_cities(self, region: str = None, tags: List[str] = None) -> Dict[str, Any]:
    from ..environment.travel_data import TravelData
    env = TravelData(self.config_manager)
    return env.search_cities(region=region, interests=tags)
```

### 6.2 添加新API端点

**步骤1: 创建路由文件**

```python
# web/src/routes/analytics.py
from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter()

@router.get("/analytics/summary")
async def get_analytics_summary(days: int = 7):
    """获取分析摘要"""
    # 实现逻辑
    return {"summary": {...}}
```

**步骤2: 注册路由**

```python
# web/src/main.py
from .routes import (
    chat_router,
    session_router,
    analytics_router,  # 新增
    # ...
)

app.include_router(analytics_router, prefix="/api", tags=["analytics"])
```

### 6.3 添加新前端组件

**步骤1: 创建组件**

```typescript
// frontend/src/components/analytics/AnalyticsPanel.tsx
import { useState, useEffect } from 'react';
import { Card, Statistic } from 'antd';

interface AnalyticsData {
    totalSessions: number;
    totalMessages: number;
    avgResponseTime: number;
}

export function AnalyticsPanel() {
    const [data, setData] = useState<AnalyticsData | null>(null);

    useEffect(() => {
        // 加载数据
    }, []);

    if (!data) return <div>加载中...</div>;

    return (
        <Card>
            <Statistic title="总会话数" value={data.totalSessions} />
            <Statistic title="总消息数" value={data.totalMessages} />
        </Card>
    );
}
```

**步骤2: 添加到页面**

```typescript
// frontend/src/app/page.tsx
import { AnalyticsPanel } from '@/components/analytics/AnalyticsPanel';

export default function HomePage() {
    return (
        <div>
            <AnalyticsPanel />
            {/* 其他组件 */}
        </div>
    );
}
```

### 6.4 添加测试

**后端测试**

```python
# tests/unit/test_services/test_analytics_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_repository():
    repo = MagicMock()
    repo.get_summary = AsyncMock(return_value={...})
    return repo

@pytest.mark.asyncio
async def test_get_analytics_summary(mock_repository):
    from web.src.services.analytics_service import AnalyticsService
    service = AnalyticsService(mock_repository)

    result = await service.get_summary(days=7)

    assert result['success'] is True
    assert 'summary' in result
```

**前端测试**

```typescript
// tests/unit/components/AnalyticsPanel.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { AnalyticsPanel } from '@/components/analytics/AnalyticsPanel';
import { describe, it, expect, vi } from 'vitest';

describe('AnalyticsPanel', () => {
    it('显示加载状态', () => {
        render(<AnalyticsPanel />);
        expect(screen.getByText('加载中...')).toBeInTheDocument();
    });
});
```

---

## 7. Git 工作流

### 7.1 分支命名

| 分支类型 | 命名示例 | 说明 |
|----------|----------|------|
| 主分支 | `main` | 生产环境代码 |
| 开发分支 | `develop` | 开发主分支 |
| 功能分支 | `feature/chat-streaming` | 新功能 |
| 修复分支 | `bugfix/fix-session-bug` | Bug修复 |
| 热修复分支 | `hotfix/critical-fix` | 紧急修复 |

### 7.2 提交规范

```
feat: 新功能
fix: Bug修复
docs: 文档更新
style: 代码格式（不影响功能）
refactor: 重构
test: 测试相关
chore: 构建/工具相关
```

示例:

```bash
git commit -m "feat: 添加城市搜索工具"
git commit -m "fix: 修复会话超时问题"
git commit -m "docs: 更新API文档"
```

### 7.3 代码审查

1. 创建 Pull Request
2. 描述变更内容
3. 添加截图/演示（如有UI变更）
4. 关联 Issue（如有）
5. 等待 Review
6. 根据反馈修改
7. 合并到主分支

---

## 8. 资源

### 8.1 学习资源

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Next.js 文档](https://nextjs.org/docs)
- [React 文档](https://react.dev/)
- [TypeScript 手册](https://www.typescriptlang.org/docs/)
- [gRPC Python 教程](https://grpc.io/docs/languages/python/)

### 8.2 相关链接

- [项目仓库](https://github.com/your-repo/ShuaiTravelAgent)
- [Issue Tracker](https://github.com/your-repo/ShuaiTravelAgent/issues)
- [Wiki](https://github.com/your-repo/ShuaiTravelAgent/wiki)

---

## 9. 基础设施服务

### 9.1 启动基础设施

**详见**: [基础设施文档](../docs/INFRASTRUCTURE.md)

```bash
# 启动所有服务 (应用 + 基础设施)
docker-compose up -d

# 仅启动基础设施
docker-compose up -d redis milvus-etcd milvus-minio milvus nacos mysql

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 9.2 服务连接配置

| 服务 | 端口 | 配置文件 | 说明 |
|------|------|----------|------|
| Redis | 6379 | `.claude/infrastructure.yaml` | 消息队列、缓存 |
| Milvus | 19530 | `.claude/infrastructure.yaml` | 向量数据库 |
| Nacos | 38848 | `.claude/infrastructure.yaml` | 配置中心 |

---

## 10. 核心组件详解

### 10.1 Agent 模块组件

| 组件 | 文件 | 作用 | 关键类/函数 |
|------|------|------|------------|
| **ReAct 引擎** | `agent/src/core/react_agent.py` | 推理循环核心 | `ReActAgent`, `execute()` |
| **旅游 Agent** | `agent/src/core/travel_agent.py` | 旅游领域逻辑 | `TravelAgent` |
| **LLM 客户端** | `agent/src/llm/client.py` | LLM 调用 | `LLMClient`, `create_client()` |
| **模型管理器** | `agent/src/llm/manager.py` | 模型配置管理 | `ModelManager`, `switch_model()` |
| **工具系统** | `agent/src/core/travel_tools.py` | 工具注册执行 | `_register_tools()` |
| **RAG 检索器** | `agent/src/middleware/milvus_rag.py` | 向量检索 | `MilvusRAGRetriever` |
| **记忆管理** | `agent/src/memory/` | 短期/长期/工作记忆 | `RedisMemoryManager` |
| **gRPC 服务器** | `agent/src/server.py` | 服务端入口 | `serve()` |

### 10.2 Web 模块组件

| 组件 | 文件 | 作用 | 关键函数 |
|------|------|------|----------|
| **FastAPI 应用** | `web/src/main.py` | 应用入口 | `create_app()` |
| **聊天路由** | `web/src/routes/chat.py` | SSE 流式接口 | `/api/chat/stream` |
| **会话路由** | `web/src/routes/session.py` | 会话 CRUD | `/api/sessions` |
| **模型路由** | `web/src/routes/model.py` | 模型列表 | `/api/models` |
| **gRPC 客户端** | `web/src/grpc_client/` | 连接 Agent | `create_channel()` |

### 10.3 Frontend 模块组件

| 组件 | 文件 | 作用 | 状态管理 |
|------|------|------|----------|
| **AppContext** | `frontend/src/context/AppContext.tsx` | 全局状态 | Zustand |
| **API 服务** | `frontend/src/services/api.ts` | HTTP/SSE 客户端 | `apiService` |
| **聊天区域** | `frontend/src/components/ChatArea.tsx` | 主聊天界面 | React State |
| **消息列表** | `frontend/src/components/MessageList.tsx` | 消息气泡 | React State |
| **侧边栏** | `frontend/src/components/Sidebar.tsx` | 会话管理 | AppContext |

### 10.4 基础设施组件

| 组件 | 文件 | 作用 |
|------|------|------|
| **Redis 记忆** | `agent/src/memory/redis_memory.py` | Redis-backed 记忆存储 |
| **Milvus RAG** | `agent/src/middleware/milvus_rag.py` | 向量检索增强 |
| **配置热更新** | `agent/src/infrastructure/config_hot_reload.py` | Nacos 配置中心 |
| **HTTP 客户端** | `agent/src/infrastructure/http_client.py` | HTTP 请求封装 |

---

## 11. Docker 全栈部署

### 11.1 启动全部服务

**详见**: [基础设施文档](../docs/INFRASTRUCTURE.md)

```bash
# 一键启动全部服务
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看应用日志
docker-compose logs -f agent web frontend
```

### 11.2 服务连接配置

| 服务 | 端口 | 配置文件 | 说明 |
|------|------|----------|------|
| Redis | 6379 | `.claude/infrastructure.yaml` | 消息队列、缓存 |
| Milvus | 19530 | `.claude/infrastructure.yaml` | 向量数据库 |
| Nacos | 38848 | `.claude/infrastructure.yaml` | 配置中心 |

### 11.3 使用基础设施

**Redis 记忆管理**:

```python
from memory.redis_memory import RedisMemoryManager

memory = RedisMemoryManager(
    host="localhost",
    port=6379,
    key_prefix="travel:",
    fallback=True  # 自动降级到内存模式
)

memory.add_message(session_id, "user", "Hello")
history = memory.get_conversation_history(session_id)
```

**Milvus RAG 检索器**:

```python
from middleware.milvus_rag import create_milvus_retriever

retriever = await create_milvus_retriever(
    collection_name="travel_documents",
    dim=1024,
    host="localhost",
    port=19530,
    fallback_to_memory=True  # 自动降级到内存模式
)

await retriever.add_documents(documents, source="travel")
results = await retriever.retrieve("北京旅游", top_k=5)
```

**配置热更新**:

```python
from infrastructure.config_hot_reload import get_config_reloader

reloader = await get_config_reloader(
    config_path=".claude/infrastructure.yaml",
    nacos_enabled=True,
    server_addresses=["http://localhost:38848"]
)

# 获取配置
app_name = reloader.get("app.name")

# 监听配置变化
def on_change(key, old, new):
    print(f"配置变化: {key}")

reloader.on_change("app", on_change)
```

### 11.4 测试基础设施

**详见**: [集成测试设计文档](../docs/INTEGRATION_TESTS.md)

```bash
# 运行基础设施测试
pytest tests/test_redis_integration.py -v
pytest tests/test_milvus_integration.py -v
pytest tests/test_nacos_integration.py -v
```

### 11.6 Docker 组件详解

| 组件 | 镜像 | 作用 | 在项目中的用途 |
|------|------|------|----------------|
| **redis** | redis:7-alpine | 内存键值数据库 | 消息队列、会话缓存、对话历史存储 |
| **milvus** | milvusdb/milvus:v2.5.10 | 向量数据库 | RAG 语义检索、文档向量存储 |
| **milvus-etcd** | quay.io/coreos/etcd:v3.5.16 | 分布式键值存储 | Milvus 元数据存储 |
| **milvus-minio** | minio/minio:RELEASE.2023-03-20T20-16-18Z | 对象存储 | Milvus 存储后端 |
| **nacos** | nacos/nacos-server:v2.3.2 | 配置中心 | 配置热更新、配置管理 |
| **mysql** | mysql:8.0-debian | 关系型数据库 | Nacos 数据持久化 |

#### 组件关系图

```
┌─────────────────────────────────────────────────────────┐
│                    应用层 (Agent/Web)                    │
└─────────────────────────┬───────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │  Redis  │    │ Milvus  │    │  Nacos  │
    └────┬────┘    └────┬────┘    └────┬────┘
         │               │               │
         │          ┌────┴────┐         │
         │          │         │         │
         │          ▼         ▼         │
         │    ┌─────────┐ ┌─────────┐   │
         │    │etcd     │ │MinIO    │   │
         │    └─────────┘ └─────────┘   │
         │                              │
         │                          ┌───┴────┐
         │                          │ MySQL  │
         │                          └────────┘
         ▼
    ┌─────────────────────────────────────────┐
    │  对话历史缓存、消息队列、会话状态         │
    └─────────────────────────────────────────┘
```

#### 各组件使用场景

| 场景 | 使用的组件 | 说明 |
|------|-----------|------|
| 存储对话历史 | Redis | 短期记忆，自动过期 |
| 语义搜索旅游知识 | Milvus | RAG 检索增强 |
| 动态调整配置 | Nacos | 无需重启即可更新配置 |
| 异步任务处理 | Redis | 消息队列、背压处理 |
| 配置版本管理 | Nacos | 配置变更历史 |

#### 详见
- 完整组件说明: [基础设施文档](../docs/INFRASTRUCTURE.md#组件详解)

---

### 11.7 相关文档

| 主题 | 文档链接 |
|------|----------|
| 基础设施服务 | [docs/INFRASTRUCTURE.md](../docs/INFRASTRUCTURE.md) |
| 集成测试设计 | [docs/INTEGRATION_TESTS.md](../docs/INTEGRATION_TESTS.md) |
| 系统架构 | [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) |
| API 接口 | [docs/api.md](../docs/api.md) |

---

## 12. 高级基础设施服务 (v0.0.1)

v0.0.1 版本新增了 7 个高级基础设施模块，充分利用 Redis 和 Milvus 提供更强大的功能支持。

### 12.1 新增模块概览

| 模块 | 文件 | 功能 |
|------|------|------|
| **LLM 响应缓存** | `agent/src/infrastructure/llm_cache.py` | Redis ベースの LLM 响应缓存 |
| **API 限流器** | `agent/src/infrastructure/rate_limiter.py` | 多算法限流保护 |
| **用户偏好存储** | `agent/src/infrastructure/user_preference_store.py` | Milvus 向量偏好存储 |
| **实时消息推送** | `agent/src/infrastructure/realtime_pusher.py` | Redis Pub/Sub 推送 |
| **基础设施监控** | `agent/src/infrastructure/monitor.py` | 多服务健康监控 |
| **对话历史存储** | `agent/src/infrastructure/conversation_store.py` | Milvus 对话向量存储 |
| **配置版本管理** | `agent/src/infrastructure/config_version_manager.py` | Redis 版本管理 |

### 12.2 使用示例

**LLM 响应缓存**:

```python
from infrastructure.llm_cache import create_llm_cache, CacheConfig

cache = await create_llm_cache(CacheConfig(ttl=3600))
await cache.set("用户问题", "LLM 回答")
cached = await cache.get("用户问题")
stats = cache.get_stats()
```

**API 限流器**:

```python
from infrastructure.rate_limiter import create_rate_limiter, RateLimitConfig

limiter = await create_rate_limiter(
    RateLimitConfig(max_requests=100, window_seconds=60)
)
result = await limiter.check("user:123")
if result.allowed:
    print("请求允许")
```

**基础设施监控**:

```python
from infrastructure.monitor import create_monitor, ServiceType

monitor = await create_monitor()
health = await monitor.check_all()
for service, status in health.items():
    print(f"{service}: {status.status}")
```

### 12.3 快速开始

```bash
# 1. 安装依赖
pip install aiohttp httpx psutil redis pymilvus aiomysql

# 2. 运行基础设施测试
cd agent
PYTHONPATH=src python -m pytest tests/test_infrastructure_modules.py -v

# 3. 查看测试报告
# 应显示 12/12 tests passed
```

### 12.4 详细文档

详见: [基础设施文档](../docs/INFRASTRUCTURE.md#高级基础设施服务-v210)

---

## 13. 优化功能指南

### 13.1 配置文件分层

项目支持多配置文件分层管理：

| 配置文件 | 说明 |
|---------|------|
| `config/llm_config.yaml` | LLM 模型配置（必选） |
| `config/agent_config.yaml` | Agent 行为配置（可选） |
| `config/infrastructure_config.yaml` | 基础设施配置（可选） |

使用示例：

```python
from config.config_manager import ConfigManager

# 自动加载所有配置文件
config = ConfigManager("config/llm_config.yaml")

# 获取各部分配置
llm_config = config.get_model_config("minimax-m2-5")
agent_config = config.get_agent_config()
infra_config = config.get_infrastructure_config()
```

### 13.2 依赖注入

项目提供简单的依赖注入容器，支持单例和瞬态服务注册：

```python
from di import Container, get_container

# 获取全局容器
container = get_container()

# 注册服务
container.register_singleton(ILLMClient, AnthropicAdapter)

# 解析服务
client = container.resolve(ILLMClient)

# ReActTravelAgent 支持依赖注入
from core.travel_agent import ReActTravelAgent

agent = ReActTravelAgent(
    config_manager=config_manager,
    memory_manager=memory_manager,
    llm_client=llm_client  # 注入自定义客户端
)
```

### 13.3 HTTP 连接池

提供 HTTP 连接池用于请求复用：

```python
from infrastructure.http_pool import get_http_pool

pool = get_http_pool()

# GET 请求（带缓存）
response = pool.get(url, use_cache=True)

# POST 请求
response = pool.post(url, json_data={"key": "value"})
```

### 13.4 运行单元测试

```bash
# 运行 ConfigManager 测试
cd agent
PYTHONPATH=src python -m pytest tests/test_config_manager.py -v

# 运行 LLM Client 测试
PYTHONPATH=src python -m pytest tests/test_llm_client.py -v
```

### 13.5 性能优化建议

1. **启用 LLM 缓存**: 配置 Redis 后自动启用响应缓存
2. **使用连接池**: HTTP 请求自动复用连接
3. **配置分层**: 将不常变化的配置分离，便于热更新
