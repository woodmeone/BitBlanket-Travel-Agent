// 'use client' 表示这是一个客户端组件，在浏览器端运行（Next.js 的约定）
// 场景举例：用户在聊天页面看到的消息列表、执行洞察面板、快捷提示等，都由此组件组织
'use client';

// 导入 React 核心库
import React from 'react';
// 导入消息列表子组件，负责渲染聊天消息（用户消息 + AI 回复）
import MessageList from '@/components/MessageList';
// 导入各种类型定义：
//   Message - 单条聊天消息
//   PlanPreview - 旅行计划预览数据
//   StreamStageEvent - 流式输出的阶段事件（如"正在搜索"、"正在生成"）
//   SubagentEvent - 子代理事件（AI 在推理过程中调用的子任务）
//   TripPlanArtifact - 旅行计划产出物（最终生成的行程方案）
import type { Message, PlanPreview, StreamStageEvent, SubagentEvent, TripPlanArtifact } from '@/types';
// 导入流式元数据类型（包含 token 用量、模型信息等）
import type { StreamMetadata } from '@/services/api';
// 导入执行洞察面板子组件，展示 AI 的推理过程、工具调用、阶段状态等
import ExecutionInsights from './ExecutionInsights';
// 导入快捷提示子组件，在无消息时展示预设的旅行需求示例
import QuickStartPrompts from './QuickStartPrompts';
// 导入运行时日志类型
import type { RuntimeLog } from './shared';

// 【核心】ChatConversationViewProps 定义了聊天对话视图组件需要的所有属性（props）
// 这个组件是聊天区域的核心展示层，负责组织：执行洞察面板 + 消息列表 + 快捷提示 + 错误提示
// 场景举例：用户打开聊天页面，看到 AI 的推理过程面板、历史消息、快捷提示卡片等
interface ChatConversationViewProps {
  messages: Message[];                                    // 聊天消息列表，包含用户消息和 AI 回复
  messagesEndRef: React.RefObject<HTMLDivElement | null>; // 消息列表底部的引用，用于自动滚动到底部
                                                          // React.RefObject 是 React 的引用类型，用来直接操作 DOM 元素
  streamingMessage: string;                               // 当前正在流式输出的 AI 回答文本（逐步追加）
  streamingReasoning: string;                             // 当前正在流式输出的 AI 推理过程文本
  waitingForResponse: boolean;                            // 是否正在等待 AI 首次响应（发送后、回答前）
  isThinking: boolean;                                    // AI 是否正在思考/推理中
  isStreaming: boolean;                                   // 是否正在流式输出（AI 正在逐字生成回答）
  currentTool: string | null;                             // 当前正在调用的工具名称，如 "search_weather"，null 表示未调用
  reasoningExpanded: Record<string, boolean>;             // 推理过程的展开/折叠状态，key 是消息 ID，value 是是否展开
                                                          // Record<string, boolean> 是 TypeScript 类型，表示键为字符串、值为布尔值的对象
  error: string | null;                                   // 错误信息，有值时在页面底部显示红色错误提示
  metadata: StreamMetadata | null;                        // 流式输出的元数据（token 用量、模型名称等）
  stageState: StreamStageEvent | null;                    // 当前流式输出阶段的状态（如"搜索中"、"生成中"）
  stageHistory: StreamStageEvent[];                       // 已完成的阶段历史记录列表
  runtimeLogs: RuntimeLog[];                              // 运行时日志列表，记录 AI 执行过程中的关键事件
  planPreview: PlanPreview | null;                        // 旅行计划预览数据，AI 生成计划时实时展示
  artifactState: TripPlanArtifact | null;                 // 旅行计划产出物，包含最终生成的完整行程方案
  activeSubagent: string | null;                          // 当前活跃的子代理名称（AI 推理中调用的子任务）
  subagentEvents: SubagentEvent[];                       // 子代理事件列表，记录子代理的执行过程
  onContinuePrompt: (prompt: string) => void;             // 继续对话回调，用户点击"继续"按钮时触发
  onPickPrompt: (prompt: string) => void;                 // 选择快捷提示回调，用户点击预设提示卡片时触发
  onToggleReasoning: (messageId: string) => void;         // 切换推理过程展开/折叠回调，用户点击推理区域时触发
}

// 【核心】ChatConversationView 聊天对话视图组件
// React.FC<ChatConversationViewProps> 表示这是一个函数组件，props 类型为 ChatConversationViewProps
// 场景举例：用户发送"北京两日游"后，此组件展示 AI 的推理过程、工具调用、最终行程方案
// props 解构：把传入的 props 对象拆开为独立变量，直接使用变量名即可
const ChatConversationView: React.FC<ChatConversationViewProps> = ({
  messages,
  messagesEndRef,
  streamingMessage,
  streamingReasoning,
  waitingForResponse,
  isThinking,
  isStreaming,
  currentTool,
  reasoningExpanded,
  error,
  metadata,
  stageState,
  stageHistory,
  runtimeLogs,
  planPreview,
  artifactState,
  activeSubagent,
  subagentEvents,
  onContinuePrompt,
  onPickPrompt,
  onToggleReasoning,
}) => {
  // <>...</> 是 React Fragment 的简写，用于包裹多个子元素而不额外创建 DOM 节点
  return (
    <>
      {/* ExecutionInsights 执行洞察面板：展示 AI 的实时推理过程
          场景举例：AI 正在"搜索北京酒店"，面板中会显示当前阶段和日志 */}
      <ExecutionInsights
        isStreaming={isStreaming}
        isThinking={isThinking}
        currentTool={currentTool}
        stageState={stageState}
        stageHistory={stageHistory}
        runtimeLogs={runtimeLogs}
        planPreview={planPreview}
        metadata={metadata}
        artifact={artifactState}
        activeSubagent={activeSubagent}
        subagentEvents={subagentEvents}
      />

      {/* 【核心】MessageList 消息列表组件：渲染所有聊天消息
          streamingMessage - 正在流式输出的回答文本
          streamingReasoning - 正在流式输出的推理过程
          isWaiting - 是否等待首次响应
          isThinking - AI 是否在思考
          currentTool - 当前调用的工具
          reasoningExpanded - 推理区域展开状态
          onToggleReasoning - 点击切换推理展开/折叠
          onContinuePrompt - 点击"继续"按钮的回调
          streamingArtifact - 正在生成的旅行计划产出物
          streamingSubagentEvents - 子代理的实时事件 */}
      <MessageList
        messages={messages}
        streamingMessage={streamingMessage}
        streamingReasoning={streamingReasoning}
        isWaiting={waitingForResponse}
        isThinking={isThinking}
        currentTool={currentTool}
        reasoningExpanded={reasoningExpanded}
        onToggleReasoning={onToggleReasoning}
        onContinuePrompt={onContinuePrompt}
        streamingArtifact={artifactState}
        streamingSubagentEvents={subagentEvents}
      />

      {/* 条件渲染：只有在"没有消息 + 不在等待 + 不在流式输出"三个条件同时满足时，
          才显示 QuickStartPrompts 快捷提示组件
          场景举例：用户刚打开页面，还没有任何对话，显示"上海三日游"、"北京周末游"等预设提示卡片
          && 是 JavaScript 的短路求值：左边为 true 才执行/渲染右边 */}
      {messages.length === 0 && !waitingForResponse && !isStreaming && <QuickStartPrompts onPickPrompt={onPickPrompt} />}

      {/* 条件渲染：有错误信息时显示红色错误提示框
          场景举例：AI 服务异常返回错误，页面底部显示"请求失败，请重试" */}
      {error && (
        <div
          style={{
            color: '#dc2626',
            padding: '14px 18px',
            background: 'linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%)',
            borderRadius: '12px',
            margin: '0 16px 16px',
            border: '1px solid rgba(220, 38, 38, 0.2)',
            boxShadow: '0 2px 8px rgba(220, 38, 38, 0.1)',
          }}
        >
          {error}
        </div>
      )}
      {/* 锚点元素：通过 ref 引用此 div，新消息到达时自动滚动到此处
          场景举例：AI 流式输出新内容时，页面自动滚动到底部，用户始终看到最新回答 */}
      <div ref={messagesEndRef} />
    </>
  );
};

// 导出组件，使其他文件可以通过 import 使用
export default ChatConversationView;
