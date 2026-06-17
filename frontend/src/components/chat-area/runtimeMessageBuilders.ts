// 'use client' 是 Next.js 的指令，表示此文件仅在浏览器端运行
'use client';

// 导入类型定义——这些类型来自项目的类型文件和服务接口
// type 关键字表示只导入类型（编译时使用，不会生成运行时代码）
import type { MessageDiagnostics, SubagentEvent, TripPlanArtifact } from '@/types';
import type { StreamCompletionPayload, StreamMetadata } from '@/services/api';

// 构建完成诊断数据所需的参数
// 这些参数来自流式响应完成后的各种数据源
interface CompletionDiagnosticsArgs {
  artifact: TripPlanArtifact | null;          // 行程结构化数据（Artifact），包含行程、预算、校验等信息
  completion?: StreamCompletionPayload;       // 流式完成时的载荷数据，包含 sessionId、runId 等追踪信息
  metadata: StreamMetadata | null;            // 流式元数据，包含工具使用、校验结果、执行统计等
  sessionId?: string | null;                  // 会话 ID，用于标识一次完整的对话
  subagentEvents: SubagentEvent[];            // 子智能体事件列表，记录各子智能体的运行状态
}

// 构建最终推理文本
// 如果有时间戳，在推理文本前加上时间戳标记
// 应用场景：AI 的推理过程（Chain of Thought）可能跨越多个时间点，加上时间戳便于调试和追踪
export function buildFinalReasoning(reasoning: string, timestamp?: string): string {
  if (!timestamp) return reasoning;
  // 模板字符串：${timestamp} 会被替换为实际的时间戳值
  return `[Timestamp: ${timestamp}]\n\n${reasoning}`;
}

// 【核心】构建流式完成后的诊断数据
// 诊断数据用于在界面上展示 AI 的运行详情，如使用了哪些工具、校验是否通过、执行统计等
// 数据来源有三个，按优先级从高到低：completion（流式完成载荷）> metadata（流式元数据）> artifact（行程数据）
// 应用场景：用户点击消息上的"查看详情"时，展示的诊断信息就是由这个函数生成的
export function buildCompletionDiagnostics({
  artifact,
  completion,
  metadata,
  sessionId,
  subagentEvents,
}: CompletionDiagnosticsArgs): MessageDiagnostics | undefined {
  // 如果没有任何有效数据，返回 undefined，表示不需要诊断信息
  if (!metadata && !artifact && subagentEvents.length === 0) return undefined;

  // 解析会话 ID，优先级：completion > metadata > 传入的 sessionId
  // ?. 是可选链操作符，如果前面的值为 null/undefined 则直接返回 undefined，不会报错
  const resolvedSessionId = completion?.sessionId || metadata?.sessionId || sessionId || undefined;

  return {
    // 如果有会话 ID 则包含，否则不包含这个字段
    // 展开运算符 ... 配合条件对象：{ ...(条件 ? { key: value } : {}) }
    // 如果条件为 true，则展开 { sessionId: '...' }；如果为 false，则展开空对象 {}（即不添加该字段）
    ...(resolvedSessionId ? { sessionId: resolvedSessionId } : {}),
    // 使用的工具列表，优先从 metadata 取，其次从 artifact 取
    toolsUsed: metadata?.toolsUsed || artifact?.toolsUsed || [],
    // 校验是否通过，?? 是空值合并运算符：左侧为 null/undefined 时才取右侧
    verificationPassed: metadata?.verificationPassed ?? artifact?.verification.passed ?? null,
    // 过时结果数量（预算计算中使用了缓存/旧数据的次数）
    staleResultCount: metadata?.staleResultCount ?? artifact?.budget.staleResultCount ?? 0,
    // 回退步骤数（AI 规划过程中因数据不足而使用备选方案的步骤数）
    fallbackSteps: metadata?.fallbackSteps ?? artifact?.budget.fallbackSteps ?? 0,
    // 行程方案 ID
    planId: metadata?.planId ?? artifact?.itinerary.planId ?? null,
    // 执行统计信息（如总耗时、API 调用次数等）
    executionStats: metadata?.executionStats ?? artifact?.budget.summary,
    // 行程结构化数据
    artifact,
    // 子智能体事件列表
    subagentEvents,
    // 执行回执，包含详细的执行过程记录
    executionReceipt: completion?.executionReceipt ?? metadata?.executionReceipt ?? undefined,
    // 运行 ID，用于追踪一次 AI 运行
    runId: completion?.runId || metadata?.runId,
    // 请求 ID，用于追踪一次 API 请求
    requestId: completion?.requestId || metadata?.requestId,
    // 追踪 ID，用于分布式链路追踪
    traceId: completion?.traceId || metadata?.traceId,
  };
}

// 构建用户手动停止生成时的诊断数据
// 比完成诊断更简单，只包含 artifact 和子智能体事件
// 应用场景：用户点击"停止生成"按钮后，仍然保留已有的行程数据和子智能体事件
export function buildStoppedDiagnostics({
  artifact,
  sessionId,
  subagentEvents,
}: {
  artifact: TripPlanArtifact | null;
  sessionId?: string | null;
  subagentEvents: SubagentEvent[];
}): MessageDiagnostics | undefined {
  // 没有行程数据也没有子智能体事件，则不需要诊断信息
  if (!artifact && subagentEvents.length === 0) return undefined;
  return {
    ...(sessionId ? { sessionId } : {}),
    artifact,
    subagentEvents,
  };
}
