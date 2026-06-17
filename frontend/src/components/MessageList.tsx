// 'use client' 是 Next.js 的标记，表示这个组件在浏览器端运行（而非服务器端渲染）
'use client';

// 从 react 库导入 React 核心对象和 useMemo（缓存计算结果的钩子函数）
import React, { useMemo } from 'react';
// 从项目类型定义文件导入三种类型：Message（聊天消息）、SubagentEvent（子代理事件）、TripPlanArtifact（旅行计划产物）
import type { Message, SubagentEvent, TripPlanArtifact } from '@/types';
// 从子目录导入两个消息展示组件：MessageItem（完整消息项）、StreamingMessageItem（流式输出消息项）
import { MessageItem, StreamingMessageItem } from './message-list/messageItems';

// interface 是 TypeScript 定义对象类型的语法，描述一个对象应该有哪些字段
// Props 定义了 MessageList 组件接收的所有属性（即父组件传给它的数据）
interface Props {
  messages: Message[];                           // 聊天消息数组，包含所有已完成的对话消息
  streamingMessage?: string;                     // 正在流式输出的消息内容（? 表示可选属性，可以不传）
  streamingReasoning?: string;                   // 正在流式输出的推理过程内容（AI思考过程的文字）
  isWaiting?: boolean;                           // 是否正在等待AI响应（显示加载状态）
  isThinking?: boolean;                          // AI是否正在思考（显示思考中状态）
  currentTool?: string | null;                   // 当前正在调用的工具名称，如"搜索酒店"（null表示无工具调用）
  reasoningExpanded?: Record<string, boolean>;   // 记录每条消息的推理区域是否展开，键是消息ID，值是展开状态
  onToggleReasoning?: (messageId: string) => void; // 点击展开/折叠推理区域的回调函数，参数为消息ID
  onContinuePrompt?: (prompt: string) => void;   // 继续对话的回调函数，例如用户点击"换个方案"时触发
  streamingArtifact?: TripPlanArtifact | null;   // 正在流式生成的旅行计划产物（如行程方案）
  streamingSubagentEvents?: SubagentEvent[];     // 正在流式输出的子代理事件列表（如"正在搜索机票"等子任务进度）
}

// React.FC<Props> 是 React 函数组件的类型写法，FC = Function Component
// 尖括号里的 Props 指定该组件接收的属性类型
// = ({ ... }) 是 props 解构：直接从传入的属性对象中取出各个字段，避免反复写 props.xxx
const MessageList: React.FC<Props> = ({
  messages,                      // 所有聊天消息
  streamingMessage,              // 流式消息内容
  streamingReasoning,            // 流式推理内容
  isWaiting = false,             // = false 是默认值，父组件不传时默认为 false
  isThinking = false,            // 默认不处于思考状态
  currentTool = null,            // 默认无工具调用
  reasoningExpanded = {},        // 默认所有推理区域都折叠
  onToggleReasoning,             // 推理区域展开/折叠回调
  onContinuePrompt,              // 继续对话回调
  streamingArtifact,             // 流式旅行计划产物
  streamingSubagentEvents = [],  // 默认子代理事件为空数组
}) => {
  // 【核心】如果父组件没有传 onToggleReasoning，则提供一个空函数作为兜底
  // 这样后续调用 toggleHandler() 时不会因 undefined 而报错
  const toggleHandler = onToggleReasoning || (() => {});

  // 【核心】useMemo 是 React 的缓存钩子：只有当依赖项变化时才重新计算，否则复用上次结果
  // 这里缓存的是消息列表的渲染结果，避免每次组件重渲染都重新遍历所有消息
  // 应用场景：当用户输入新消息时，只有 messages 变化才会重新渲染列表，其他状态变化不会触发
  const renderedMessages = useMemo(
    () =>
      // 遍历所有消息，为每条消息生成对应的 MessageItem 组件
      messages.map((msg, index) => {
        // 用消息时间戳+索引拼接唯一ID，作为 React 的 key（帮助 React 高效更新列表）
        const messageId = `msg_${msg.timestamp}_${index}`;

        return (
          <MessageItem
            key={messageId}              // React 列表渲染必须的 key，用于标识每项
            msg={msg}                     // 当前消息对象
            messageId={messageId}         // 消息唯一ID
            reasoningExpanded={reasoningExpanded}  // 推理区域展开状态
            onToggleReasoning={toggleHandler}      // 展开/折叠推理的回调
            onContinuePrompt={onContinuePrompt}    // 继续对话的回调
          />
        );
      }),
    // 依赖数组：只有这些值变化时才重新计算 renderedMessages
    [messages, reasoningExpanded, toggleHandler, onContinuePrompt]
  );

  // 【核心】判断是否需要显示流式输出对话框
  // 满足以下任一条件即显示：
  //   1. 正在等待AI响应（isWaiting）
  //   2. AI正在思考（isThinking）
  //   3. 有流式消息内容且非空（streamingMessage）
  //   4. 有流式推理内容且非空（streamingReasoning）
  // 应用场景：用户发送"帮我规划三亚5日游"后，AI开始思考和输出，此时底部出现流式对话框
  const shouldShowStreamingDialog =
    isWaiting ||
    isThinking ||
    Boolean(streamingMessage && streamingMessage.length > 0) ||
    Boolean(streamingReasoning && streamingReasoning.length > 0);

  return (
    // 最外层容器，限制最大宽度900px并居中，保证聊天区域不会过宽
    <div className="chat-message-container" style={{ maxWidth: '900px', margin: '0 auto', width: '100%' }}>
      {/* 已完成的消息列表 */}
      {renderedMessages}

      {/* 条件渲染：只有 shouldShowStreamingDialog 为 true 时才显示流式消息组件 */}
      {/* && 是 React 中条件渲染的常见写法：条件为真时渲染右侧组件，为假时不渲染 */}
      {shouldShowStreamingDialog && (
        <StreamingMessageItem
          content={streamingMessage || ''}           // 流式消息内容，无内容时传空字符串
          reasoning={streamingReasoning}              // 流式推理内容
          isWaiting={isWaiting}                       // 是否等待中
          isThinking={isThinking}                     // 是否思考中
          currentTool={currentTool}                   // 当前调用的工具名
          artifact={streamingArtifact}                // 流式旅行计划产物
          subagentEvents={streamingSubagentEvents}    // 子代理事件列表
        />
      )}
    </div>
  );
};

// export default 表示这是模块的默认导出，其他文件 import 时可以直接写 import MessageList from '...'
export default MessageList;
