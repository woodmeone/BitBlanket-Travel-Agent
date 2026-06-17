# BitBlanket-Travel-Agent

![LangGraph](https://img.shields.io/badge/LangGraph-Agent-4B5563)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi)
![Next.js](https://img.shields.io/badge/Next.js-16-111111?logo=next.js)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python)

一个基于 LangGraph 的 AI 旅行助手，核心是自研的 Agent 编排架构——通过状态机驱动多轮工具调用、验证与回退，把旅行建议整理成可操作的结构化结果。

## 预览

![Quick Demo](docs/assets/readme-demo.gif)

**对话与流式执行**

![对话页](docs/assets/readme-home.png)

**城市探索与决策卡片**

![城市探索](docs/assets/readme-city-explorer.png)

**行程工具箱与结果整理**

![行程结果](docs/assets/readme-itinerary-result.png)

## Agent 架构

这是项目的核心部分，基于 LangGraph 实现了一套完整的 Agent 编排系统。

### 图执行流程

```
用户输入 → intent(意图识别) → strategy(策略路由) → plan/react/direct(三种模式)
    → execute(工具执行，可循环) → verify(结果验证) → answer(回答生成) → self_check(自检) → END
```

- **intent**: 意图识别，三层回退（结构化解析 → LLM JSON → 关键词匹配）
- **strategy**: 策略路由，根据意图选择 plan/react/direct 模式，高风险问题强制验证
- **execute**: 工具执行，三重保护防死循环（轮次上限 + 预算控制 + 熔断）
- **verify**: 结果验证，5维度校验（完整性/覆盖度/新鲜度/一致性/风险合规），不通过可重试或降级
- **answer**: 回答生成，根据验证状态决定输出策略

### Runtime 三层架构

```
AgentRuntime (应用层：会话管理、子Agent追踪、执行回执)
    → RuntimeDriver (接口层：Protocol协议，依赖倒置，便于Mock和替换)
        → RuntimeFlow (执行层：LangGraph图执行、事件分发、记忆持久化)
```

- **AgentRuntime**: 入口，构建运行请求、追踪子Agent切换、组装执行回执
- **RuntimeDriver**: Protocol 协议类，纯委托层，延迟导入防循环依赖
- **RuntimeFlow**: 核心执行，通过 `astream_events` 驱动 LangGraph 图，按事件类型分发处理

### Tool → Skill → SubAgent 层级

```
Tool (最小执行单元，如搜索景点、查天气)
    → Skill (能力单元 = Tool + 契约 + 选择策略 + 时效策略 + 降级策略)
        → SubAgent (分组标签，事后归因，追踪哪些工具调用属于哪个逻辑角色)
```

当前采用**事后归因**模式：所有工具调用在同一个图中执行，完成后通过 SubagentRegistry 归因到对应子Agent。这样做的优势是低侵入、渐进演进，未来可平滑迁移到事前分发模式。

### 可靠性机制

| 机制 | 说明 |
|------|------|
| 意图识别三层回退 | 结构化解析 → LLM JSON → 关键词兜底 |
| 执行防死循环 | 轮次上限 + Token预算 + 连续失败熔断 |
| 结果验证 | 5维度校验，不通过可重试或降级 |
| 记忆持久化 | 5层记忆结构（短期/情景/长期/冲突/跨会话），Token预算分配 |
| CheckPointer | LangGraph检查点机制，支持断点续传和时间旅行 |

### 关键设计决策

- **SSE 而非 WebSocket**: 单向流式推送足够，实现简单
- **Protocol 而非 ABC**: 鸭子类型，不需要显式继承，便于Mock
- **事后归因而非事前分发**: 低侵入，渐进演进，Phase-2 当前架构
- **共享上下文而非独立上下文**: Token经济，信息无损，当前阶段够用
- **延迟导入**: RuntimeDriver 延迟导入 RuntimeFlow，避免循环依赖

## 产品能力

- 三种对话模式：direct / react / plan
- SSE 流式输出，实时展示阶段、工具调用、推理过程
- 行程结果结构化：每日行程卡、预算联动、多方案对比、冲突检测
- 城市探索：150+ 城市池，场景筛选，一键生成方案
- 地图路线预览（高德接入）
- 结果导出：图片长图、分享短链

## 技术栈

| 层 | 技术 |
|----|------|
| Agent | LangChain + LangGraph |
| Backend | FastAPI + Python 3.13 |
| Frontend | Next.js 16 + React 19 + TypeScript + antd |
| 模型 | DeepSeek / OpenAI 兼容接口 |

## 项目结构

```text
agent/travel_agent/
├── runtime/          # AgentRuntime + RuntimeDriver，运行时入口
├── graph/            # LangGraph 图构建、节点实现、状态定义、提示词模板
├── supervisor/       # Supervisor 图构建，叠加子Agent元数据
├── subagents/        # 子Agent基类与注册表（搜索/规划/预算/验证）
├── contracts/        # Skill契约、执行回执、事件定义
├── pipelines/        # PlanningPipeline + VerificationPipeline
├── skills/           # Skill注册表
├── tools/            # 工具实现（旅行API、旅行工具）
├── memory/           # 记忆持久化与冲突解决
└── llm/              # LangChain适配器

backend/moyuan_web/
├── routes/           # REST路由（chat/session/artifacts/share/cities/health）
├── services/         # 业务逻辑层，编排Agent调用与数据持久化
├── repositories/     # 数据访问层，SQLite读写
├── config/           # 运行时配置（模型、服务、CORS、限流）
└── main.py           # FastAPI应用入口，lifespan管理

frontend/src/
├── app/              # Next.js App Router，页面路由与布局
├── components/       # UI组件（chat-area / message-list / travel-plan-toolkit / city-explorer）
├── services/api/     # 后端API客户端，按资源分模块
├── context/          # React Context（会话状态、模型选择）
└── lib/              # 工具函数与类型定义

deploy/               # Docker Compose、Dockerfile、数据库迁移
```

## 快速开始

### 环境要求

- Python 3.13+
- Node.js 20+

### 安装与启动

```bash
# 1. 安装依赖
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 2. 配置模型
cp backend/config/llm_config.yaml.example backend/config/llm_config.yaml
# 编辑 llm_config.yaml，填入你的 API key

# 3. 启动后端
python -m uvicorn moyuan_web.main:app --host 0.0.0.0 --port 38000 --app-dir backend --reload

# 4. 启动前端
cd frontend && npm run dev
```

### 访问地址

- Frontend: http://localhost:33001
- API Docs: http://localhost:38000/rapidoc
- Health: http://localhost:38000/api/health

### Docker 启动

```bash
docker compose --file deploy/compose/compose.yaml up --build
```

## 后续方向

- 事前分发模式：SubAgent 拥有独立上下文，真正多智能体协作
- 更多数据源：酒店/门票/交通实时数据
- 路线编辑体验升级
- 城市探索热度与季节排序
