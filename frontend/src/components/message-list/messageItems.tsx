'use client';

import React, { memo, useMemo, useRef } from 'react';
import { Card } from 'antd';
import { RobotOutlined, UserOutlined } from '@ant-design/icons';
import type { Message, SubagentEvent, TripPlanArtifact } from '@/types';
import TravelPlanToolkit from '@/components/TravelPlanToolkit';
import { CopyButton, deriveExportTitle, ExportImageButton, formatSubagentLabel } from './messageActions';
import { extractThinkBlocks, formatThinkContent, MarkdownRenderer } from './markdownRenderer';
import { DiagnosticsPanel, ReasoningBlock, ThinkBlock } from './messageSections';

function MessageAvatar({ isUser }: { isUser: boolean }) {
  return (
    <div
      style={{
        width: '40px',
        height: '40px',
        borderRadius: '50%',
        background: isUser
          ? 'linear-gradient(135deg, #f59e0b 0%, #ef4444 100%)'
          : 'linear-gradient(135deg, #0ea5e9 0%, #14b8a6 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        border: '2px solid rgba(255, 255, 255, 0.9)',
        boxShadow: isUser
          ? '0 8px 18px rgba(239, 68, 68, 0.28)'
          : '0 8px 18px rgba(20, 184, 166, 0.28)',
      }}
    >
      {isUser ? <UserOutlined style={{ color: 'white', fontSize: '18px' }} /> : <RobotOutlined style={{ color: 'white', fontSize: '18px' }} />}
    </div>
  );
}

function StreamingRuntimeCard({
  artifact,
  subagentEvents,
}: {
  artifact?: TripPlanArtifact | null;
  subagentEvents?: SubagentEvent[];
}) {
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
      {artifact?.itinerary.planId && <div style={{ fontSize: '12px', color: '#155e75' }}>Artifact: #{artifact.itinerary.planId}</div>}
      {artifact?.verification.passed !== null && artifact?.verification.passed !== undefined && (
        <div style={{ fontSize: '12px', color: '#155e75' }}>校验: {artifact.verification.passed ? '通过' : '未通过'}</div>
      )}
      {subagentEvents && subagentEvents.length > 0 && (
        <div style={{ fontSize: '12px', color: '#155e75' }}>
          子 Agent: {subagentEvents.map((event) => formatSubagentLabel(event.subagent)).join(' → ')}
        </div>
      )}
    </div>
  );
}

export const MessageItem = memo(function MessageItem({
  msg,
  messageId,
  reasoningExpanded,
  onToggleReasoning,
  onContinuePrompt,
}: {
  msg: Message;
  messageId: string;
  reasoningExpanded: Record<string, boolean>;
  onToggleReasoning: (messageId: string) => void;
  onContinuePrompt?: (prompt: string) => void;
}) {
  const isUser = msg.role === 'user';
  const isExpanded = reasoningExpanded[messageId] ?? false;
  const exportCardRef = useRef<HTMLDivElement>(null);
  const thinkData = useMemo(() => extractThinkBlocks(msg.content), [msg.content]);
  const thinkContent = useMemo(() => formatThinkContent(thinkData.thinkBlocks), [thinkData.thinkBlocks]);
  const visibleMessageContent = thinkData.visibleContent || '';
  const visibleRenderSource = isUser ? msg.content : visibleMessageContent;
  const copySource = isUser ? msg.content : visibleMessageContent || msg.content;
  const exportTitle = useMemo(() => deriveExportTitle(copySource), [copySource]);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: isUser ? 'row-reverse' : 'row',
        justifyContent: 'flex-start',
        marginBottom: '20px',
        alignItems: 'flex-start',
        gap: '14px',
        maxWidth: '100%',
        padding: '0 16px',
      }}
    >
      <MessageAvatar isUser={isUser} />

      <div style={{ flex: 1, maxWidth: 'calc(100% - 52px)' }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '6px', gap: '8px' }}>
          <span style={{ fontSize: '13px', fontWeight: 500, color: isUser ? '#4338ca' : '#262730' }}>{isUser ? '你' : '小帅助手'}</span>
          <span style={{ fontSize: '11px', opacity: 0.6, color: '#999' }}>{msg.timestamp}</span>
        </div>

        <div ref={exportCardRef}>
          <Card
            className="chat-message-card"
            style={{
              background: '#ffffff',
              color: '#1f2937',
              borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
              border: isUser ? '1px solid rgba(239, 68, 68, 0.18)' : '1px solid rgba(0, 0, 0, 0.06)',
              boxShadow: isUser ? '0 4px 16px rgba(239, 68, 68, 0.12)' : '0 2px 12px rgba(0, 0, 0, 0.04)',
            }}
            styles={{ body: { padding: '16px 18px' } }}
          >
            {!isUser && msg.reasoning && (
              <ReasoningBlock
                reasoning={msg.reasoning}
                messageId={messageId}
                isExpanded={isExpanded}
                onToggle={onToggleReasoning}
              />
            )}

            {!isUser && thinkContent && <ThinkBlock content={thinkContent} isStreaming={thinkData.hasUnclosedThink} />}

            <div style={{ lineHeight: 1.7, fontSize: '14px' }}>
              {isUser || visibleMessageContent ? (
                <MarkdownRenderer content={visibleRenderSource} />
              ) : (
                <div style={{ fontSize: '12px', color: '#64748b' }}>已折叠思考过程，正文内容为空。</div>
              )}
            </div>

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

            {!isUser && <DiagnosticsPanel diagnostics={msg.diagnostics} />}
          </Card>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
          {!isUser && (
            <ExportImageButton
              targetRef={exportCardRef}
              filename={`answer-${messageId}`}
              title={exportTitle}
              exportedAt={new Date().toLocaleString('zh-CN', { hour12: false })}
            />
          )}
          <CopyButton content={copySource} />
        </div>
      </div>
    </div>
  );
});

export const StreamingMessageItem = memo(function StreamingMessageItem({
  content,
  reasoning,
  isWaiting = false,
  isThinking = false,
  currentTool = null,
  artifact = null,
  subagentEvents = [],
}: {
  content: string;
  reasoning?: string;
  isWaiting?: boolean;
  isThinking?: boolean;
  currentTool?: string | null;
  artifact?: TripPlanArtifact | null;
  subagentEvents?: SubagentEvent[];
}) {
  const streamingThinkData = useMemo(() => extractThinkBlocks(content), [content]);
  const streamingThinkContent = useMemo(
    () => formatThinkContent(streamingThinkData.thinkBlocks),
    [streamingThinkData.thinkBlocks]
  );
  const visibleStreamingContent = streamingThinkData.visibleContent;
  const hasContent = Boolean(visibleStreamingContent && visibleStreamingContent.length > 0);
  const showReasoning = Boolean(reasoning && reasoning.trim());
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
      <MessageAvatar isUser={false} />

      <div style={{ flex: 1, maxWidth: 'calc(100% - 52px)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
          <span style={{ fontSize: '13px', fontWeight: 500, color: '#1f2937' }}>小帅助手</span>
          <span
            style={{
              fontSize: '11px',
              color: statusColor,
              background: `${statusColor}1A`,
              padding: '2px 10px',
              borderRadius: '10px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: statusColor,
                animation: 'pulse 1.2s infinite',
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
          {!hasContent && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {[0, 1, 2].map((item) => (
                  <span
                    key={item}
                    style={{
                      width: '7px',
                      height: '7px',
                      borderRadius: '50%',
                      background: '#8b5cf6',
                      animation: 'bounce 1.2s infinite ease-in-out both',
                      animationDelay: `${item * 0.16}s`,
                    }}
                  />
                ))}
                <span style={{ fontSize: '13px', color: '#6d28d9' }}>正在分析你的问题，请稍候...</span>
              </div>

              <div style={{ display: 'grid', gap: '8px' }}>
                <span
                  style={{
                    height: '8px',
                    borderRadius: '999px',
                    background: '#eef2ff',
                    animation: 'pulse 1.8s infinite',
                  }}
                />
                <span
                  style={{
                    width: '82%',
                    height: '8px',
                    borderRadius: '999px',
                    background: '#f1f5f9',
                    animation: 'pulse 2s infinite',
                  }}
                />
              </div>
            </div>
          )}

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

          {streamingThinkContent && (
            <ThinkBlock
              content={streamingThinkContent}
              isStreaming={isWaiting || isThinking || streamingThinkData.hasUnclosedThink}
            />
          )}

          {currentTool && (
            <div style={{ marginBottom: hasContent ? '12px' : 0, fontSize: '12px', color: '#92400e' }}>
              工具执行中: {currentTool}
            </div>
          )}

          <StreamingRuntimeCard artifact={artifact} subagentEvents={subagentEvents} />

          {hasContent && (
            <div style={{ lineHeight: 1.7, fontSize: '14px', color: '#1f2937', wordBreak: 'break-word' }}>
              <MarkdownRenderer content={visibleStreamingContent} />
              {(isWaiting || isThinking) && (
                <span
                  style={{
                    display: 'inline-block',
                    width: '2px',
                    height: '16px',
                    background: '#2563eb',
                    marginLeft: '2px',
                    animation: 'blink 0.8s infinite',
                  }}
                />
              )}
            </div>
          )}
        </Card>

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
          <CopyButton content={hasContent ? visibleStreamingContent : '小帅助手正在思考中...'} />
        </div>
      </div>
    </div>
  );
});
