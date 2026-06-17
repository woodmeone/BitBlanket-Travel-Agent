/* 【核心】消息条目组件模块 —— 定义单条聊天消息的完整渲染，包括头像、内容卡片、操作按钮等 */
/* 这是消息列表中最核心的组件，负责把一条消息数据渲染成可视化的聊天气泡 */
'use client';

/* memo：React 性能优化钩子，只有当传入的参数变化时才重新渲染组件 */
/* useMemo：缓存计算结果，避免重复计算 */
/* useRef：创建一个"引用"，可以持久化地指向一个 DOM 元素或值，不会因渲染而重置 */
import React, { memo, useMemo, useRef } from 'react';
/* Card：ant-design 的卡片组件，用于包裹消息内容 */
import { Card } from 'antd';
/* 机器人图标和用户图标，用于区分 AI 和用户的消息 */
import { RobotOutlined, UserOutlined } from '@ant-design/icons';
/* 导入类型定义 */
import type { Message, SubagentEvent, TripPlanArtifact } from '@/types';
/* 旅行方案工具栏组件，提供方案相关的操作按钮 */
import TravelPlanToolkit from '@/components/TravelPlanToolkit';
/* 导入消息操作相关组件和函数 */
import { CopyButton, deriveExportTitle, ExportImageButton, formatSubagentLabel } from './messageActions';
/* 导入 Markdown 渲染器和思考内容提取函数 */
import { extractThinkBlocks, formatThinkContent, MarkdownRenderer } from './markdownRenderer';
/* 导入消息区段子组件（推理区块、思考区块、诊断面板） */
import { DiagnosticsPanel, ReasoningBlock, ThinkBlock } from './messageSections';

/* 【核心】消息头像组件 —— 根据是否为用户消息显示不同的头像和颜色 */
/* isUser=true 显示用户头像（橙红渐变），isUser=false 显示 AI 头像（蓝绿渐变） */
function MessageAvatar({ isUser }: { isUser: boolean }) {
  return (
    <div
      style={{
        width: '40px',
        height: '40px',
        borderRadius: '50%',    /* 圆形头像 */
        /* 用户头像用橙红渐变，AI 头像用蓝绿渐变 */
        background: isUser
          ? 'linear-gradient(135deg, #f59e0b 0%, #ef4444 100%)'
          : 'linear-gradient(135deg, #0ea5e9 0%, #14b8a6 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,  /* 不允许头像被压缩 */
        border: '2px solid rgba(255, 255, 255, 0.9)',
        /* 用户头像用红色阴影，AI 头像用青色阴影 */
        boxShadow: isUser
          ? '0 8px 18px rgba(239, 68, 68, 0.28)'
          : '0 8px 18px rgba(20, 184, 166, 0.28)',
      }}
    >
      {/* 用户显示人形图标，AI 显示机器人图标 */}
      {isUser ? <UserOutlined style={{ color: 'white', fontSize: '18px' }} /> : <RobotOutlined style={{ color: 'white', fontSize: '18px' }} />}
    </div>
  );
}

/* 流式输出运行时卡片 —— 在 AI 正在生成回答时，展示当前的运行状态信息 */
/* 应用场景：AI 正在调用多个子 Agent 协作生成旅行方案时，实时展示进度 */
/* 例如："Artifact: #plan-123"、"校验: 通过"、"子 Agent: 规划 → 研究" */
function StreamingRuntimeCard({
  artifact,
  subagentEvents,
}: {
  artifact?: TripPlanArtifact | null;     // 旅行方案产物
  subagentEvents?: SubagentEvent[];      // 子 Agent 执行事件
}) {
  /* 如果没有产物也没有子 Agent 事件，不渲染 */
  if (!artifact && (!subagentEvents || subagentEvents.length === 0)) return null;

  return (
    <div
      style={{
        marginBottom: '12px',
        padding: '10px 12px',
        borderRadius: '12px',
        background: 'linear-gradient(135deg, #ecfeff 0%, #f8fafc 100%)',
        border: '1px solid rgba(8, 145, 178, 0.15)',
        display: 'grid',
        gap: '4px',
      }}
    >
      {/* 显示旅行方案的计划 ID */}
      {artifact?.itinerary.planId && <div style={{ fontSize: '12px', color: '#155e75' }}>Artifact: #{artifact.itinerary.planId}</div>}
      {/* 显示验证结果 */}
      {artifact?.verification.passed !== null && artifact?.verification.passed !== undefined && (
        <div style={{ fontSize: '12px', color: '#155e75' }}>校验: {artifact.verification.passed ? '通过' : '未通过'}</div>
      )}
      {/* 显示子 Agent 执行流程 */}
      {subagentEvents && subagentEvents.length > 0 && (
        <div style={{ fontSize: '12px', color: '#155e75' }}>
          子 Agent: {subagentEvents.map((event) => formatSubagentLabel(event.subagent)).join(' → ')}
        </div>
      )}
    </div>
  );
}

/* 【核心】消息条目组件 —— 渲染一条完整的聊天消息（用户消息或 AI 消息） */
/* 应用场景：聊天界面中的每一条消息都由这个组件渲染 */
/* 用 memo 包裹是为了性能优化：只有当消息内容变化时才重新渲染 */
/* 例如：用户发送"帮我规划东京3日游"，AI 回复旅行方案，这两条消息分别渲染为两个 MessageItem */
export const MessageItem = memo(function MessageItem({
  msg,                    // 消息数据对象
  messageId,              // 消息唯一标识
  reasoningExpanded,      // 各消息的推理区块展开状态（键值对：消息ID → 是否展开）
  onToggleReasoning,      // 切换推理区块展开/折叠的回调函数
  onContinuePrompt,       // 继续对话的回调函数（用于旅行方案工具栏的"继续追问"功能）
}: {
  msg: Message;
  messageId: string;
  reasoningExpanded: Record<string, boolean>;
  onToggleReasoning: (messageId: string) => void;
  onContinuePrompt?: (prompt: string) => void;
}) {
  /* 判断是否为用户消息 */
  const isUser = msg.role === 'user';
  /* 获取当前消息的推理区块展开状态，默认折叠 */
  const isExpanded = reasoningExpanded[messageId] ?? false;
  /* 创建一个 DOM 引用，指向消息卡片元素，用于导出图片时截图 */
  const exportCardRef = useRef<HTMLDivElement>(null);
  /* 【核心】从消息内容中提取思考块（<think>...</think>标签包裹的内容） */
  /* extractThinkBlocks 会把消息内容分成"可见内容"和"思考内容"两部分 */
  const thinkData = useMemo(() => extractThinkBlocks(msg.content), [msg.content]);
  /* 将多个思考块合并为一段文本，用分隔线连接 */
  const thinkContent = useMemo(() => formatThinkContent(thinkData.thinkBlocks), [thinkData.thinkBlocks]);
  /* 可见内容：去掉思考标签后的消息正文 */
  const visibleMessageContent = thinkData.visibleContent || '';
  /* 用户消息直接显示原始内容，AI 消息显示去掉思考标签后的可见内容 */
  const visibleRenderSource = isUser ? msg.content : visibleMessageContent;
  /* 复制源：用户消息复制原始内容，AI 消息复制可见内容（如果没有可见内容则复制原始内容） */
  const copySource = isUser ? msg.content : visibleMessageContent || msg.content;
  /* 推导导出图片的标题 */
  const exportTitle = useMemo(() => deriveExportTitle(copySource), [copySource]);

  return (
    <div
      style={{
        display: 'flex',
        /* 用户消息靠右（row-reverse 反转排列方向），AI 消息靠左 */
        flexDirection: isUser ? 'row-reverse' : 'row',
        justifyContent: 'flex-start',
        marginBottom: '20px',
        alignItems: 'flex-start',
        gap: '14px',
        maxWidth: '100%',
        padding: '0 16px',
      }}
    >
      {/* 头像 */}
      <MessageAvatar isUser={isUser} />

      {/* 消息内容区域 */}
      <div style={{ flex: 1, maxWidth: 'calc(100% - 52px)' }}>
        {/* 发送者名称和时间 */}
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '6px', gap: '8px' }}>
          <span style={{ fontSize: '13px', fontWeight: 500, color: isUser ? '#4338ca' : '#262730' }}>{isUser ? '你' : '放心游助手'}</span>
          <span style={{ fontSize: '11px', opacity: 0.6, color: '#999' }}>{msg.timestamp}</span>
        </div>

        {/* 消息卡片（用于导出图片时截图的目标区域） */}
        <div ref={exportCardRef}>
          <Card
            className="chat-message-card"
            style={{
              background: '#ffffff',
              color: '#1f2937',
              /* 用户消息右下角圆角小（4px），AI 消息左下角圆角小，形成聊天气泡效果 */
              borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
              border: isUser ? '1px solid rgba(239, 68, 68, 0.18)' : '1px solid rgba(0, 0, 0, 0.06)',
              boxShadow: isUser ? '0 4px 16px rgba(239, 68, 68, 0.12)' : '0 2px 12px rgba(0, 0, 0, 0.04)',
            }}
            styles={{ body: { padding: '16px 18px' } }}
          >
            {/* AI 消息才显示推理区块 */}
            {!isUser && msg.reasoning && (
              <ReasoningBlock
                reasoning={msg.reasoning}
                messageId={messageId}
                isExpanded={isExpanded}
                onToggle={onToggleReasoning}
              />
            )}

            {/* AI 消息才显示思考区块 */}
            {!isUser && thinkContent && <ThinkBlock content={thinkContent} isStreaming={thinkData.hasUnclosedThink} />}

            {/* 消息正文内容 */}
            <div style={{ lineHeight: 1.7, fontSize: '14px' }}>
              {/* 如果是用户消息，或者有可见内容，则用 Markdown 渲染器展示 */}
              {isUser || visibleMessageContent ? (
                <MarkdownRenderer content={visibleRenderSource} />
              ) : (
                /* 如果 AI 消息只有思考内容没有可见正文，显示提示文字 */
                <div style={{ fontSize: '12px', color: '#64748b' }}>已折叠思考过程，正文内容为空。</div>
              )}
            </div>

            {/* AI 消息才显示旅行方案工具栏 */}
            {!isUser && (
              <TravelPlanToolkit
                messageId={messageId}
                content={visibleMessageContent}
                diagnostics={msg.diagnostics}
                artifact={msg.diagnostics?.artifact}
                subagentEvents={msg.diagnostics?.subagentEvents}
                onContinuePrompt={onContinuePrompt}
              />
            )}

            {/* AI 消息才显示诊断面板 */}
            {!isUser && <DiagnosticsPanel diagnostics={msg.diagnostics} />}
          </Card>
        </div>

        {/* 操作按钮区域（复制、导出图片） */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
          {/* AI 消息才显示导出图片按钮 */}
          {!isUser && (
            <ExportImageButton
              targetRef={exportCardRef}
              filename={`answer-${messageId}`}
              title={exportTitle}
              exportedAt={new Date().toLocaleString('zh-CN', { hour12: false })}
            />
          )}
          {/* 所有消息都显示复制按钮 */}
          <CopyButton content={copySource} />
        </div>
      </div>
    </div>
  );
});

/* 【核心】流式消息条目组件 —— 渲染 AI 正在生成中的消息（实时流式输出） */
/* 应用场景：当 AI 正在逐字生成回答时，用这个组件实时展示生成过程 */
/* 与 MessageItem 的区别：MessageItem 展示已完成的消息，StreamingMessageItem 展示正在生成的消息 */
/* 例如：AI 回答"东京3日游攻略如下：\n第一天..."，文字会一个一个地出现，就是流式输出 */
export const StreamingMessageItem = memo(function StreamingMessageItem({
  content,                // 当前已生成的消息内容（会不断更新）
  reasoning,              // 当前已生成的推理内容
  isWaiting = false,      // 是否正在等待 AI 响应
  isThinking = false,     // AI 是否正在思考中
  currentTool = null,     // 当前正在执行的工具名称
  artifact = null,        // 当前生成的旅行方案产物
  subagentEvents = [],    // 子 Agent 执行事件列表
}: {
  content: string;
  reasoning?: string;
  isWaiting?: boolean;
  isThinking?: boolean;
  currentTool?: string | null;
  artifact?: TripPlanArtifact | null;
  subagentEvents?: SubagentEvent[];
}) {
  /* 从流式内容中提取思考块 */
  const streamingThinkData = useMemo(() => extractThinkBlocks(content), [content]);
  const streamingThinkContent = useMemo(
    () => formatThinkContent(streamingThinkData.thinkBlocks),
    [streamingThinkData.thinkBlocks]
  );
  /* 可见的流式内容（去掉思考标签后的正文） */
  const visibleStreamingContent = streamingThinkData.visibleContent;
  /* 是否有可见内容 */
  const hasContent = Boolean(visibleStreamingContent && visibleStreamingContent.length > 0);
  /* 是否显示推理区块 */
  const showReasoning = Boolean(reasoning && reasoning.trim());
  /* 根据当前状态确定状态标签文字和颜色 */
  /* 有内容→"生成中"（蓝色），思考中→"思考中"（紫色），否则→"等待响应"（紫色） */
  const statusLabel = hasContent ? '生成中' : isThinking ? '思考中' : '等待响应';
  const statusColor = hasContent ? '#2563eb' : '#7c3aed';

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'row',
        justifyContent: 'flex-start',
        marginBottom: '16px',
        alignItems: 'flex-start',
        gap: '12px',
        maxWidth: '100%',
        padding: '0 16px',
      }}
    >
      {/* AI 头像 */}
      <MessageAvatar isUser={false} />

      <div style={{ flex: 1, maxWidth: 'calc(100% - 52px)' }}>
        {/* 名称和状态标签 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
          <span style={{ fontSize: '13px', fontWeight: 500, color: '#1f2937' }}>放心游助手</span>
          {/* 状态标签：带脉冲动画的圆点 + 状态文字 */}
          <span
            style={{
              fontSize: '11px',
              color: statusColor,
              background: `${statusColor}1A`,  /* 1A 是16进制透明度，约10%不透明度 */
              padding: '2px 10px',
              borderRadius: '10px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            {/* 脉冲动画圆点，表示正在工作中 */}
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: statusColor,
                animation: 'pulse 1.2s infinite',  /* CSS 动画：1.2秒循环脉冲 */
              }}
            />
            {statusLabel}
          </span>
        </div>

        <Card
          className="chat-message-card"
          style={{
            background: '#ffffff',
            color: '#1f2937',
            borderRadius: '18px 18px 18px 4px',
            border: '1px solid rgba(0, 0, 0, 0.06)',
            boxShadow: '0 2px 12px rgba(0, 0, 0, 0.04)',
          }}
          styles={{ body: { padding: '16px 18px' } }}
        >
          {/* 没有内容时显示加载动画（三个跳动的圆点 + 骨架屏） */}
          {!hasContent && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {/* 三个跳动的紫色圆点，表示正在加载 */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {[0, 1, 2].map((item) => (
                  <span
                    key={item}
                    style={{
                      width: '7px',
                      height: '7px',
                      borderRadius: '50%',
                      background: '#8b5cf6',
                      animation: 'bounce 1.2s infinite ease-in-out both',  /* 弹跳动画 */
                      animationDelay: `${item * 0.16}s`,  /* 每个圆点延迟0.16秒，形成波浪效果 */
                    }}
                  />
                ))}
                <span style={{ fontSize: '13px', color: '#6d28d9' }}>正在分析你的问题，请稍候...</span>
              </div>

              {/* 骨架屏：模拟内容加载的灰色条形占位符 */}
              <div style={{ display: 'grid', gap: '8px' }}>
                <span
                  style={{
                    height: '8px',
                    borderRadius: '999px',
                    background: '#eef2ff',
                    animation: 'pulse 1.8s infinite',  /* 脉冲动画，表示正在加载 */
                  }}
                />
                <span
                  style={{
                    width: '82%',     /* 第二行稍短，模拟真实文本长度差异 */
                    height: '8px',
                    borderRadius: '999px',
                    background: '#f1f5f9',
                    animation: 'pulse 2s infinite',
                  }}
                />
              </div>
            </div>
          )}

          {/* 显示推理过程（如果有） */}
          {showReasoning && (
            <div
              style={{
                marginBottom: hasContent ? '12px' : 0,
                padding: '10px 12px',
                borderRadius: '12px',
                background: 'linear-gradient(135deg, #eef2ff 0%, #f5f3ff 100%)',
                border: '1px solid rgba(124, 58, 237, 0.14)',
              }}
            >
              <div style={{ fontSize: '12px', color: '#6d28d9', marginBottom: '6px', fontWeight: 500 }}>思考过程</div>
              <div
                style={{
                  fontSize: '12px',
                  color: '#4c1d95',
                  lineHeight: 1.65,
                  maxHeight: '120px',
                  overflow: 'auto',
                }}
              >
                <MarkdownRenderer content={reasoning || ''} />
              </div>
            </div>
          )}

          {/* 显示思考区块（如果有） */}
          {streamingThinkContent && (
            <ThinkBlock
              content={streamingThinkContent}
              isStreaming={isWaiting || isThinking || streamingThinkData.hasUnclosedThink}
            />
          )}

          {/* 显示当前正在执行的工具名称 */}
          {currentTool && (
            <div style={{ marginBottom: hasContent ? '12px' : 0, fontSize: '12px', color: '#92400e' }}>
              工具执行中: {currentTool}
            </div>
          )}

          {/* 显示运行时卡片（Artifact 和子 Agent 信息） */}
          <StreamingRuntimeCard artifact={artifact} subagentEvents={subagentEvents} />

          {/* 有可见内容时，用 Markdown 渲染器展示 */}
          {hasContent && (
            <div style={{ lineHeight: 1.7, fontSize: '14px', color: '#1f2937', wordBreak: 'break-word' }}>
              <MarkdownRenderer content={visibleStreamingContent} />
              {/* 流式输出时显示闪烁的光标，模拟打字效果 */}
              {(isWaiting || isThinking) && (
                <span
                  style={{
                    display: 'inline-block',
                    width: '2px',
                    height: '16px',
                    background: '#2563eb',
                    marginLeft: '2px',
                    animation: 'blink 0.8s infinite',  /* 闪烁动画 */
                  }}
                />
              )}
            </div>
          )}
        </Card>

        {/* 复制按钮 */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
          {/* 有内容时复制可见内容，否则复制提示文字 */}
          <CopyButton content={hasContent ? visibleStreamingContent : '放心游助手正在思考中...'} />
        </div>
      </div>
    </div>
  );
});
