// chatStreamTypes.ts —— 聊天流式响应的类型定义文件
// 本文件定义了 SSE（Server-Sent Events，服务器推送事件）流式通信中使用的所有类型
//
// 关键概念解释：
// - SSE（Server-Sent Events）：一种服务器向浏览器单向推送数据的技术，
//   类似于"直播弹幕"——服务器持续发送消息，浏览器逐条接收
// - enum（枚举）：TypeScript 中定义一组命名常量的语法，例如 { RED, GREEN, BLUE }
// - interface（接口）：TypeScript 中定义对象"形状"的语法，描述一个对象有哪些属性
// - type：TypeScript 中定义类型别名的关键字，可以给复杂类型取个简短的名字

// import type：只引入类型定义，不会产生实际的运行时代码
// 这些类型来自项目的统一类型定义文件 @/types
import type {
  ArtifactPatch,       // 行程计划的增量补丁（局部更新数据）
  ExecutionReceipt,    // 执行回执，记录AI执行过程的统计信息
  PlanPreview,         // 计划预览，AI生成行程前的规划概览
  StreamStageEvent,    // 流式阶段事件，表示当前处于哪个处理阶段
  SubagentEvent,       // 子代理事件，表示某个子AI助手的启动/结束
  TripPlanArtifact,    // 行程计划产物，包含完整的旅行行程数据
} from '@/types';

// 【核心】SSEConnectionStatus —— SSE 连接状态枚举
// enum：枚举类型，每个值都是一个命名的常量，方便代码中引用
// 例如可以用 SSEConnectionStatus.IDLE 代替字符串 'idle'，避免拼写错误
//
// 连接状态的流转过程：
// IDLE（空闲）→ CONNECTING（连接中）→ STREAMING（接收数据中）
// 如果出错：→ ERROR（错误）
// 如果断开需要重连：→ RECONNECTING（重连中）
// 如果用户主动断开：→ DISCONNECTED（已断开）
export enum SSEConnectionStatus {
  IDLE = 'idle',           // 空闲，没有正在进行的请求
  CONNECTING = 'connecting', // 正在建立连接
  STREAMING = 'streaming',   // 正在接收流式数据
  RECONNECTING = 'reconnecting', // 连接断开后正在重连
  ERROR = 'error',           // 连接出错
  DISCONNECTED = 'disconnected', // 连接已断开
}

// StreamMetadata —— 流式响应的元数据
// 当一次流式聊天完成后，服务器会发送这些统计信息
// 例如：用了哪些工具、推理了多长、回答了多长等
export interface StreamMetadata {
  sessionId?: string;              // 会话ID，标识这次对话
  totalSteps: number;              // AI 执行的总步骤数
  toolsUsed: string[];             // AI 使用过的工具名称列表
  hasReasoning: boolean;           // 是否包含推理过程
  reasoningLength: number;         // 推理内容的字符长度
  answerLength: number;            // 回答内容的字符长度
  verificationPassed: boolean | null; // 验证是否通过（null 表示未验证）
  staleResultCount: number;        // 过时结果的数量（AI 中间步骤产生的但最终未采用的结果）
  fallbackSteps: number;           // 降级步骤数（AI 执行失败后回退的步骤数）
  planId?: string | null;          // 行程计划ID
  executionStats?: Record<string, unknown>; // 执行统计信息，键值对结构
  // Record<string, unknown> 表示"键是字符串、值是任意类型的对象"
  runId?: string;                  // 一次AI运行的唯一标识
  requestId?: string;              // 请求ID
  traceId?: string;                // 链路追踪ID
  artifact?: TripPlanArtifact | null; // 最终生成的行程计划产物
  executionReceipt?: ExecutionReceipt | null; // 执行回执
}

// StreamCompletionPayload —— 流式响应完成时携带的数据
// 当服务器发送 [DONE] 或 done 事件时，会附带这些信息
export interface StreamCompletionPayload {
  artifact?: TripPlanArtifact | null; // 最终生成的行程计划
  sessionId?: string;                 // 会话ID
  runId?: string;                     // AI运行ID
  requestId?: string;                 // 请求ID
  traceId?: string;                   // 链路追踪ID
  executionReceipt?: ExecutionReceipt | null; // 执行回执
}

// 【核心】StreamCallbacks —— 流式响应的回调函数集合
// 回调函数：一种"你告诉我事情发生了，我来处理"的模式
// 调用方提供这些函数，当对应事件发生时自动被调用
//
// 应用场景举例：用户发送"帮我规划北京3日游"，AI 开始流式响应：
// 1. onSessionId → 收到会话ID
// 2. onReasoningStart → AI 开始思考
// 3. onReasoning → AI 思考过程逐字显示
// 4. onReasoningEnd → AI 思考结束
// 5. onAnswerStart → AI 开始回答
// 6. onChunk → AI 回答内容逐字显示
// 7. onToolStart → AI 调用工具（如搜索酒店）
// 8. onToolEnd → 工具返回结果
// 9. onArtifactPatch → 行程计划局部更新
// 10. onComplete → 流式响应完成
export interface StreamCallbacks {
  onSessionId?: (sessionId: string) => void;          // 收到会话ID时触发
  onStage?: (stage: StreamStageEvent) => void;        // 处理阶段变更时触发
  onPlanPreview?: (preview: PlanPreview) => void;     // 收到计划预览时触发
  onSubagentStart?: (event: SubagentEvent) => void;   // 子代理启动时触发
  onSubagentEnd?: (event: SubagentEvent) => void;     // 子代理结束时触发
  onArtifactPatch?: (subagent: string, patch: ArtifactPatch) => void; // 行程计划局部更新时触发
  onChunk: (content: string) => void;                 // 【核心】收到回答文本片段时触发（必须提供）
  onReasoning: (content: string) => void;             // 收到推理文本片段时触发
  onReasoningStart: () => void;                       // 推理过程开始时触发
  onReasoningEnd: () => void;                         // 推理过程结束时触发
  onReasoningTimestamp: (timestamp: string) => void;  // 收到推理时间戳时触发
  onAnswerStart: () => void;                          // 正式回答开始时触发
  onToolStart?: (toolName: string) => void;           // 工具调用开始时触发
  onToolEnd?: (toolName: string, result: string) => void; // 工具调用返回结果时触发
  onMetadata: (data: StreamMetadata) => void;         // 收到元数据时触发
  onError: (error: string) => void;                   // 【核心】发生错误时触发（必须提供）
  onComplete: (payload?: StreamCompletionPayload) => void; // 【核心】流式响应完成时触发（必须提供）
  onStop?: () => boolean;                             // 外部判断是否需要停止接收（返回 true 表示停止）
  onConnectionChange?: (status: SSEConnectionStatus) => void; // 连接状态变更时触发
}
