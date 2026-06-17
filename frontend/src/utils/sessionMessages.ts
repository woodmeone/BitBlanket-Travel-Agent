// 会话消息处理工具模块
// 负责将从后端获取的原始消息数据标准化、与最新产物关联等操作
//
// 核心功能：
// 1. 标准化持久化消息：将后端返回的原始数据转换为类型安全的 Message 对象
// 2. 查找最新助手消息：在消息列表中找到最后一条 AI 回复
// 3. 注入最新产物：将后端返回的最新旅行计划产物关联到对应的消息上
//
// 应用场景：用户打开历史会话时，后端返回的消息数据可能格式不规范，
// 需要标准化处理；同时需要将最新的产物数据注入到对应消息的 diagnostics 中，
// 以便前端展示行程详情面板

import type {
  ExecutionReceipt,
  LatestArtifactResponse,
  Message,
  MessageDiagnostics,
  SubagentEvent,
  TripPlanArtifact,
} from '@/types';

// 判断一个值是否为普通对象（Record）
// 与 agentArtifacts.ts 中的同名函数功能相同，此处独立定义以避免模块间循环依赖
// value is Record<string, unknown> 是类型谓词，告诉编译器返回 true 时 value 的类型
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

// 标准化子代理事件列表 —— 将原始数据转换为类型安全的 SubagentEvent 数组
// 应用场景：后端返回的 subagentEvents 可能格式不规范（如字段缺失、类型错误），
// 此函数逐个字段校验并转换，确保前端使用时类型安全
function normalizeSubagentEvents(value: unknown): SubagentEvent[] | undefined {
  if (!Array.isArray(value)) return undefined;  // 不是数组则返回 undefined
  return value
    .filter(isRecord)                    // 过滤掉非对象元素
    .map((event) => ({
      subagent: typeof event.subagent === 'string' ? event.subagent : 'unknown',  // 确保是字符串
      description: typeof event.description === 'string' ? event.description : null,
      // item is string 是类型谓词，确保 filter 后数组元素类型为 string
      skills: Array.isArray(event.skills) ? event.skills.filter((item): item is string => typeof item === 'string') : [],
      toolNames: Array.isArray(event.toolNames)
        ? event.toolNames.filter((item): item is string => typeof item === 'string')
        : [],
      sequence: typeof event.sequence === 'number' ? event.sequence : null,
      trigger: typeof event.trigger === 'string' ? event.trigger : null,
      status: typeof event.status === 'string' ? event.status : null,
      summary: typeof event.summary === 'string' ? event.summary : null,
      timestamp: typeof event.timestamp === 'string' ? event.timestamp : undefined,
    }));
}

// 标准化执行回执 —— 将原始数据转换为 ExecutionReceipt 类型
// 简化处理：只检查是否为对象，如果是则直接断言类型
function normalizeExecutionReceipt(value: unknown): ExecutionReceipt | undefined {
  return isRecord(value) ? (value as unknown as ExecutionReceipt) : undefined;
}

// 【核心】标准化消息诊断信息 —— 将原始数据转换为类型安全的 MessageDiagnostics
// 逐个字段校验类型，确保每个字段都符合预期类型，不符合则使用默认值
// 应用场景：后端返回的 diagnostics 可能缺少某些字段或类型不匹配，
// 此函数确保前端使用时不会因类型错误而崩溃
function normalizeDiagnostics(value: unknown): MessageDiagnostics | undefined {
  if (!isRecord(value)) return undefined;

  return {
    sessionId: typeof value.sessionId === 'string' ? value.sessionId : undefined,
    toolsUsed: Array.isArray(value.toolsUsed) ? value.toolsUsed.filter((item): item is string => typeof item === 'string') : [],
    verificationPassed:
      typeof value.verificationPassed === 'boolean' || value.verificationPassed === null
        ? value.verificationPassed
        : null,                          // 不是 boolean 也不是 null 则默认为 null
    staleResultCount: typeof value.staleResultCount === 'number' ? value.staleResultCount : 0,
    fallbackSteps: typeof value.fallbackSteps === 'number' ? value.fallbackSteps : 0,
    planId: typeof value.planId === 'string' ? value.planId : null,
    executionStats: isRecord(value.executionStats) ? value.executionStats : undefined,
    artifact: isRecord(value.artifact) ? (value.artifact as unknown as TripPlanArtifact) : null,
    subagentEvents: normalizeSubagentEvents(value.subagentEvents),  // 递归标准化子代理事件
    executionReceipt: normalizeExecutionReceipt(value.executionReceipt),
    runId: typeof value.runId === 'string' ? value.runId : undefined,
    requestId: typeof value.requestId === 'string' ? value.requestId : undefined,
    traceId: typeof value.traceId === 'string' ? value.traceId : undefined,
  };
}

// 【核心】标准化持久化消息列表 —— 将后端返回的原始消息数组转换为类型安全的 Message 数组
// 应用场景：用户打开历史会话时，后端返回的消息数据需要标准化处理
// 例如：后端返回 [{ role: 'assistant', content: 123 }] → 标准化为 [{ role: 'assistant', content: '' }]
export function normalizePersistedMessages(value: unknown): Message[] {
  if (!Array.isArray(value)) return [];  // 不是数组则返回空数组

  return value
    .filter(isRecord)                    // 过滤掉非对象元素
    .map((message) => ({
      // role 只允许 'assistant' 或 'user'，其他值一律视为 'user'
      role: message.role === 'assistant' ? 'assistant' : 'user',
      content: typeof message.content === 'string' ? message.content : '',  // 非字符串则用空字符串
      timestamp: typeof message.timestamp === 'string' ? message.timestamp : '--:--:--',
      reasoning: typeof message.reasoning === 'string' ? message.reasoning : undefined,
      diagnostics: normalizeDiagnostics(message.diagnostics),  // 递归标准化诊断信息
    }));
}

// 查找最新助手消息的索引 —— 从后往前遍历消息列表，找到最后一条 AI 回复
// 应用场景：需要将最新产物关联到最后一条 AI 回复上
// 返回 -1 表示没有找到助手消息
export function findLatestAssistantMessageIndex(messages: Message[]): number {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (messages[index]?.role === 'assistant') return index;
    // ?. 是可选链运算符，如果 messages[index] 为 null/undefined 则不会报错，而是返回 undefined
  }
  return -1;
}

// 确定产物应该关联到哪条消息 —— 优先使用指定索引，否则找最新的助手消息
// 应用场景：后端返回产物时可能指定了 message_index，优先使用；
// 如果指定的索引无效（越界或不是助手消息），则回退到最新的助手消息
function resolveArtifactTargetIndex(messages: Message[], preferredIndex?: number | null): number {
  if (
    typeof preferredIndex === 'number' &&
    preferredIndex >= 0 &&
    preferredIndex < messages.length &&
    messages[preferredIndex]?.role === 'assistant'
  ) {
    return preferredIndex;               // 使用指定的索引
  }
  return findLatestAssistantMessageIndex(messages);  // 回退到最新助手消息
}

// 【核心】将最新产物注入到消息列表中 —— 在对应消息的 diagnostics 中添加产物数据
// 应用场景：用户打开历史会话时，需要将最新的旅行计划产物关联到对应的 AI 回复上，
// 以便前端展示行程详情面板
// 流程：
// 1. 检查后端返回的最新产物是否有效
// 2. 找到产物应该关联的消息（通常是最后一条 AI 回复）
// 3. 在该消息的 diagnostics 中注入产物、会话ID、计划ID、运行ID 等信息
export function hydrateMessagesWithLatestArtifact(
  messages: Message[],
  latestArtifact: LatestArtifactResponse | null | undefined
): Message[] {
  // 如果产物无效，直接返回原始消息列表
  if (!latestArtifact?.success || !latestArtifact.artifact_found || !latestArtifact.artifact) {
    return messages;
  }
  const artifact = latestArtifact.artifact;

  // 找到产物应该关联的消息索引
  const targetIndex = resolveArtifactTargetIndex(messages, latestArtifact.message_index);
  if (targetIndex < 0) return messages;  // 没有找到目标消息

  // 使用 map 创建新的消息数组，只修改目标索引的消息
  return messages.map((message, index) => {
    if (index !== targetIndex) return message;  // 非目标消息保持不变

    // 修改目标消息：注入产物数据到 diagnostics
    return {
      ...message,                        // 展开运算符：复制原消息的所有字段
      content: message.content || artifact.answer || '',  // 如果消息内容为空，用产物的回答填充
      diagnostics: {
        ...message.diagnostics,          // 保留原有的诊断信息
        artifact,                        // 注入产物数据
        sessionId: latestArtifact.session_id ?? message.diagnostics?.sessionId,  // 优先使用产物的会话ID
        planId: artifact.itinerary.planId ?? message.diagnostics?.planId ?? null,  // 优先使用产物的计划ID
        runId: latestArtifact.run_id ?? message.diagnostics?.runId,  // 优先使用产物的运行ID
      },
    };
  });
}
