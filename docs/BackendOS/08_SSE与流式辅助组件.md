# 08 SSE 与流式辅助组件

> **一句话定位**：流式辅助组件负责 SSE 事件序列化、流终结收尾、诊断信息构建、计划预览编排和产物合并，将 StreamMixin 中的复杂子流程拆分为独立可测试的协作组件。

---

## 1. 核心类/方法

### sse_serializer.py — SSE 信封序列化

| 行号 | 类/方法 | 说明 |
|------|---------|------|
| L18 | `class ChatStreamSSESerializer` | SSE 信封序列化器 |
| L22 | `serialize_payload()` | 单个载荷序列化 |
| L27 | `serialize_payloads()` | 批量载荷序列化 |
| L32 | ⭐ `sse()` | 校验载荷 + 格式化为 `data: {JSON}\n\n` |

### stream_finalizer.py — 流终结器

| 行号 | 类/方法 | 说明 |
|------|---------|------|
| L21 | `class ChatStreamFinalizer` | 流终结器 |
| L42 | ⭐ `finalize_success()` | 持久化成功结果 + 构建终端事件（metadata + done） |
| L64 | `finalize_failure()` | 持久化失败状态 + 构建终端事件（error + done） |
| L91 | `_finalize_stream_state()` | 补全派生状态（去重工具列表、计算降级步骤） |
| L107 | ⭐ `_persist_successful_stream()` | 保存助手消息 + 写入记忆 + 补写用户记忆 |
| L133 | `_emit_success_stream_telemetry()` | 发送成功遥测和结构化日志 |
| L163 | ⭐ `_build_success_terminal_payloads()` | 构建 metadata + done 事件 |
| L196 | `_persist_failed_stream()` | 保存中断消息（标记 [INTERRUPTED]） |
| L249 | `_build_failure_terminal_payloads()` | 构建 error + done 事件 |

### stream_diagnostics.py — 诊断信息构建器

| 行号 | 类/方法 | 说明 |
|------|---------|------|
| L17 | `class ChatStreamDiagnostics` | 诊断信息构建器 |
| L21 | `public_artifact_contract()` | 产物规范化为公共合约格式 |
| L33 | `public_execution_receipt_contract()` | 执行回执规范化 |
| L44 | `build_success_diagnostics()` | 构建成功运行的完整诊断信息 |
| L65 | `build_failure_diagnostics()` | 构建中断运行的诊断信息 |

### plan_preview_coordinator.py — plan 模式预览协调器

| 行号 | 类/方法 | 说明 |
|------|---------|------|
| L35 | `_PlanPreviewState` (Protocol) | 预览所需的最小状态合约 |
| L47 | `class ChatPlanPreviewCoordinator` | plan 模式预览协调器 |
| L68 | ⭐ `normalize()` | 编排预览生成和事件推送的完整流程 |
| L102 | `_build_intro_payloads()` | 推送初始推理提示 |
| L108 | `_load_plan_preview()` | 在工作线程中生成计划预览 |
| L120 | `_merge_preview_artifacts()` | 合并预览产物到累积状态 |
| L132 | `_build_subagent_start_payloads()` | 构建子 Agent 启动事件 |
| L159 | `_build_preview_payload()` | 构建公共计划预览载荷 |
| L176 | `_build_subagent_completion_payloads()` | 构建子 Agent 完成事件 |
| L208 | `_build_summary_payload()` | 构建推理摘要 |

### shared.py — 共享工具函数

| 行号 | 函数 | 说明 |
|------|------|------|
| L12 | ⭐ `merge_artifact_payload()` | 深度合并产物片段（递归合并字典，非字典值覆盖） |

### api/events/chat_stream.py — SSE 事件类型体系

| 行号 | 类/常量 | 说明 |
|------|---------|------|
| L27 | `_ChatStreamEventBase` | 所有 SSE 事件的公共基类（extra="forbid"） |
| L36 | `SessionIdEvent` | 会话标识事件 |
| L44 | `ReasoningStartEvent` | 推理开始事件 |
| L50 | `ReasoningChunkEvent` | 推理增量事件 |
| L57 | `ReasoningEndEvent` | 推理结束事件 |
| L63 | `AnswerStartEvent` | 回答开始事件 |
| L69 | `StageEvent` | 阶段转换事件 |
| L83 | `PlanPreviewEvent` | 计划预览事件 |
| L119 | `SubagentStartEvent` | 子代理开始事件 |
| L135 | `SubagentEndEvent` | 子代理结束事件 |
| L145 | `ArtifactPatchEvent` | 产物增量补丁事件 |
| L163 | `ToolStartEvent` | 工具执行开始事件 |
| L171 | `ToolEndEvent` | 工具执行结束事件 |
| L180 | `ChunkEvent` | 回答增量事件 |
| L187 | `MetadataEvent` | 元数据事件（流结束时） |
| L223 | `ErrorEvent` | 错误事件 |
| L231 | `DoneEvent` | 完成事件 |
| L252 | ⭐ `ChatStreamEvent` | Discriminated Union（通过 type 字段判别） |
| L274 | `CHAT_STREAM_EVENT_TYPES` | 16 种事件类型元组 |
| L296 | ⭐ `validate_chat_stream_payload()` | 校验并标准化 SSE 载荷 |

### api/schemas/chat.py — 聊天请求模型

| 行号 | 类/类型 | 说明 |
|------|---------|------|
| L23 | `ChatMode` | 三种模式枚举：Literal["direct", "react", "plan"] |
| L26 | `ChatRequest` | 聊天请求体（message/display_message/session_id/mode） |

---

## 2. 跳过的内容

| 可跳过项 | 行号 | 原因 |
|----------|------|------|
| `sse_serializer.py` L22-29 | L22-29 | `serialize_payload/payloads` 简单委托方法 |
| `stream_finalizer.py` L91-106 | L91-106 | `_finalize_stream_state` 逐字段补全，逻辑直观 |
| `stream_finalizer.py` L218-247 | L218-247 | `_emit_failed_stream_telemetry` 与成功遥测对称 |
| `plan_preview_coordinator.py` L50-66 | L50-66 | 构造函数，纯赋值 |
| `chat_stream.py` 各事件类的 field_validator | 散布各处 | 产物规范化校验器，理解目的即可 |
| `chat_stream.py` L320-335 | L320-335 | `__all__` 导出列表 |
| `chat.py` L43-51 | L43-51 | `_empty_string_to_none` 空白字段转 None，简单校验 |

---

## 3. 核心流程总结

### 3.1 SSE 事件序列化流程

```
Agent 运行时事件 (dict)
    │
    ▼
_normalize_runtime_event()          ← StreamMixin: 规范化为公共事件
    │
    ▼
ChatStreamSSESerializer.sse()       ← 序列化器
    │
    ├─ 1. get_request_context()      ← 获取 request_id / trace_id
    │
    ├─ 2. validate_chat_stream_payload()
    │      ├─ 补充 request_id / trace_id
    │      ├─ TypeAdapter.validate_python()   ← 根据 type 字段自动选择事件模型
    │      └─ model_dump(exclude_none=True)   ← 排除 None 值减小体积
    │
    ├─ 3. record_sse_event()         ← 记录事件类型用于可观测性统计
    │
    └─ 4. return "data: {JSON}\n\n"  ← SSE 标准格式
```

### 3.2 流终结器流程

```
流式传输结束
    │
    ├─ [成功] finalize_success()
    │      │
    │      ├─ 1. _finalize_stream_state()       ← 补全派生状态
    │      │      ├─ 去重 tools_used
    │      │      ├─ 统计 fallback_steps / stale_result_count
    │      │      └─ 推断 verification_passed
    │      │
    │      ├─ 2. build_success_diagnostics()     ← 构建诊断信息
    │      │
    │      ├─ 3. _persist_successful_stream()    ← 持久化
    │      │      ├─ save_message("assistant", answer, reasoning, diagnostics)
    │      │      ├─ _write_memory_assistant()
    │      │      └─ [补写] _write_memory_user() (如果之前未写入)
    │      │
    │      ├─ 4. _emit_success_stream_telemetry() ← 遥测 + 日志
    │      │
    │      └─ 5. _build_success_terminal_payloads()
    │             ├─ metadata 事件 (运行统计/工具/验证/产物)
    │             └─ done 事件 (产物/执行回执)
    │
    └─ [失败] finalize_failure()
           │
           ├─ 1. 记录异常日志
           ├─ 2. _record_run_metrics(hard_error=True)
           ├─ 3. _persist_failed_stream()        ← 保存 [INTERRUPTED] 消息
           ├─ 4. _emit_failed_stream_telemetry()
           └─ 5. _build_failure_terminal_payloads()
                  ├─ error 事件
                  └─ done 事件
```

### 3.3 plan 模式预览协调流程

```
normalize(state, session_id, message)
    │
    ├─ 1. _build_intro_payloads()          ← "开始制定旅行计划..."
    │
    ├─ 2. _load_plan_preview()             ← asyncio.to_thread 生成预览
    │      └─ 失败时返回空列表，不中断主流程
    │
    ├─ 3. _merge_preview_artifacts()       ← 合并 artifact + artifact_patch
    │
    ├─ 4. _build_subagent_start_payloads() ← 子 Agent 启动事件
    │
    ├─ 5. _build_preview_payload()         ← plan_preview 事件
    │      (plan_id / intent / explanation / steps / artifact)
    │
    ├─ 6. _build_subagent_completion_payloads() ← artifact_patch + subagent_end
    │
    └─ 7. _build_summary_payload()         ← "识别意图：trip_planning，将执行 4 步。"
```

### 3.4 16 种 SSE 事件生命周期

```
时间轴 ─────────────────────────────────────────────────────────►

session_id ─► reasoning_start ─► reasoning_chunk* ─► reasoning_end
                                                          │
                                     ┌───────────────────┘
                                     ▼
                              answer_start ─► stage* ─► plan_preview*
                                     │
                                     ├─► subagent_start ─► tool_start ─► tool_end
                                     │       ─► artifact_patch* ─► subagent_end
                                     │
                                     ├─► chunk* ─► metadata ─► done
                                     │
                                     └─► [异常] error ─► done
```

### 3.5 产物深度合并

```
酒店子 Agent 产出:                    景点子 Agent 产出:
{                                     {
  "hotel": {                            "hotel": {"price": 500},
    "name": "三亚湾酒店"                "attractions": [...]
  }                                   }
}
        │                                     │
        └──────────┬──────────────────────────┘
                   ▼
         merge_artifact_payload()
                   │
                   ▼
{
  "hotel": {"name": "三亚湾酒店", "price": 500},
  "attractions": [...]
}

规则: 嵌套字典递归合并, 非字典值直接覆盖
```

---

## 4. 关键设计点

| 设计点 | 实现 | 为什么 |
|--------|------|--------|
| SSE 信封格式 | `data: {JSON}\n\n` | SSE 标准协议格式，前端 EventSource API 自动解析；双换行标记事件结束 |
| Discriminated Union | `ChatStreamEvent = Annotated[Union[...], Field(discriminator="type")]` | 通过 type 字段自动选择对应的事件模型，实现类型安全的序列化/反序列化，避免手动 if-else |
| extra="forbid" | `_ChatStreamEventBase.model_config` | 禁止未知字段静默透传，防止前端收到意外数据，确保 API 契约严格 |
| 流终结器分离 | `ChatStreamFinalizer` 独立类 | 将终结逻辑从流式传输主流程中分离，降低 StreamMixin 复杂度，便于独立测试 |
| Protocol 定义合约 | `_PlanPreviewState(Protocol)` | 只要求实现类有 `reasoning_content/final_artifact/subagent_events` 三个属性，鸭子类型，测试替身更容易创建 |
| 协调器依赖注入 | `ChatPlanPreviewCoordinator` 通过构造函数注入依赖 | 不硬编码依赖，可独立实例化和测试，符合依赖倒置原则 |
| 产物深度合并 | `merge_artifact_payload()` 递归合并 | 多个子 Agent 各自产出部分产物，需要合并为完整旅行计划；嵌套字典递归合并保证数据完整性 |
| exclude_none | `model_dump(exclude_none=True)` | SSE 载荷中 None 值无意义，排除后减小传输体积，降低带宽消耗 |
| asyncio.to_thread | `_load_plan_preview()` 中使用 | 计划预览生成是同步阻塞操作，放到工作线程避免阻塞事件循环 |
| 失败柔化 | `_load_plan_preview` 失败返回空列表 | 预览生成失败不中断主聊天流程，用户仍能获得完整回答 |

---

## 5. 你要回答的问题

1. **SSE 协议中 `data: {JSON}\n\n` 的双换行有什么作用？** 如果只有一个换行，EventSource 会怎么处理？

2. **Discriminated Union 模式相比手动 `if type == "xxx"` 判断有什么优势？** 在新增事件类型时，两种方式的工作量差异是什么？

3. **`ChatStreamFinalizer` 为什么要从 StreamMixin 中分离出来？** 如果不分离，StreamMixin 会有多复杂？

4. **`merge_artifact_payload` 为什么对嵌套字典递归合并，而非简单覆盖？** 如果用 `dict1 | dict2` 合并，酒店子 Agent 的 name 会被景点子 Agent 覆盖吗？

5. **`validate_chat_stream_payload` 中 `exclude_none=True` 有什么实际意义？** 如果不排除 None，前端会收到什么？

6. **`_PlanPreviewState` 使用 Protocol 而非 ABC 有什么好处？** 在单元测试中，Protocol 和 ABC 哪个更容易创建 Mock？

7. **`_load_plan_preview` 为什么要用 `asyncio.to_thread` 而不是直接调用？** 如果直接在事件循环中调用同步函数，会发生什么？
