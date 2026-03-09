# System Architecture

## 总体结构

ShuaiTravelAgent 由三层组成：

1. Frontend：Next.js 对话与旅行工具 UI
2. Web API：FastAPI 路由与服务编排层
3. Agent：LangGraph 驱动的意图识别、计划、执行、验证链路

```text
Browser
  -> FastAPI /api/chat/stream (SSE)
    -> ChatService
      -> LangGraph TravelAgent
         -> intent -> strategy -> plan -> execute -> verify -> answer -> self_check
      -> Session / Memory / Checkpoint Storage
```

## 分层职责

### Frontend (`frontend/`)

负责把 Agent 的流式能力变成真正可交互的旅行产品界面。

核心职责：

- 对话输入、约束面板、模式切换
- 流式展示 reasoning / stage / tool event / answer
- 行程结果二次结构化：每日卡片、预算滑杆、对比、冲突检测、导出图片、分享
- 城市探索、候选池、对比池与继续追问入口
- 调用地图预览、分享短链、城市详情等 API

关键文件：

- `frontend/src/app/page.tsx`
- `frontend/src/components/ChatArea.tsx`
- `frontend/src/components/MessageList.tsx`
- `frontend/src/components/TravelPlanToolkit.tsx`
- `frontend/src/components/CityExplorer.tsx`
- `frontend/src/services/api.ts`

### Web API (`web/shuai_web/`)

负责把前端请求组织成稳定的服务入口，并承接会话、城市、分享、健康状态等能力。

核心职责：

- 暴露 `/api/chat/stream` SSE 接口
- 管理 session、model、city、map、share、health 等 REST 接口
- 封装 session 存储、分享存储、城市数据服务
- 汇总工具健康、intent 聚合与可观测性结果

关键文件：

- `web/shuai_web/main.py`
- `web/shuai_web/routes/chat.py`
- `web/shuai_web/routes/session.py`
- `web/shuai_web/routes/city.py`
- `web/shuai_web/routes/health.py`
- `web/shuai_web/services/chat_service.py`

### Agent (`agent/travel_agent/`)

负责真正的推理执行逻辑，把用户问题转成工具调用、验证链路和最终答案。

核心职责：

- 意图识别与策略路由
- 计划生成与步骤校验
- 工具执行、重试、熔断、早停
- stale 检测、刷新与 fallback
- 结果验证、可信度和风险提示
- 会话记忆、摘要、偏好画像与 checkpoint 持久化

关键文件：

- `agent/travel_agent/graph/builder.py`
- `agent/travel_agent/graph/nodes.py`
- `agent/travel_agent/graph/runtime_config.py`
- `agent/travel_agent/graph/memory_integration.py`
- `agent/travel_agent/graph/persistent_checkpointer.py`
- `agent/travel_agent/tools/travel_tools.py`

## 主要请求链路

### 对话链路

```text
用户输入
  -> Frontend 发送 POST /api/chat/stream
  -> ChatService 初始化 / 恢复 session
  -> LangGraph Agent 执行 intent -> strategy -> plan -> execute -> verify -> answer
  -> Web API 将阶段、工具事件、答案片段通过 SSE 回推前端
  -> Frontend 渲染消息 + TravelPlanToolkit
```

### 城市探索链路

```text
用户打开城市探索
  -> Frontend 请求 /api/regions /api/tags /api/cities
  -> CityService 返回城市摘要列表
  -> 用户点击城市详情
  -> Frontend 请求 /api/cities/{city_id}
  -> Frontend 在卡片中继续触发对话生成完整方案
```

### 分享与导出链路

```text
用户在结果区点击导出或分享
  -> 前端导出图片: html2canvas 生成长图
  -> 前端创建分享: POST /api/share-links
  -> 后端持久化分享内容并返回 share_url
```

## SSE 事件协议

前端主要消费这些事件：

- `session_id`
- `reasoning_start`
- `reasoning_chunk`
- `reasoning_end`
- `plan_preview`
- `stage`
- `tool_start`
- `tool_end`
- `answer_start`
- `chunk`
- `metadata`
- `error`
- `done`

其中：

- `plan_preview` 用于展示可审计的计划预览
- `metadata` 用于渲染工具列表、验证状态、stale 数量、fallback 次数等诊断信息
- `stage/tool_*` 用于驱动前端“执行时间线”和“运行诊断”模块

## 持久化与运行数据

默认会落盘以下数据：

- `data/sessions/sessions.json`: 会话与消息
- `data/agent_memory.json`: 摘要、偏好、澄清信息
- `data/langgraph_checkpoints.sqlite3`: LangGraph checkpoint
- `data/runtime_failure_clusters.jsonl`: 失败聚类日志

详细说明见 [data-storage.md](data-storage.md)。

## 当前设计重点

### 1. 从“AI 回答”升级为“可操作结果”

项目前端不满足于直接显示一段 Markdown，而是继续把结果加工成：

- 每日行程卡
- 预算滑杆
- 多方案对比
- 冲突检测与修复
- 导出图片 / 分享
- 城市探索与候选池

### 2. 从“工具调用”升级为“可验证执行”

Agent 层重点在于：

- 计划是否合理
- 工具是否执行成功
- 数据是否过期
- 结论是否经过验证
- 风险是否需要显式提示给用户

### 3. 从“对话系统”升级为“旅行决策系统”

产品目标不是回答一个问题，而是帮助用户完成：

- 目的地选择
- 方案比较
- 预算取舍
- 风险规避
- 最终分享与执行

## 相关文档

- [../reference/api-reference.md](../reference/api-reference.md)
- [../reference/project-structure.md](../reference/project-structure.md)
- [../testing/testing-guide.md](../testing/testing-guide.md)
