// chatStreamParser.ts —— 聊天流式响应解析器
// 本文件负责将服务器发来的 SSE（Server-Sent Events）文本行解析为结构化的事件，
// 并调用对应的回调函数通知上层代码
//
// 关键概念解释：
// - SSE 数据格式：服务器发送的每一行以 "data:" 开头，后面跟着 JSON 数据
//   例如：data: {"type": "chunk", "content": "你好"}
// - 解析器（Parser）：将原始文本转换为程序可以理解的结构化数据的工具
// - 类型守卫（Type Guard）：TypeScript 中用来判断一个值是否符合某种类型的函数
//   例如 isRecord() 函数判断一个值是否是普通对象

import type { ArtifactPatch, ChatStreamEventType, ExecutionReceipt, TripPlanArtifact } from '@/types';
import { CHAT_STREAM_EVENT_TYPES } from '@/types';
import { SSEConnectionStatus, type StreamCallbacks } from './chatStreamTypes';

// ChatStreamLifecycle —— 流式请求的生命周期管理接口
// 提供两个方法来控制请求的生命周期
interface ChatStreamLifecycle {
  finalizeRequest: () => void;                         // 结束请求，清理资源
  setConnectionStatus: (status: SSEConnectionStatus) => void; // 更新连接状态
}

// isRecord —— 类型守卫函数，判断一个值是否是普通对象（非数组、非null）
// value is Record<string, unknown> 是 TypeScript 的类型谓词语法
// 告诉 TypeScript：如果这个函数返回 true，那么 value 就是 Record<string, unknown> 类型
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

// stringArray —— 安全地将 unknown 值转换为字符串数组
// 过滤掉非字符串的元素，确保返回的数组中每个元素都是 string 类型
function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

// recordArray —— 安全地将 unknown 值转换为对象数组
// 过滤掉非对象的元素，确保返回的数组中每个元素都是 Record<string, unknown> 类型
function recordArray(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

// unknownArray —— 安全地将 unknown 值转换为数组
// 如果不是数组则返回空数组
function unknownArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

// CHAT_STREAM_EVENT_TYPE_SET —— 将事件类型对象转换为 Set 集合
// Set 是 JavaScript 中的一种数据结构，类似于数组但不允许重复值
// 查找速度比数组快，用来快速判断某个事件类型是否合法
const CHAT_STREAM_EVENT_TYPE_SET = new Set<string>(Object.values(CHAT_STREAM_EVENT_TYPES));

// parseChatStreamEventType —— 解析事件类型字符串
// 如果值是合法的事件类型字符串则返回它，否则返回 null
// typeof value !== 'string'：先判断是否是字符串
// CHAT_STREAM_EVENT_TYPE_SET.has(value)：再判断是否是已知的事件类型
function parseChatStreamEventType(value: unknown): ChatStreamEventType | null {
  if (typeof value !== 'string' || !CHAT_STREAM_EVENT_TYPE_SET.has(value)) return null;
  return value as ChatStreamEventType;
}

// 【核心】handleChatStreamLine —— 处理单行 SSE 数据
// 这是流式响应解析的核心函数，每一行从服务器收到的数据都经过此函数处理
//
// 参数说明：
// - line: 服务器发来的一行原始文本，例如 'data: {"type":"chunk","content":"你好"}'
// - callbacks: 回调函数集合，解析出事件后调用对应的回调
// - lifecycle: 生命周期管理器，用于更新连接状态和清理资源
//
// 返回值：boolean
// - true 表示流已结束（收到 [DONE]、done 或 error 事件），调用方应停止读取
// - false 表示流仍在继续，调用方应继续读取下一行
export function handleChatStreamLine(
  line: string,
  callbacks: StreamCallbacks,
  lifecycle: ChatStreamLifecycle
): boolean {
  // 去除行尾的回车符和首尾空格
  const trimmed = line.replace(/\r$/, '').trim();
  // 如果不是以 "data:" 开头，说明不是 SSE 数据行，跳过
  if (!trimmed.startsWith('data:')) return false;

  // 提取 "data:" 后面的内容
  const dataStr = trimmed.slice(5).trim();
  // 如果内容为空，跳过
  if (!dataStr) return false;

  // 【核心】处理 [DONE] 信号 —— 服务器主动告知流式传输结束
  // 这是 SSE 协议的约定，服务器发送 "data: [DONE]" 表示所有数据已发送完毕
  if (dataStr === '[DONE]') {
    lifecycle.setConnectionStatus(SSEConnectionStatus.IDLE);
    callbacks.onComplete();
    lifecycle.finalizeRequest();
    return true; // 流已结束
  }

  try {
    // JSON.parse：将 JSON 字符串解析为 JavaScript 对象
    // as Record<string, unknown>：告诉 TypeScript 把解析结果当作"键是字符串、值是任意类型"的对象
    const data = JSON.parse(dataStr) as Record<string, unknown>;
    // 解析事件类型
    const dataType = parseChatStreamEventType(data.type);

    // 处理 SESSION_ID 事件 —— 服务器返回会话ID
    // 应用场景：用户发起新对话时，服务器创建一个新会话并返回其ID
    if (dataType === CHAT_STREAM_EVENT_TYPES.SESSION_ID && typeof data.session_id === 'string') {
      callbacks.onSessionId?.(data.session_id);
      // ?. 是可选链，如果 onSessionId 未定义则不调用，避免报错
      return false;
    }

    // 处理 STAGE 事件 —— 当前处理阶段变更
    // 应用场景：AI 从"理解需求"阶段进入"搜索信息"阶段，界面可以显示对应的进度提示
    if (dataType === CHAT_STREAM_EVENT_TYPES.STAGE) {
      callbacks.onStage?.({
        stage: typeof data.stage === 'string' ? data.stage : undefined,
        label: typeof data.label === 'string' ? data.label : undefined,
        progress: data.progress === undefined ? null : Number(data.progress),
        subagent: typeof data.subagent === 'string' ? data.subagent : null,
      });
      return false;
    }

    // 处理 PLAN_PREVIEW 事件 —— 行程计划预览
    // 应用场景：AI 在正式生成行程前，先展示一个规划概览让用户确认方向
    if (dataType === CHAT_STREAM_EVENT_TYPES.PLAN_PREVIEW) {
      callbacks.onPlanPreview?.({
        planId: typeof data.plan_id === 'string' ? data.plan_id : null,
        intent: typeof data.intent === 'string' ? data.intent : null,
        explanation: typeof data.explanation === 'string' ? data.explanation : null,
        validationStatus: typeof data.validation_status === 'string' ? data.validation_status : null,
        validationErrors: unknownArray(data.validation_errors),
        steps: recordArray(data.steps),
        artifact: isRecord(data.artifact) ? (data.artifact as unknown as TripPlanArtifact) : null,
        artifactPatch: isRecord(data.artifact_patch) ? (data.artifact_patch as ArtifactPatch) : null,
        subagent: typeof data.subagent === 'string' ? data.subagent : null,
        skills: stringArray(data.skills),
      });
      return false;
    }

    // 处理 SUBAGENT_START 事件 —— 子代理启动
    // 应用场景：主AI将任务分发给"酒店搜索"子代理，界面显示"正在搜索酒店..."
    if (dataType === CHAT_STREAM_EVENT_TYPES.SUBAGENT_START && typeof data.subagent === 'string') {
      callbacks.onSubagentStart?.({
        subagent: data.subagent,
        description: typeof data.description === 'string' ? data.description : null,
        skills: stringArray(data.skills),
        toolNames: stringArray(data.tool_names),
        sequence: data.sequence === undefined ? null : Number(data.sequence),
        trigger: typeof data.trigger === 'string' ? data.trigger : null,
      });
      return false;
    }

    // 处理 SUBAGENT_END 事件 —— 子代理结束
    // 应用场景："酒店搜索"子代理完成工作，界面更新为"酒店搜索完成"
    if (dataType === CHAT_STREAM_EVENT_TYPES.SUBAGENT_END && typeof data.subagent === 'string') {
      callbacks.onSubagentEnd?.({
        subagent: data.subagent,
        sequence: data.sequence === undefined ? null : Number(data.sequence),
        status: typeof data.status === 'string' ? data.status : null,
        summary: typeof data.summary === 'string' ? data.summary : null,
      });
      return false;
    }

    // 处理 ARTIFACT_PATCH 事件 —— 行程计划局部更新
    // 应用场景：子代理"景点推荐"找到了新景点，通过补丁更新行程计划中的景点部分
    // 不需要重新发送整个行程，只发送变化的部分，提高效率
    if (
      dataType === CHAT_STREAM_EVENT_TYPES.ARTIFACT_PATCH &&
      typeof data.subagent === 'string' &&
      isRecord(data.artifact_patch)
    ) {
      callbacks.onArtifactPatch?.(data.subagent, data.artifact_patch as ArtifactPatch);
      return false;
    }

    // 处理 METADATA 事件 —— 流式响应的元数据统计
    // 应用场景：AI 完成回答后，发送统计数据，如使用了哪些工具、推理了多长等
    if (dataType === CHAT_STREAM_EVENT_TYPES.METADATA) {
      const metadataPayload = {
        totalSteps: Number(data.total_steps || 0),
        toolsUsed: stringArray(data.tools_used),
        hasReasoning: Boolean(data.has_reasoning),
        reasoningLength: Number(data.reasoning_length || 0),
        answerLength: Number(data.answer_length || 0),
        verificationPassed: data.verification_passed === undefined ? null : Boolean(data.verification_passed),
        staleResultCount: Number(data.stale_result_count || 0),
        fallbackSteps: Number(data.fallback_steps || 0),
        planId: typeof data.plan_id === 'string' ? data.plan_id : null,
        executionStats: isRecord(data.execution_stats) ? data.execution_stats : undefined,
        runId: typeof data.run_id === 'string' ? data.run_id : '',
        requestId: typeof data.request_id === 'string' ? data.request_id : '',
        traceId: typeof data.trace_id === 'string' ? data.trace_id : '',
        artifact: isRecord(data.artifact) ? (data.artifact as unknown as TripPlanArtifact) : null,
        executionReceipt: isRecord(data.execution_receipt)
          ? (data.execution_receipt as unknown as ExecutionReceipt)
          : null,
        ...(typeof data.session_id === 'string' && data.session_id ? { sessionId: data.session_id } : {}),
        // ... 是展开运算符，将一个对象的属性"铺开"到当前对象中
      };
      callbacks.onMetadata(metadataPayload);
      return false;
    }

    // 处理 REASONING_START 事件 —— AI 推理过程开始
    // 应用场景：界面显示"AI正在思考..."的动画
    if (dataType === CHAT_STREAM_EVENT_TYPES.REASONING_START) {
      callbacks.onReasoningStart();
      return false;
    }

    // 处理 reasoning_timestamp 事件 —— 推理时间戳
    // 注意：这里没有使用 dataType 判断，而是直接比较 data.type
    // 因为 reasoning_timestamp 可能不在 CHAT_STREAM_EVENT_TYPES 枚举中
    if (typeof data.type === 'string' && data.type === 'reasoning_timestamp' && typeof data.timestamp === 'string') {
      callbacks.onReasoningTimestamp(data.timestamp);
      return false;
    }

    // 处理 REASONING_CHUNK 事件 —— AI 推理过程的文本片段
    // 应用场景：界面逐字显示AI的思考过程，如"我需要先查找北京的景点信息..."
    if (dataType === CHAT_STREAM_EVENT_TYPES.REASONING_CHUNK && typeof data.content === 'string') {
      callbacks.onReasoning(data.content);
      return false;
    }

    // 处理 REASONING_END 事件 —— AI 推理过程结束
    if (dataType === CHAT_STREAM_EVENT_TYPES.REASONING_END) {
      callbacks.onReasoningEnd();
      return false;
    }

    // 处理 ANSWER_START 事件 —— AI 正式回答开始
    // 应用场景：推理结束后，界面切换到"回答"模式，准备显示最终答案
    if (dataType === CHAT_STREAM_EVENT_TYPES.ANSWER_START) {
      callbacks.onAnswerStart();
      return false;
    }

    // 处理 TOOL_START 事件 —— 工具调用开始
    // 应用场景：AI 调用"酒店搜索"工具，界面显示"正在搜索酒店..."
    if (dataType === CHAT_STREAM_EVENT_TYPES.TOOL_START && typeof data.tool === 'string') {
      callbacks.onToolStart?.(data.tool);
      return false;
    }

    // 处理 TOOL_END 事件 —— 工具调用返回结果
    // 应用场景："酒店搜索"工具返回了结果，界面更新状态
    if (dataType === CHAT_STREAM_EVENT_TYPES.TOOL_END && typeof data.tool === 'string') {
      callbacks.onToolEnd?.(data.tool, typeof data.result === 'string' ? data.result : '');
      return false;
    }

    // 【核心】处理 CHUNK 事件 —— 回答文本片段
    // 这是最常见的事件类型，AI 的回答内容通过多个 CHUNK 逐字送达
    // 应用场景：AI 回答"北京三日游的行程如下..."，每个字/词作为一个 CHUNK 发送
    if (dataType === CHAT_STREAM_EVENT_TYPES.CHUNK && typeof data.content === 'string') {
      callbacks.onChunk(data.content);
      return false;
    }

    // 处理 ERROR 事件 —— 服务器报告错误
    // 流式传输中出现错误，需要终止
    if (dataType === CHAT_STREAM_EVENT_TYPES.ERROR && typeof data.content === 'string') {
      lifecycle.setConnectionStatus(SSEConnectionStatus.ERROR);
      callbacks.onError(data.content);
      lifecycle.finalizeRequest();
      return true; // 流已结束（出错）
    }

    // 【核心】处理 DONE 事件 —— 流式响应正式完成
    // 与 [DONE] 不同，这个事件可能携带最终数据（如完整的行程计划）
    if (dataType === CHAT_STREAM_EVENT_TYPES.DONE) {
      lifecycle.setConnectionStatus(SSEConnectionStatus.IDLE);
      const completionPayload = {
        artifact: isRecord(data.artifact) ? (data.artifact as unknown as TripPlanArtifact) : null,
        runId: typeof data.run_id === 'string' ? data.run_id : '',
        requestId: typeof data.request_id === 'string' ? data.request_id : '',
        traceId: typeof data.trace_id === 'string' ? data.trace_id : '',
        executionReceipt: isRecord(data.execution_receipt)
          ? (data.execution_receipt as unknown as ExecutionReceipt)
          : null,
        ...(typeof data.session_id === 'string' && data.session_id ? { sessionId: data.session_id } : {}),
      };
      callbacks.onComplete(completionPayload);
      lifecycle.finalizeRequest();
      return true; // 流已结束
    }

    // 兜底处理：如果 data 中有 chunk 字段（旧格式兼容），也当作文本片段处理
    if (typeof data.chunk === 'string') callbacks.onChunk(data.chunk);
    // 兜底处理：如果 data 中有 error 字段（旧格式兼容），也当作错误处理
    if (typeof data.error === 'string') {
      lifecycle.setConnectionStatus(SSEConnectionStatus.ERROR);
      callbacks.onError(data.error);
      lifecycle.finalizeRequest();
      return true;
    }
  } catch {
    // JSON 解析失败时忽略这一行（格式错误的 SSE 数据）
    // 不抛出异常，避免因为一行坏数据导致整个流中断
  }

  return false; // 默认：流未结束
}
