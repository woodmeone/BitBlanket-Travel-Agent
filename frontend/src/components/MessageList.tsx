'use client';

import React, { memo, useMemo, useRef, useState } from 'react';
import { App, Card } from 'antd';
import {
  BulbOutlined,
  CheckOutlined,
  CopyOutlined,
  DownOutlined,
  FileImageOutlined,
  RobotOutlined,
  UpOutlined,
  UserOutlined,
} from '@ant-design/icons';
import html2canvas from 'html2canvas';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Message } from '@/types';
import TravelPlanToolkit from './TravelPlanToolkit';

interface Props {
  messages: Message[];
  streamingMessage?: string;
  streamingReasoning?: string;
  isWaiting?: boolean;
  isThinking?: boolean;
  currentTool?: string | null;
  reasoningExpanded?: Record<string, boolean>;
  onToggleReasoning?: (messageId: string) => void;
  onContinuePrompt?: (prompt: string) => void;
}

function normalizeInlinePseudoTables(input: string): string {
  const lines = input.split('\n');

  return lines
    .map((line) => {
      const raw = line.trim();
      if (!raw.includes('|')) return line;

      const firstPipeIndex = raw.indexOf('|');
      const prefix = firstPipeIndex > 0 ? raw.slice(0, firstPipeIndex).trim() : '';
      const tableCandidate = raw.slice(firstPipeIndex).trim();

      const pipeCount = (tableCandidate.match(/\|/g) || []).length;
      const hasSeparator = /\|\s*:?-{3,}:?\s*\|/.test(tableCandidate);
      const hasInlineRowJoin = /\|\s+\|/.test(tableCandidate);

      if (pipeCount < 6 || (!hasSeparator && !hasInlineRowJoin)) return line;

      const normalizedTable = tableCandidate
        .replace(/\|\s+\|(?=\s*[:\-]{3,}|[^\n|])/g, '|\n|')
        .replace(/\n{2,}/g, '\n')
        .trim();

      if (!normalizedTable.includes('\n|')) return line;
      return prefix ? `${prefix}\n${normalizedTable}` : normalizedTable;
    })
    .join('\n');
}

function normalizeLooseTableBlocks(input: string): string {
  const lines = input.split('\n');
  const output: string[] = [];

  for (let index = 0; index < lines.length; index += 1) {
    const currentLine = lines[index].trim();
    const nextLine = lines[index + 1]?.trim() || '';

    const hasHeaderLikePipes = currentLine.startsWith('|') && currentLine.endsWith('|');
    const hasSeparatorLikeLine = /^\|?\s*:?-{3,}:?(\s*\|\s*:?-{3,}:?)+\s*\|?$/.test(nextLine);

    if (!hasHeaderLikePipes || !hasSeparatorLikeLine) {
      output.push(lines[index]);
      continue;
    }

    output.push(lines[index]);

    if (!nextLine.startsWith('|')) {
      output.push(`| ${nextLine.replace(/^\|?\s*/, '').replace(/\s*\|?$/, '')} |`);
    } else {
      output.push(lines[index + 1]);
    }

    index += 1;
  }

  return output.join('\n');
}

function normalizeHtmlBreaks(input: string): string {
  return input.replace(/<br\s*\/?>/gi, '\n');
}

function normalizePseudoSeparators(input: string): string {
  return input
    .split('\n')
    .map((line) => {
      const raw = line.trim();
      if (!raw) return line;

      if (/^\|{2,}[\-|｜| ]+\|{1,}$/.test(raw) || /^[\-|｜ ]{8,}$/.test(raw)) {
        return '';
      }

      return line
        .replace(/\|\|\s*/g, ' ')
        .replace(/\s*\|\|/g, ' ')
        .replace(/\s*[|｜]\s*/g, ' | ')
        .replace(/\s{2,}/g, ' ')
        .trimEnd();
    })
    .filter((line, index, lines) => !(line === '' && lines[index - 1] === ''))
    .join('\n');
}

function normalizeEvidenceBlocks(input: string): string {
  return input.replace(/(证据来源\s*\n(?:\|.*\n)+)(?!\n)/g, '$1\n');
}

function cleanContent(content: string): string {
  if (!content) return '';

  const normalized = content
    .replace(/\r\n?/g, '\n')
    .replace(/\u00a0/g, ' ')
    .replace(/[ \t]+$/gm, '');

  return normalizeEvidenceBlocks(
    normalizeLooseTableBlocks(normalizeInlinePseudoTables(normalizePseudoSeparators(normalizeHtmlBreaks(normalized))))
  ).trim();
}

const markdownComponents: Components = {
  p: ({ children }) => <p style={{ margin: 0, padding: 0 }}>{children}</p>,
  li: ({ children }) => <li style={{ margin: 0, padding: 0, lineHeight: 1.6 }}>{children}</li>,
  h1: ({ children }) => (
    <h1 style={{ margin: '4px 0 2px 0', fontSize: '1.5em', fontWeight: 600 }}>{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 style={{ margin: '4px 0 2px 0', fontSize: '1.3em', fontWeight: 600 }}>{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 style={{ margin: '4px 0 2px 0', fontSize: '1.1em', fontWeight: 600 }}>{children}</h3>
  ),
  ol: ({ children }) => <ol style={{ margin: '2px 0', paddingLeft: '20px' }}>{children}</ol>,
  ul: ({ children }) => <ul style={{ margin: '2px 0', paddingLeft: '20px' }}>{children}</ul>,
  table: ({ children }) => (
    <div style={{ overflowX: 'auto', margin: '8px 0' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th
      style={{
        border: '1px solid #e5e7eb',
        background: '#f8fafc',
        padding: '6px 8px',
        textAlign: 'left',
      }}
    >
      {children}
    </th>
  ),
  td: ({ children }) => <td style={{ border: '1px solid #e5e7eb', padding: '6px 8px' }}>{children}</td>,
  code: ({ children }) => (
    <code
      style={{
        background: '#f3f4f6',
        borderRadius: '4px',
        padding: '1px 4px',
        fontFamily: 'SF Mono, Monaco, Consolas, monospace',
        fontSize: '12px',
      }}
    >
      {children}
    </code>
  ),
};

function deriveExportTitle(content: string): string {
  const firstMeaningfulLine = cleanContent(content)
    .split('\n')
    .map((line) => line.trim())
    .find((line) => line && !line.startsWith('|') && !line.startsWith('-') && !line.startsWith('>'));

  if (!firstMeaningfulLine) return '旅行方案分享';
  const normalized = firstMeaningfulLine.replace(/^#+\s*/, '').slice(0, 28).trim();
  return normalized || '旅行方案分享';
}

const CopyButton: React.FC<{ content: string }> = ({ content }) => {
  const [copied, setCopied] = useState(false);
  const { message } = App.useApp();

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      message.success('已复制到剪贴板');
      setTimeout(() => setCopied(false), 1500);
    } catch {
      message.error('复制失败，请手动复制');
    }
  }

  return (
    <button
      onClick={handleCopy}
      title={copied ? '已复制' : '复制'}
      style={{
        background: 'transparent',
        border: 'none',
        cursor: 'pointer',
        padding: '4px 8px',
        borderRadius: '4px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: copied ? '#52c41a' : 'inherit',
        transition: 'all 0.2s ease',
      }}
    >
      {copied ? (
        <CheckOutlined style={{ fontSize: '14px' }} />
      ) : (
        <CopyOutlined style={{ fontSize: '14px' }} />
      )}
    </button>
  );
};

const ExportImageButton: React.FC<{
  targetRef: React.RefObject<HTMLDivElement | null>;
  filename: string;
  title: string;
  exportedAt: string;
}> = ({ targetRef, filename, title, exportedAt }) => {
  const [exporting, setExporting] = useState(false);
  const { message } = App.useApp();

  async function handleExport() {
    if (!targetRef.current || exporting) return;

    let exportShell: HTMLDivElement | null = null;

    try {
      setExporting(true);
      exportShell = document.createElement('div');
      exportShell.style.position = 'fixed';
      exportShell.style.left = '-10000px';
      exportShell.style.top = '0';
      exportShell.style.width = '920px';
      exportShell.style.padding = '28px';
      exportShell.style.background = 'linear-gradient(180deg, #f8fbff 0%, #ffffff 28%, #f8fafc 100%)';
      exportShell.style.boxSizing = 'border-box';

      const header = document.createElement('div');
      header.style.display = 'flex';
      header.style.justifyContent = 'space-between';
      header.style.alignItems = 'center';
      header.style.gap = '16px';
      header.style.padding = '18px 20px';
      header.style.marginBottom = '18px';
      header.style.borderRadius = '20px';
      header.style.background = 'linear-gradient(135deg, #082f49 0%, #0f766e 100%)';
      header.style.color = '#ffffff';

      const brand = document.createElement('div');
      brand.style.display = 'flex';
      brand.style.alignItems = 'center';
      brand.style.gap = '12px';

      const logo = document.createElement('div');
      logo.textContent = 'ST';
      logo.style.width = '42px';
      logo.style.height = '42px';
      logo.style.display = 'flex';
      logo.style.alignItems = 'center';
      logo.style.justifyContent = 'center';
      logo.style.borderRadius = '12px';
      logo.style.background = 'rgba(255,255,255,0.16)';
      logo.style.fontWeight = '700';
      logo.style.fontSize = '16px';

      const brandText = document.createElement('div');
      const brandTitle = document.createElement('div');
      brandTitle.textContent = 'Shuai Travel Agent';
      brandTitle.style.fontSize = '16px';
      brandTitle.style.fontWeight = '700';
      const brandSubtitle = document.createElement('div');
      brandSubtitle.textContent = '\u0041\u0049 \u65c5\u884c\u65b9\u6848\u5206\u4eab\u5361';
      brandSubtitle.style.fontSize = '12px';
      brandSubtitle.style.opacity = '0.82';
      brandText.appendChild(brandTitle);
      brandText.appendChild(brandSubtitle);

      brand.appendChild(logo);
      brand.appendChild(brandText);

      const meta = document.createElement('div');
      meta.style.textAlign = 'right';
      const metaTitle = document.createElement('div');
      metaTitle.textContent = title;
      metaTitle.style.fontSize = '18px';
      metaTitle.style.fontWeight = '700';
      const metaTime = document.createElement('div');
      metaTime.textContent = `\u5bfc\u51fa\u65f6\u95f4 ${exportedAt}`;
      metaTime.style.fontSize = '12px';
      metaTime.style.opacity = '0.82';
      meta.appendChild(metaTitle);
      meta.appendChild(metaTime);

      header.appendChild(brand);
      header.appendChild(meta);

      const clonedCard = targetRef.current.cloneNode(true) as HTMLDivElement;
      clonedCard.style.maxWidth = '100%';

      exportShell.appendChild(header);
      exportShell.appendChild(clonedCard);
      document.body.appendChild(exportShell);

      const canvas = await html2canvas(exportShell, {
        scale: 2,
        backgroundColor: '#f8fbff',
        useCORS: true,
      });
      const link = document.createElement('a');
      link.href = canvas.toDataURL('image/png');
      link.download = `${filename}.png`;
      link.click();
      message.success('\u56de\u7b54\u5df2\u5bfc\u51fa\u4e3a\u56fe\u7247');
    } catch {
      message.error('\u5bfc\u51fa\u56fe\u7247\u5931\u8d25\uff0c\u8bf7\u91cd\u8bd5');
    } finally {
      if (exportShell?.parentNode) exportShell.parentNode.removeChild(exportShell);
      setExporting(false);
    }
  }

  return (
    <button
      onClick={handleExport}
      title={exporting ? '\u5bfc\u51fa\u4e2d' : '\u5bfc\u51fa\u56fe\u7247'}
      style={{
        background: 'transparent',
        border: 'none',
        cursor: exporting ? 'wait' : 'pointer',
        padding: '4px 8px',
        borderRadius: '4px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: exporting ? '#2563eb' : 'inherit',
        transition: 'all 0.2s ease',
      }}
      disabled={exporting}
    >
      <FileImageOutlined style={{ fontSize: '14px' }} />
    </button>
  );
};

const ReasoningBlock: React.FC<{
  reasoning: string;
  messageId: string;
  isExpanded: boolean;
  onToggle: (messageId: string) => void;
  isStreaming?: boolean;
}> = ({ reasoning, messageId, isExpanded, onToggle, isStreaming = false }) => {
  if (!reasoning) return null;

  const timestampMatch = reasoning.match(/\[Timestamp: ([^\]]+)\]/);
  const timestamp = timestampMatch ? timestampMatch[1] : null;
  const cleaned = reasoning.replace(/\[Timestamp: [^\]]+\]\n?\n?/g, '').trim();

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
        {isExpanded ? (
          <UpOutlined style={{ color: '#722ed1' }} />
        ) : (
          <DownOutlined style={{ color: '#722ed1' }} />
        )}
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
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
            {cleanContent(cleaned)}
          </ReactMarkdown>
        </div>
      )}
    </div>
  );
};

const DiagnosticsPanel: React.FC<{ diagnostics?: Message['diagnostics'] }> = ({ diagnostics }) => {
  if (!diagnostics) return null;

  const toolsUsed = diagnostics.toolsUsed || [];
  const verification = diagnostics.verificationPassed;
  const staleCount = Number(diagnostics.staleResultCount || 0);
  const fallbackSteps = Number(diagnostics.fallbackSteps || 0);

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
    </div>
  );
};

const MessageItem = memo(function MessageItem({
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
  const exportTitle = useMemo(() => deriveExportTitle(msg.content), [msg.content]);

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
        {isUser ? (
          <UserOutlined style={{ color: 'white', fontSize: '18px' }} />
        ) : (
          <RobotOutlined style={{ color: 'white', fontSize: '18px' }} />
        )}
      </div>

      <div style={{ flex: 1, maxWidth: 'calc(100% - 52px)' }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '6px', gap: '8px' }}>
          <span style={{ fontSize: '13px', fontWeight: 500, color: isUser ? '#4338ca' : '#262730' }}>
            {isUser ? '你' : '小帅助手'}
          </span>
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

            <div style={{ lineHeight: 1.7, fontSize: '14px' }}>
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {cleanContent(msg.content)}
              </ReactMarkdown>
            </div>

            {!isUser && (
              <TravelPlanToolkit
                messageId={messageId}
                content={msg.content}
                diagnostics={msg.diagnostics}
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
          <CopyButton content={msg.content} />
        </div>
      </div>
    </div>
  );
});

const StreamingMessageItem = memo(function StreamingMessageItem({
  content,
  reasoning,
  isWaiting = false,
  isThinking = false,
  currentTool = null,
}: {
  content: string;
  reasoning?: string;
  isWaiting?: boolean;
  isThinking?: boolean;
  currentTool?: string | null;
}) {
  const hasContent = Boolean(content && content.length > 0);
  const cleanReasoning = cleanContent(reasoning || '');
  const showReasoning = Boolean(cleanReasoning);
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
      <div
        style={{
          width: '40px',
          height: '40px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #0ea5e9 0%, #14b8a6 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          border: '2px solid rgba(255, 255, 255, 0.9)',
          boxShadow: '0 8px 18px rgba(20, 184, 166, 0.28)',
        }}
      >
        <RobotOutlined style={{ color: 'white', fontSize: '18px' }} />
      </div>

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
              <div style={{ fontSize: '12px', color: '#6d28d9', marginBottom: '6px', fontWeight: 500 }}>
                思考过程
              </div>
              <div
                style={{
                  fontSize: '12px',
                  color: '#4c1d95',
                  lineHeight: 1.65,
                  maxHeight: '120px',
                  overflow: 'auto',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {cleanReasoning}
              </div>
            </div>
          )}

          {currentTool && (
            <div style={{ marginBottom: hasContent ? '12px' : 0, fontSize: '12px', color: '#92400e' }}>
              工具执行中: {currentTool}
            </div>
          )}

          {hasContent && (
            <div style={{ lineHeight: 1.7, fontSize: '14px', color: '#1f2937', wordBreak: 'break-word' }}>
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {cleanContent(content)}
              </ReactMarkdown>
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
          <CopyButton content={hasContent ? content : '小帅助手正在思考中...'} />
        </div>
      </div>
    </div>
  );
});

const MessageList: React.FC<Props> = ({
  messages,
  streamingMessage,
  streamingReasoning,
  isWaiting = false,
  isThinking = false,
  currentTool = null,
  reasoningExpanded = {},
  onToggleReasoning,
  onContinuePrompt,
}) => {
  const toggleHandler = onToggleReasoning || (() => {});

  const renderedMessages = useMemo(
    () =>
      messages.map((msg, index) => {
        const messageId = `msg_${msg.timestamp}_${index}`;

        return (
          <MessageItem
            key={`${msg.role}-${msg.timestamp}-${index}`}
            msg={msg}
            messageId={messageId}
            reasoningExpanded={reasoningExpanded}
            onToggleReasoning={toggleHandler}
            onContinuePrompt={onContinuePrompt}
          />
        );
      }),
    [messages, reasoningExpanded, toggleHandler, onContinuePrompt]
  );

  const shouldShowStreamingDialog =
    isWaiting ||
    isThinking ||
    Boolean(streamingMessage && streamingMessage.length > 0) ||
    Boolean(streamingReasoning && streamingReasoning.length > 0);

  return (
    <div className="chat-message-container" style={{ maxWidth: '900px', margin: '0 auto', width: '100%' }}>
      {renderedMessages}

      {shouldShowStreamingDialog && (
        <StreamingMessageItem
          content={streamingMessage || ''}
          reasoning={streamingReasoning}
          isWaiting={isWaiting}
          isThinking={isThinking}
          currentTool={currentTool}
        />
      )}
    </div>
  );
};

export default MessageList;
