# 小帅旅游助手 - 智能AI旅游推荐系统

## 项目概述

基于 **五层架构** (Application → Algorithm → Middleware → Framework → Infrastructure) 设计的智能旅游助手系统，提供城市推荐、景点查询、路线规划等功能。核心采用自定义 **ReAct Agent** 架构，通过节点化工作流实现智能推理。

### 核心特性

- **五层架构设计** - 清晰的层次划分，职责分离
- **节点化工作流** - 6 种节点类型，支持复杂业务流程
- **深度思考展示** - 可折叠的思考过程框，实时展示 AI 推理过程
- **SSE 流式响应** - Token 级别实时输出，用户体验大幅提升
- **MiniMax M2.5 支持** - Anthropic 兼容 API，强大的推理能力
- **多协议 LLM 支持** - OpenAI、Claude、Gemini、Ollama 等
- **RAG 检索增强** - 混合检索策略，上下文理解
- **多会话管理** - 独立对话历史，会话隔离
- **Snowflake ID** - 分布式唯一 ID 生成
- **Prompt 模板管理** - 模板版本控制，动态生成

### Memory v2.2 智能记忆系统

- **AttentionWindow** - 注意力窗口，基于位置/重要性/相关性动态选择关键消息
- **ReflectionMechanism** - 反思机制，从对话中提取关键洞察和用户意图
- **SmartEvictionPolicy** - 智能淘汰，基于多维度决策自动管理记忆容量
- **ConversationVectorizer** - 对话向量化，支持多粒度语义检索
- **MemoryRecirculation** - 记忆回流，阈值/频率/时间触发自动归档
- **ContextAwareRetrieval** - 上下文感知检索，RRF 重排序优化结果

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Next.js 16 + React 19 + TypeScript + Zustand + antd 6 |
| 后端 Web | FastAPI + Python 3.10+ |
| Agent | 自定义 ReAct 引擎 + gRPC |
| 部署 | Docker Compose 全栈编排 |

---

## 系统架构

### 五层架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     1. Application Layer (应用层)                  │
│  TravelApplication - 旅游应用入口，节点化工作流编排                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     2. Algorithm Layer (算法层)                   │
│  StateManager - 状态管理、快照、撤销、追踪                        │
│  NodeExecutor  - 节点执行器，支持 6 种节点类型                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     3. Middleware Layer (中间件层)                 │
│  RAGRetriever - 检索增强生成，混合搜索、文档分块                  │
│  MemorySystem - 记忆系统，短期/长期/工作记忆                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     4. Framework Layer (框架层)                    │
│  ReAct Engine  - 自定义 ReAct 推理引擎                           │
│  Node Types    - 节点类型定义                                    │
│  SSE Streamer  - Server-Sent Events 流式输出                     │
│  Prompt Manager - Prompt 模板管理                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   5. Infrastructure Layer (基础设施层)            │
│  LLM Client    - 多协议 LLM 客户端                               │
│  HTTP Client   - HTTP 客户端，支持同步/异步、重试                 │
│  Snowflake ID  - 分布式唯一 ID 生成器                            │
│  Redis Queue   - Redis 消息队列                                 │
│  Milvus Vector - Milvus 向量数据库                              │
│  Nacos Config  - Nacos 配置中心                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 节点类型

| 节点类型 | 说明 | 使用场景 |
|----------|------|----------|
| `ActionNode` | 动作节点 | 执行具体操作，如工具调用 |
| `AgentNode` | Agent 节点 | 复杂推理，子 Agent 委托 |
| `LoopNode` | 循环节点 | 重复执行直到满足条件 |
| `DecisionNode` | 决策节点 | 条件分支判断 |
| `PreparationNode` | 准备节点 | 数据准备、上下文构建 |
| `PersistenceNode` | 持久化节点 | 数据保存、状态持久化 |

---

## 项目结构

```
ShuaiTravelAgent/
├── agent/                      # AI Agent 模块 (gRPC 服务, 端口 50051)
│   ├── src/
│   │   ├── application/        # 5. 应用层 - 入口和工作流编排
│   │   │   ├── travel_app.py  # 旅游应用入口
│   │   │   └── __init__.py
│   │   ├── framework/         # 4. 框架层 - ReAct 引擎和节点类型
│   │   │   ├── node_types.py  # 节点类型定义
│   │   │   ├── state_manager.py # 状态管理
│   │   │   └── __init__.py
│   │   ├── middleware/         # 3. 中间件层 - RAG 和记忆
│   │   │   ├── rag.py         # RAG 检索增强
│   │   │   └── __init__.py
│   │   ├── core/              # 核心模块
│   │   │   ├── travel_agent.py # ReAct Agent 实现
│   │   │   ├── react_agent.py  # ReAct 引擎核心
│   │   │   ├── travel_tools.py  # 工具工厂
│   │   │   ├── response_generator.py # 响应生成
│   │   │   ├── exceptions.py   # 异常处理
│   │   │   └── __init__.py
│   │   ├── memory/             # 记忆系统
│   │   │   ├── short_term.py  # 短期记忆
│   │   │   ├── long_term.py   # 长期记忆
│   │   │   ├── working.py     # 工作记忆
│   │   │   └── __init__.py
│   │   ├── infrastructure/     # 5. 基础设施层
│   │   │   ├── http_client.py  # HTTP 客户端
│   │   │   ├── snowflake.py   # Snowflake ID
│   │   │   ├── streaming.py   # SSE 流式输出
│   │   │   ├── prompt_manager.py # Prompt 模板
│   │   │   ├── redis_queue.py # Redis 消息队列
│   │   │   ├── milvus_vector.py # Milvus 向量数据库
│   │   │   ├── nacos_client.py # Nacos 配置中心
│   │   │   ├── config_hot_reload.py # 配置热更新
│   │   │   ├── infra_config.py # 基础设施配置
│   │   │   # v0.0.1 新增模块
│   │   │   ├── llm_cache.py # LLM 响应缓存
│   │   │   ├── rate_limiter.py # API 限流器
│   │   │   ├── user_preference_store.py # 用户偏好存储
│   │   │   ├── realtime_pusher.py # 实时消息推送
│   │   │   ├── monitor.py # 基础设施监控
│   │   │   ├── conversation_store.py # 对话历史存储
│   │   │   ├── config_version_manager.py # 配置版本管理
│   │   │   └── __init__.py
│   │   ├── config/             # 配置层
│   │   │   ├── config_manager.py
│   │   │   └── __init__.py
│   │   └── server.py           # gRPC 服务器
│   ├── proto/
│   │   ├── agent.proto         # gRPC 服务定义
│   │   ├── agent_pb2.py        # 生成的消息类型
│   │   └── agent_pb2_grpc.py   # 生成的 gRPC 存根
│
├── web/                        # Web API 模块 (FastAPI, 端口 8000)
│   └── src/
│       ├── main.py             # FastAPI 应用入口
│       ├── routes/             # API 路由
│       │   ├── chat.py         # 流式聊天接口
│       │   ├── session.py      # 会话管理
│       │   ├── model.py        # 模型配置
│       │   ├── city.py         # 城市信息
│       │   └── health.py       # 健康检查
│       ├── services/           # 业务服务
│       │   ├── chat_service.py
│       │   └── session_service.py
│       ├── grpc_client/        # gRPC 客户端
│       ├── dependencies/       # 依赖注入
│       └── config/             # 配置管理
│
├── frontend/                   # Next.js 16 前端
│   └── src/
│       ├── app/                # App Router
│       │   └── page.tsx        # 主页面
│       ├── components/         # React 组件
│       │   ├── ChatArea.tsx    # 聊天区域
│       │   ├── MessageList.tsx # 消息列表
│       │   ├── Sidebar.tsx     # 侧边栏
│       │   └── TaskSteps.tsx   # 思考步骤展示
│       └── stores/             # Zustand 状态管理
│
├── config/                     # 配置文件
│   ├── llm_config.yaml         # 实际配置 (被 git 忽略)
│   └── llm_config.yaml.example # 配置模板
│
├── tests/                      # 测试用例 (项目根目录)
│   ├── test_sse_streaming.py   # SSE 流式传输测试
│   ├── test_e2e_streaming.py   # 端到端集成测试
│   ├── conftest.py             # pytest 配置
│   └── README.md               # 测试说明文档
│
├── agent/tests/                # Agent 模块测试
│   └── test_infrastructure_modules.py  # 基础设施模块测试 (12/12 PASS)
│
├── docs/                       # 文档
│   ├── ARCHITECTURE.md         # 系统架构设计
│   ├── api.md                  # API 接口文档
│   ├── prd.md                  # 产品需求文档 (PRD)
│   ├── db.md                   # 数据库设计文档
│   ├── INFRASTRUCTURE.md       # 基础设施服务文档 (v0.0.1)
│   ├── INTEGRATION_TESTS.md    # 集成测试设计文档 (v0.0.1)
│   └── DEVELOP.md              # 开发指南
│
├── run_api.py                  # Web API 启动脚本
├── run_agent.py                # Agent 启动脚本
└── requirements.txt            # Python 依赖
```

---

## 快速开始

### 前置条件

- Python 3.10+
- Node.js 18+
- npm 9+

### 安装依赖

**后端依赖**：

```bash
pip install -r requirements.txt
```

**前端依赖**：

```bash
cd frontend
npm install
```

### 配置

1. 复制配置模板：

```bash
cp config/llm_config.yaml.example config/llm_config.yaml
```

2. 编辑配置文件，填入你的 API Key：

```bash
vim config/llm_config.yaml
```

### 启动服务

| 服务 | 命令 | 端口 |
|------|------|------|
| Agent | `python run_agent.py` | 50051 |
| Web API | `python run_api.py` | 48081 |
| Frontend | `cd frontend && npm run dev` | 43001 |

### 访问应用

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | http://localhost:43001 | Next.js 16 主应用 |
| Swagger API 文档 | http://localhost:48081/docs | Swagger UI (OpenAPI) |
| RapiDoc API 文档 | http://localhost:48081/rapidoc | RapiDoc (美观 UI) |
| ReDoc API 文档 | http://localhost:48081/redoc | ReDoc (文档风格) |

---

## 组件说明

### Agent 模块 (agent/)

| 组件 | 文件路径 | 作用 |
|------|----------|------|
| **ReAct 引擎** | `agent/src/core/react_agent.py` | 自定义 ReAct 推理引擎，实现思考-行动-观察-评估循环 |
| **旅游 Agent** | `agent/src/core/travel_agent.py` | 旅游领域专用 Agent，集成意图识别和工具匹配 |
| **LLM 客户端** | `agent/src/llm/client.py` | 多协议 LLM 客户端，支持 OpenAI/Claude/Gemini/Ollama |
| **模型管理器** | `agent/src/llm/manager.py` | 统一管理模型配置，支持动态切换 |
| **工具系统** | `agent/src/core/travel_tools.py` | 旅游工具注册和调用（城市、景点、天气等） |
| **RAG 检索器** | `agent/src/middleware/milvus_rag.py` | 向量检索增强，支持混合检索和内存降级 |
| **记忆系统** | `agent/src/memory/` | 短期/长期/工作记忆管理 |
| **配置管理** | `agent/src/config/config_manager.py` | 多配置文件分层加载和验证 |
| **依赖注入** | `agent/src/di/__init__.py` | 依赖注入容器，支持单例/瞬态服务 |
| **HTTP 连接池** | `agent/src/infrastructure/http_pool.py` | HTTP 连接复用和请求缓存 |
| **LLM 缓存** | `agent/src/infrastructure/llm_cache.py` | LLM 响应缓存（Redis） |
| **gRPC 服务器** | `agent/src/server.py` | gRPC 服务端，提供 ProcessMessage/StreamMessage 接口 |

### Web 模块 (web/)

| 组件 | 文件路径 | 作用 |
|------|----------|------|
| **FastAPI 应用** | `web/src/main.py` | FastAPI 应用入口，路由注册 |
| **聊天路由** | `web/src/routes/chat.py` | SSE 流式聊天接口 `/api/chat/stream` |
| **会话路由** | `web/src/routes/session.py` | 会话管理接口（创建/删除/列表） |
| **模型路由** | `web/src/routes/model.py` | 模型列表和配置接口 |
| **gRPC 客户端** | `web/src/grpc_client/` | 连接 Agent gRPC 服务的客户端 |
| **业务服务** | `web/src/services/` | 聊天服务和会话服务的业务逻辑 |

### Frontend 模块 (frontend/)

| 组件 | 文件路径 | 作用 |
|------|----------|------|
| **App 状态** | `frontend/src/context/AppContext.tsx` | 全局状态管理（会话、模型、消息） |
| **API 服务** | `frontend/src/services/api.ts` | HTTP 和 SSE 客户端封装 |
| **聊天区域** | `frontend/src/components/ChatArea.tsx` | 聊天主界面，消息展示和输入 |
| **消息列表** | `frontend/src/components/MessageList.tsx` | 消息气泡，思考过程展示 |
| **侧边栏** | `frontend/src/components/Sidebar.tsx` | 会话列表管理 |
| **思考步骤** | `frontend/src/components/TaskSteps.tsx` | AI 推理过程展示组件 |

---

## Docker 全栈部署

### 前置条件

- Docker 24+
- Docker Compose V2
- 8GB+ 可用内存

### 一键启动

```bash
# 构建并启动全部服务 (应用 + 基础设施)
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看应用日志
docker-compose logs -f agent web frontend

# 停止所有服务
docker-compose down
```

### Docker 服务架构

```
┌───────────────────────────────────────────────────────────────┐
│                     docker-compose.yml                         │
│                                                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │  Frontend   │→│   Web API   │→│   Agent     │           │
│  │  :43001     │  │  :48081     │  │  :50051     │           │
│  │  Next.js    │  │  FastAPI    │  │  gRPC       │           │
│  └─────────────┘  └─────────────┘  └──────┬──────┘           │
│                                            │                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐   ┌──────────┐    │
│  │  Redis   │  │  Milvus  │  │  Nacos   │   │  MySQL   │    │
│  │  :6379   │  │  :19530  │  │  :38848  │   │  :3306   │    │
│  └──────────┘  └──────────┘  └──────────┘   └──────────┘    │
└───────────────────────────────────────────────────────────────┘
```

### 多阶段 Dockerfile

| 服务 | Dockerfile | 基础镜像 | 构建策略 |
|------|-----------|----------|----------|
| Agent | `agent/Dockerfile` | python:3.10-slim | 二阶段 (builder + runner) |
| Web | `web/Dockerfile` | python:3.10-slim | 二阶段 (builder + runner) |
| Frontend | `frontend/Dockerfile` | node:20-alpine | 三阶段 (deps + builder + runner, standalone) |

### 仅启动基础设施

```bash
docker-compose up -d redis milvus-etcd milvus-minio milvus nacos mysql
```

---

## Docker 快速开始

### 前置条件

- Docker 24+
- Docker Compose V2
- 8GB+ 可用内存

### 一键启动所有服务

```bash
# 1. 启动基础设施 (Redis, Milvus, Nacos, MinIO, MySQL)
docker-compose up -d

# 2. 验证服务状态
docker-compose ps

# 3. 启动 Agent gRPC 服务
python run_agent.py

# 4. 启动 Web API 服务 (新终端)
python run_api.py

# 5. 启动前端开发服务器
cd frontend && npm run dev
```

### 单独启动基础设施服务

```bash
# Redis (消息队列/缓存)
docker run -d --name redis \
  -p 6379:6379 \
  -v redis_data:/data \
  redis:7-alpine redis-server --appendonly yes --maxmemory 256mb

# Milvus (向量数据库)
docker run -d --name milvus-etcd \
  -p 2379:2379 \
  quay.io/coreos/etcd:v3.5.16

docker run -d --name milvus-minio \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /minio_data --console-address ":9001"

docker run -d --name milvus \
  -p 19530:19530 -p 9091:9091 \
  -v milvus_data:/var/lib/milvus \
  milvusdb/milvus:v2.5.10

# Nacos (配置中心)
docker run -d --name nacos \
  -p 38848:8848 -p 39848:9848 \
  -v nacos_data:/home/nacos/data \
  nacos/nacos-server:v2.3.2
```

### 验证服务状态

```bash
# Redis
redis-cli -h localhost -p 6379 ping
# 期望: PONG

# Milvus
curl -s http://localhost:9091/healthz
# 期望: OK

# Nacos
curl -s http://localhost:38848/nacos/v1/ns/service/list
# 期望: success

# MinIO
curl -s http://localhost:9000/minio/health/live
# 期望: ok
```

### 服务端口汇总

| 服务 | 端口 | Docker 端口 | 作用 |
|------|------|------------|------|
| Frontend | 43001 | - | Next.js 前端 |
| Web API | 48081 | - | FastAPI 后端 |
| Agent gRPC | 50051 | - | Agent gRPC 服务 |
| Redis | 6379 | 6379 | 消息队列/缓存 |
| Milvus | 19530 | 19530 | 向量数据库 |
| Milvus HTTP | 9091 | 9091 | 健康检查 |
| Nacos HTTP | 38848 | 38848 | 配置中心 |
| Nacos gRPC | 39848 | 39848 | 服务通信 |
| MinIO API | 9000 | 9000 | 对象存储 |
| MinIO Console | 9001 | 9001 | 控制台 |
| MySQL | 3306 | 3306 | Nacos 数据库 |

### 停止服务

```bash
# 停止基础设施
docker-compose down

# 停止并删除数据卷 (慎用！)
docker-compose down -v
```

---

## API 接口文档

### 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/ready` | 就绪检查 |
| GET | `/api/live` | 存活检查 |

**响应示例**：

```json
{
  "status": "healthy",
  "version": "0.0.1",
  "agent": "connected",
  "services": {
    "api": "healthy",
    "database": "healthy",
    "agent": "healthy"
  }
}
```

### 流式聊天

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat/stream` | SSE 流式聊天 |

**请求参数**：

```json
{
  "message": "云南丽江旅游攻略",
  "session_id": "user-session-001"
}
```

**响应格式** (SSE)：

```
data: {"type": "session_id", "session_id": "user-session-001"}

data: {"type": "reasoning_start"}

data: {"type": "reasoning_chunk", "content": "[已思考 0.5秒]\n\n分析用户需求..."}

data: {"type": "reasoning_end"}

data: {"type": "answer_start"}

data: {"type": "chunk", "content": "云南"}

data: {"type": "chunk", "content": "丽江"}

data: {"type": "chunk", "content": "是"}

...

data: {"type": "done", "stats": {"tokens": 482, "duration": 17.087}}
```

### 会话管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/session/new` | 创建新会话 |
| GET | `/api/sessions` | 列出所有会话 |
| DELETE | `/api/session/{session_id}` | 删除会话 |
| PUT | `/api/session/{session_id}/name` | 更新会话名称 |
| PUT | `/api/session/{session_id}/model` | 设置会话模型 |
| GET | `/api/session/{session_id}/model` | 获取会话模型 |
| POST | `/api/clear/{session_id}` | 清除聊天记录 |

### 模型管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/models` | 列出可用模型 |
| GET | `/api/models/{model_id}` | 获取模型详情 |

### 城市信息

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/cities` | 列出城市（支持过滤） |
| GET | `/api/cities/{city_id}` | 获取城市详情 |
| GET | `/api/cities/{city_id}/attractions` | 获取城市景点 |
| GET | `/api/regions` | 列出地区 |
| GET | `/api/tags` | 列出标签 |

---

## SSE 流式接口

### SSE 事件类型

| 事件类型 | 说明 | 数据结构 |
|----------|------|----------|
| `session_id` | 会话标识 | `{"type": "session_id", "session_id": "..."}` |
| `reasoning_start` | 思考过程开始 | `{"type": "reasoning_start"}` |
| `reasoning_chunk` | 思考内容片段 | `{"type": "reasoning_chunk", "content": "..."}` |
| `reasoning_end` | 思考过程结束 | `{"type": "reasoning_end"}` |
| `answer_start` | 答案开始生成 | `{"type": "answer_start"}` |
| `chunk` | 答案内容片段 | `{"type": "chunk", "content": "..."}` |
| `error` | 错误信息 | `{"type": "error", "content": "..."}` |
| `heartbeat` | 心跳保活 | `{"type": "heartbeat", "timestamp": "..."}` |
| `done` | 传输完成 | `{"type": "done", "stats": {...}}` |

### 前端集成示例

```typescript
import { useState, useCallback } from 'react';

interface SSEEvent {
  type: string;
  content?: string;
  session_id?: string;
  stats?: { tokens: number; duration: number };
}

export function useChatStream() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const sendMessage = useCallback(async (message: string, sessionId?: string) => {
    setIsStreaming(true);
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId }),
    });

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) return;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const text = decoder.decode(value);
      const lines = text.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event: SSEEvent = JSON.parse(line.slice(6));

            switch (event.type) {
              case 'chunk':
                // 更新消息内容
                setMessages(prev => {
                  const last = prev[prev.length - 1];
                  if (last?.role === 'assistant') {
                    return [...prev.slice(0, -1), {
                      ...last,
                      content: last.content + (event.content || '')
                    }];
                  }
                  return [...prev, { role: 'assistant', content: event.content || '' }];
                });
                break;

              case 'done':
                setIsStreaming(false);
                console.log('完成:', event.stats);
                break;
            }
          } catch (e) {
            // 忽略解析错误
          }
        }
      }
    }
  }, []);

  return { sendMessage, isStreaming, messages };
}
```

---

## Proto 文件编译

### 编译命令

修改 `agent/proto/agent.proto` 后，需要重新编译生成 Python 代码：

```bash
cd d:\projects\shuai\ShuaiTravelAgent

# 一键编译到所有位置
python -m grpc_tools.protoc -I./agent/proto --python_out=./agent/proto --grpc_python_out=./agent/proto agent/proto/*.proto
python -m grpc_tools.protoc -I./agent/proto --python_out=./agent/src --grpc_python_out=./agent/src agent/proto/*.proto
python -m grpc_tools.protoc -I./agent/proto --python_out=./web/src --grpc_python_out=./web/src agent/proto/*.proto
```

详细说明请参阅 [agent/proto/README.md](agent/proto/README.md)

---

## gRPC 服务定义

### 服务接口

```protobuf
service AgentService {
  // 处理用户消息
  rpc ProcessMessage (MessageRequest) returns (MessageResponse);

  // 流式处理用户消息
  rpc StreamMessage (MessageRequest) returns (stream StreamChunk);

  // 健康检查
  rpc HealthCheck (HealthRequest) returns (HealthResponse);
}
```

### 消息类型

```protobuf
message MessageRequest {
  string session_id = 1;
  string user_input = 2;
  string model_id = 3;
  bool stream = 4;
}

message MessageResponse {
  bool success = 1;
  string answer = 2;
  ReasoningInfo reasoning = 3;
  string error = 4;
  repeated HistoryStep history = 5;
}

message StreamChunk {
  string chunk_type = 1;  // "thinking_start", "thinking_chunk", "thinking_end", "answer_start", "answer", "done", "error"
  string content = 2;
  bool is_last = 3;
}
```

---

## 配置说明

### 配置文件

```
config/
├── llm_config.yaml              # LLM 模型配置
├── llm_config.yaml.example     # 配置模板
├── agent_config.yaml            # Agent 行为配置
└── infrastructure_config.yaml   # 基础设施配置
```

**配置文件分层说明**:
- `llm_config.yaml` - LLM 模型配置（必选）
- `agent_config.yaml` - Agent 行为配置（可选）
- `infrastructure_config.yaml` - 基础设施配置（可选）

### 支持的 Provider

| provider | 说明 |
|----------|------|
| `openai` | OpenAI GPT 系列 |
| `anthropic` | Anthropic Claude 系列 |
| `google` | Google Gemini 系列 |
| `ollama` | Ollama 本地模型 |
| `openai-compatible` | 兼容 OpenAI API 的自定义服务 |

### 配置示例

```yaml
# 默认使用的模型ID
default_model: minimax-m2-5

# 模型配置列表
models:
  minimax-m2-5:
    name: "MiniMax M2.5"
    provider: anthropic
    model: "MiniMax-M2.5"
    api_base: "https://api.minimaxi.com/anthropic"
    api_key: "sk-xxx"
    temperature: 0.7
    max_tokens: 4096
    timeout: 60
    max_retries: 3

  gpt-4o-mini:
    name: "GPT-4o Mini"
    provider: openai
    model: "gpt-4o-mini"
    api_base: "https://api.openai.com/v1"
    api_key: "sk-xxx"
    temperature: 0.7
    max_tokens: 2000
    timeout: 30
    max_retries: 3

  claude-3-5-sonnet:
    name: "Claude 3.5 Sonnet"
    provider: anthropic
    model: "claude-sonnet-4-20250514"
    api_base: "https://api.anthropic.com/v1"
    api_key: "sk-ant-xxx"
    api_version: "2023-06-01"
    temperature: 0.7
    max_tokens: 2000
    timeout: 60
    max_retries: 3

  ollama-llama3:
    name: "Llama 3 (Ollama)"
    provider: openai-compatible
    model: "llama3"
    api_base: "http://localhost:11434/v1"
    api_key: ""
    temperature: 0.7
    max_tokens: 2000
    timeout: 120
    max_retries: 2

# Agent 配置
agent:
  name: "TravelAssistantAgent"
  max_steps: 10
  max_reasoning_depth: 5
  max_working_memory: 10
  max_long_term_memory: 50

# Web 服务配置
web:
  host: "0.0.0.0"
  port: 48081
  debug: true

# gRPC 服务配置
grpc:
  host: "0.0.0.0"
  port: 50051
```

---

## 测试

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_sse_streaming.py -v

# 运行特定测试类
pytest tests/test_sse_streaming.py::TestSSEStreaming -v

# 运行特定测试方法
pytest tests/test_sse_streaming.py::TestSSEStreaming::test_token_streaming -v

# 生成测试报告
pytest tests/ --html=report.html
```

### 测试要求

- Web API 服务器运行在端口 48081
- gRPC 服务器运行在端口 50051
- Python 3.10+
- pytest-asyncio
- httpx

### 测试文件说明

| 文件 | 说明 |
|------|------|
| `tests/test_sse_streaming.py` | SSE 流式传输核心测试用例 |
| `tests/test_e2e_streaming.py` | 端到端集成测试和性能测试 |
| `tests/conftest.py` | Pytest 配置和共享 fixtures |
| `tests/README.md` | 测试详细说明文档 |
| `agent/tests/test_infrastructure_modules.py` | 基础设施模块测试 (12/12 PASS) |

### 运行基础设施模块测试

```bash
# 切换到虚拟环境
source venv/bin/activate

# 运行基础设施测试
PYTHONPATH=agent/src python3 agent/tests/test_infrastructure_modules.py
```

---

## 文档

项目包含两套文档体系：

### 设计文档 (docs/)

详细的技术设计文档，包含产品需求、API 接口、数据库设计、架构设计和基础设施服务。

| 文档 | 说明 | 重点内容 |
|------|------|----------|
| [prd.md](docs/prd.md) | 产品需求文档 | 功能需求、用户场景、版本规划 |
| [api.md](docs/api.md) | API 接口文档 | REST API 定义、SSE 事件、请求响应格式 |
| [db.md](docs/db.md) | 数据库设计文档 | 数据模型、会话存储方案 |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 系统架构设计 | 五层架构、组件关系、Docker 部署 |
| [INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md) | 基础设施服务 | Docker Compose、Redis/Milvus/Nacos、配置管理 |
| [INTEGRATION_TESTS.md](docs/INTEGRATION_TESTS.md) | 集成测试设计 | 测试策略、用例设计、CI/CD |

### 学习文档 (learn_docs/)

面向开发者的学习资料，按顺序阅读可快速掌握系统核心机制。

| 顺序 | 文档 | 重点内容 |
|------|------|----------|
| 1 | [01_系统架构](learn_docs/01_ARCHITECTURE.md) | 三层微服务架构、技术选型、Docker 容器化 |
| 2 | [02_ReAct代理](learn_docs/02_REACT_AGENT.md) | ReAct 推理循环、状态机、工具系统 |
| 3 | [03_多模式对话](learn_docs/03_MULTI_MODE_CHAT.md) | Direct/ReAct/Plan 三种模式 |
| 4 | [04_接口文档](learn_docs/04_API.md) | HTTP API 接口定义 |
| 5 | [05_开发指南](learn_docs/05_DEVELOP.md) | 开发环境、调试技巧、基础设施使用 |
| 6 | [06_部署指南](learn_docs/06_DEPLOY.md) | Docker 部署、Nginx 配置、云服务部署 |
| 7 | [07_API文档配置](learn_docs/07_RapiDoc_ReDoc.md) | RapiDoc + ReDoc 文档方案 |

### 推荐阅读路径

```
新手入门
    │
    ├── 1. 阅读 01_系统架构
    │      了解系统由哪些模块组成
    │      理解三层架构（Frontend → Web → Agent）
    │
    ├── 2. 阅读 02_ReAct代理
    │      理解 Agent 如何思考和执行
    │      了解工具如何被调用
    │
    └── 3. 阅读 03_多模式对话
           理解三种对话模式的区别
           知道何时使用哪种模式
                  │
                  ▼
            开始开发
                  │
                  ├── 需要 API 详情 → 04_接口文档
                  ├── 本地调试 → 05_开发指南
                  ├── 部署上线 → 06_部署指南
                  └── 接口测试 → 07_API文档配置
```

---

## 更新日志

### v0.0.3 (2026-02-16)

**Memory v2.2 增强版本**

#### 新增组件

**注意力窗口**:
- [memory/attention.py](agent/src/memory/attention.py) - AttentionWindow
- 基于位置/重要性/相关性三维度计算注意力分数
- Softmax 归一化，支持关键词匹配

**反思机制**:
- [memory/reflection.py](agent/src/memory/reflection.py) - ReflectionMechanism
- 从对话中提取关键洞察和用户意图
- 支持 LLM 反思和规则反思两种模式

**智能淘汰策略**:
- [memory/eviction_policy.py](agent/src/memory/eviction_policy.py) - SmartEvictionPolicy
- 基于重要性/时间衰减/访问频率的多维度决策
- AdaptiveEvictionPolicy 支持自适应权重调整

**对话向量化**:
- [memory/vectorizer.py](agent/src/memory/vectorizer.py) - ConversationVectorizer
- 多粒度向量化（摘要/关键事实/用户偏好）
- 支持 TF-IDF 回退和 LLM 嵌入

**记忆回流**:
- [memory/recirculation.py](agent/src/memory/recirculation.py) - MemoryRecirculation
- 阈值/频率/时间/手动四种触发条件
- 自动更新用户画像和长期存储

**上下文感知检索**:
- [memory/retrieval.py](agent/src/memory/retrieval.py) - ContextAwareRetrieval
- 多路检索（语义/画像/时间）
- RRF 重排序优化结果

#### MemoryOrchestrator 增强

- 集成所有 6 个新组件
- 新增 14 个配置选项
- 与 TravelAgent 深度集成

#### 测试覆盖

- 76 个单元测试 + 集成测试全部通过
- 覆盖所有 Memory v2.2 组件

### v0.0.2 (2026-02-16)

**Docker 全栈容器化版本**

- Docker Compose 全栈编排 (Agent + Web + Frontend + 基础设施)
- 多阶段 Dockerfile 构建优化 (Agent, Web, Frontend)
- Next.js standalone 模式部署
- 五层架构重构完成
- MiniMax M2.5 模型集成
- 长短期记忆优化模块
- 全量集成测试验证

### v0.0.1 (2026-02-04)

**基础设施功能增强版本**

#### 新增基础设施模块

**LLM 响应缓存**:
- [infrastructure/llm_cache.py](agent/src/infrastructure/llm_cache.py) - LLM 响应语义缓存
- 基于 Redis 的智能缓存，减少重复 LLM 调用
- 支持 TTL 过期、缓存命中统计

**API 限流**:
- [infrastructure/rate_limiter.py](agent/src/infrastructure/rate_limiter.py) - 分布式限流
- 滑动窗口、令牌桶、固定窗口多种算法
- 精细化的端点限流配置

**用户偏好向量存储**:
- [infrastructure/user_preference_store.py](agent/src/infrastructure/user_preference_store.py) - 个性化推荐
- 基于 Milvus 的用户偏好向量化
- 相似用户查找、个性化目的地推荐

**实时消息推送**:
- [infrastructure/realtime_pusher.py](agent/src/infrastructure/realtime_pusher.py) - WebSocket 推送
- Redis Pub/Sub 实时通知
- 价格提醒、天气预警、旅行更新推送

**基础设施监控**:
- [infrastructure/monitor.py](agent/src/infrastructure/monitor.py) - 健康监控
- Redis/Milvus/Nacos/MinIO/MySQL 统一监控
- 响应时间、QPS、内存使用统计

**对话历史向量化**:
- [infrastructure/conversation_store.py](agent/src/infrastructure/conversation_store.py) - 对话检索
- 对话历史语义存储和检索
- 相似对话搜索、上下文增强

**配置版本管理**:
- [infrastructure/config_version_manager.py](agent/src/infrastructure/config_version_manager.py) - 配置回滚
- 配置变更历史记录
- 版本对比、一键回滚

#### 测试脚本

```bash
# 运行基础设施模块测试
PYTHONPATH=agent/src python3 agent/tests/test_infrastructure_modules.py
```

#### 相关文档

| 主题 | 文档链接 |
|------|----------|
| 基础设施 | [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md) |
| 架构设计 | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| 集成测试 | [docs/INTEGRATION_TESTS.md](docs/INTEGRATION_TESTS.md) |
| 开发指南 | [learn_docs/05_DEVELOP.md](learn_docs/05_DEVELOP.md) |
| 部署指南 | [learn_docs/06_DEPLOY.md](learn_docs/06_DEPLOY.md) |

---

## 版本历史

| 版本 | 日期 | 主要更新 |
|------|------|----------|
| **2.7.4** | 2026-02-17 | 测试覆盖完善，新增316个测试用例 |
| **2.7.0** | 2026-02-17 | 测试增强，文档完善 |
| **2.6.0** | 2026-02-04 | 生产级增强：Sandbox、CircuitBreaker、Monitor |
| **2.5.0** | 2026-02-04 | 智能编排：AdaptiveWorkflow、Evaluator、FeedbackLoop |
| **2.4.0** | 2026-02-04 | 多Agent框架：Orchestrator、MessageBus、AgentFactory |
| **2.3.0** | 2026-02-04 | 工作流引擎、扩展工具、状态管理 |
| **2.2.0** | 2026-02-04 | 智能记忆系统：Attention、Reflection、Eviction |
| **2.0.0** | 2025-02-04 | 基础设施集成：Redis、Milvus、Nacos |

详细更新日志请查看 [CHANGELOG.md](CHANGELOG.md)

---

## 许可证

MIT License
