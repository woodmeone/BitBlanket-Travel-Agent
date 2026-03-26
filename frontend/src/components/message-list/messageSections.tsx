'use client';

import React, { useMemo, useState } from 'react';
import { BulbOutlined, DownOutlined, UpOutlined } from '@ant-design/icons';
import type { Message } from '@/types';
import { MarkdownRenderer } from './markdownRenderer';
import { formatSubagentLabel } from './messageActions';

export const ReasoningBlock: React.FC<{
  reasoning: string;
  messageId: string;
  isExpanded: boolean;
  onToggle: (messageId: string) => void;
  isStreaming?: boolean;
}> = ({ reasoning, messageId, isExpanded, onToggle, isStreaming = false }) => {
  const hasReasoning = Boolean(reasoning);
  const timestampMatch = reasoning.match(/\[Timestamp: ([^\]]+)\]/);
  const timestamp = timestampMatch ? timestampMatch[1] : null;
  const cleaned = useMemo(() => reasoning.replace(/\[Timestamp: [^\]]+\]\n?\n?/g, '').trim(), [reasoning]);

  if (!hasReasoning) return null;

  return (
    <div
      style={{
        marginBottom: '12px',
        background: isStreaming
          ? 'linear-gradient(135deg, #e0f2fe 0%, #f0f9ff 100%)'
          : 'linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%)',
        borderRadius: '12px',
        border: '1px solid rgba(114, 46, 209, 0.15)',
        overflow: 'hidden',
      }}
    >
      <div
        onClick={() => onToggle(messageId)}
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '10px 14px',
          cursor: 'pointer',
          userSelect: 'none',
          background: isStreaming
            ? 'linear-gradient(135deg, #e8f4fd 0%, #dbeafe 100%)'
            : 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
        }}
      >
        <BulbOutlined style={{ color: '#722ed1', marginRight: '8px' }} />
        <span style={{ fontSize: '13px', color: '#1f2937', flex: 1, fontWeight: 500 }}>
          {isStreaming ? '深度思考中...' : '推理过程'}
        </span>
        {timestamp && !isStreaming && (
          <span style={{ fontSize: '11px', color: '#9ca3af', marginRight: '8px' }}>{timestamp}</span>
        )}
        {isExpanded ? <UpOutlined style={{ color: '#722ed1' }} /> : <DownOutlined style={{ color: '#722ed1' }} />}
      </div>

      {isExpanded && (
        <div
          style={{
            padding: '14px',
            background: '#ffffff',
            fontFamily: 'SF Mono, Monaco, Inconsolata, monospace',
            fontSize: '12px',
            lineHeight: 1.8,
            whiteSpace: 'pre-wrap',
            maxHeight: '350px',
            overflow: 'auto',
            color: '#4b5563',
            borderTop: '1px dashed rgba(114, 46, 209, 0.1)',
          }}
        >
          <MarkdownRenderer content={cleaned} />
        </div>
      )}
    </div>
  );
};

export const ThinkBlock: React.FC<{ content: string; isStreaming?: boolean }> = ({ content, isStreaming = false }) => {
  const [expanded, setExpanded] = useState(false);
  if (!content) return null;

  return (
    <div
      style={{
        marginBottom: '12px',
        borderRadius: '12px',
        border: '1px solid rgba(180, 83, 9, 0.2)',
        background: 'linear-gradient(135deg, #fffbeb 0%, #fff7ed 100%)',
        overflow: 'hidden',
      }}
    >
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        style={{
          width: '100%',
          border: 'none',
          background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          cursor: 'pointer',
          padding: '10px 12px',
          color: '#78350f',
          fontSize: '13px',
          fontWeight: 600,
        }}
      >
        <BulbOutlined />
        <span style={{ flex: 1, textAlign: 'left' }}>{isStreaming ? '思考中（可展开）' : '思考过程（可展开）'}</span>
        {expanded ? <UpOutlined /> : <DownOutlined />}
      </button>

      {expanded && (
        <div
          style={{
            padding: '12px',
            borderTop: '1px dashed rgba(180, 83, 9, 0.25)',
            fontSize: '12px',
            color: '#7c2d12',
            lineHeight: 1.7,
            maxHeight: '260px',
            overflow: 'auto',
          }}
        >
          <MarkdownRenderer content={content} />
        </div>
      )}
    </div>
  );
};

export const DiagnosticsPanel: React.FC<{ diagnostics?: Message['diagnostics'] }> = ({ diagnostics }) => {
  if (!diagnostics) return null;

  const toolsUsed = diagnostics.toolsUsed || [];
  const verification = diagnostics.verificationPassed;
  const staleCount = Number(diagnostics.staleResultCount || 0);
  const fallbackSteps = Number(diagnostics.fallbackSteps || 0);
  const artifact = diagnostics.artifact;
  const subagentEvents = diagnostics.subagentEvents || [];

  return (
    <div
      style={{
        marginTop: '10px',
        padding: '10px 12px',
        borderRadius: '10px',
        border: '1px solid rgba(15, 23, 42, 0.08)',
        background: '#f8fafc',
        display: 'grid',
        gap: '6px',
      }}
    >
      <div style={{ fontSize: '12px', color: '#334155' }}>
        验证状态: {verification === null || verification === undefined ? '未知' : verification ? '通过' : '未通过'}
      </div>
      <div style={{ fontSize: '12px', color: '#334155' }}>过期结果: {staleCount} 条</div>
      <div style={{ fontSize: '12px', color: '#334155' }}>备源切换: {fallbackSteps} 次</div>
      <div style={{ fontSize: '12px', color: '#334155', wordBreak: 'break-all' }}>
        工具列表: {toolsUsed.length > 0 ? toolsUsed.join(', ') : '无'}
      </div>
      {artifact?.itinerary.planId && (
        <div style={{ fontSize: '12px', color: '#334155' }}>Artifact 计划ID: {artifact.itinerary.planId}</div>
      )}
      {subagentEvents.length > 0 && (
        <div style={{ fontSize: '12px', color: '#334155' }}>
          子 Agent: {subagentEvents.map((event) => formatSubagentLabel(event.subagent)).join(' → ')}
        </div>
      )}
    </div>
  );
};
