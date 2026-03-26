'use client';

import React, { memo, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';

function parsePipeCells(line: string): string[] {
  return line
    .trim()
    .replace(/｜/g, '|')
    .replace(/^\|+/, '')
    .replace(/\|+$/, '')
    .split('|')
    .map((cell) => cell.replace(/\s+/g, ' ').trim())
    .filter(Boolean);
}

function isTableSeparatorLine(line: string): boolean {
  return /^\|\s*:?-{3,}:?(?:\s*\|\s*:?-{3,}:?)+\s*\|$/.test(line.trim());
}

function buildTableSeparator(columnCount: number): string {
  return `| ${Array.from({ length: Math.max(columnCount, 2) }, () => '---').join(' | ')} |`;
}

function normalizeHtmlBreaks(input: string): string {
  return input.replace(/<br\s*\/?>/gi, '\n');
}

function normalizePseudoSeparators(input: string): string {
  return input.replace(/｜/g, '|').replace(/[ \t]*\|\|[ \t]*/g, '\n| ').replace(/\n{3,}/g, '\n\n');
}

function normalizePipeTableBlocks(input: string): string {
  const lines = input.split('\n');
  const output: string[] = [];

  let index = 0;
  while (index < lines.length) {
    const firstCells = parsePipeCells(lines[index]);
    const firstLooksLikeRow = firstCells.length >= 2 && lines[index].includes('|');

    if (!firstLooksLikeRow) {
      output.push(lines[index]);
      index += 1;
      continue;
    }

    const tableRows: string[] = [];
    let rowIndex = index;
    while (rowIndex < lines.length) {
      const cells = parsePipeCells(lines[rowIndex]);
      const looksLikeRow = cells.length >= 2 && lines[rowIndex].includes('|');
      if (!looksLikeRow) break;
      tableRows.push(`| ${cells.join(' | ')} |`);
      rowIndex += 1;
    }

    if (tableRows.length >= 2) {
      const headerColumns = parsePipeCells(tableRows[0]).length;
      if (isTableSeparatorLine(tableRows[1])) {
        output.push(...tableRows);
      } else {
        output.push(tableRows[0], buildTableSeparator(headerColumns), ...tableRows.slice(1));
      }
    } else {
      const singleCells = parsePipeCells(tableRows[0] || '');
      if (singleCells.length >= 2) {
        output.push(`- **${singleCells[0]}**：${singleCells.slice(1).join(' / ')}`);
      } else {
        output.push(...tableRows);
      }
    }

    index = rowIndex;
  }

  return output.join('\n');
}

function normalizeEvidenceBlocks(input: string): string {
  return input.replace(/(证据来源\s*\n(?:\|.*\n)+)(?!\n)/g, '$1\n');
}

function cleanContent(content: string): string {
  if (!content) return '';

  const normalized = content.replace(/\r\n?/g, '\n').replace(/\u00a0/g, ' ').replace(/[ \t]+$/gm, '');

  return normalizeEvidenceBlocks(normalizePipeTableBlocks(normalizePseudoSeparators(normalizeHtmlBreaks(normalized)))).trim();
}

function getNodeText(node: React.ReactNode): string {
  if (node === null || node === undefined || typeof node === 'boolean') return '';
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map((item) => getNodeText(item)).join('');
  if (React.isValidElement(node)) {
    const element = node as React.ReactElement<{ children?: React.ReactNode }>;
    return getNodeText(element.props.children);
  }
  return '';
}

function extractMarkdownTableRows(node: React.ReactNode, rows: string[][] = []): string[][] {
  React.Children.forEach(node, (child) => {
    if (!React.isValidElement(child)) return;

    const element = child as React.ReactElement<{ children?: React.ReactNode }>;
    const elementType = typeof element.type === 'string' ? element.type : '';

    if (elementType === 'tr') {
      const cells: string[] = [];
      React.Children.forEach(element.props.children, (cellNode) => {
        if (!React.isValidElement(cellNode)) return;
        const cellElement = cellNode as React.ReactElement<{ children?: React.ReactNode }>;
        const cellType = typeof cellElement.type === 'string' ? cellElement.type : '';
        if (cellType !== 'th' && cellType !== 'td') return;

        const text = getNodeText(cellElement.props.children).replace(/\s+/g, ' ').trim();
        cells.push(text);
      });
      if (cells.length > 0) rows.push(cells);
      return;
    }

    extractMarkdownTableRows(element.props.children, rows);
  });

  return rows;
}

const MarkdownTableAsCards: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  const rows = extractMarkdownTableRows(children);
  if (rows.length === 0) return null;

  const header = rows[0];
  const bodyRows = rows.slice(1).filter((row) => row.some((cell) => cell.trim().length > 0));
  if (bodyRows.length === 0) return null;

  const columnCount = Math.max(2, header.length, ...bodyRows.map((row) => row.length));
  const headers = Array.from({ length: columnCount }, (_, index) => header[index] || `字段${index + 1}`);
  const normalizedBody = bodyRows.map((row) => Array.from({ length: columnCount }, (_, index) => row[index] || '-'));
  const isKeyValue = columnCount <= 2;

  return (
    <div style={{ display: 'grid', gap: 8, margin: '8px 0' }}>
      {normalizedBody.map((row, rowIndex) => (
        <div
          key={`markdown-table-row-${rowIndex}`}
          style={{
            border: '1px solid #dbe4ee',
            borderRadius: 12,
            background: 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)',
            padding: 10,
          }}
        >
          {isKeyValue ? (
            <div style={{ display: 'grid', gap: 4 }}>
              <div style={{ fontSize: 11, color: '#64748b', fontWeight: 700, letterSpacing: 0.2 }}>
                {row[0] === '-' ? headers[0] : row[0]}
              </div>
              <div style={{ fontSize: 14, color: '#0f172a', fontWeight: 600, lineHeight: 1.6 }}>{row[1] || '-'}</div>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 8 }}>
              <div style={{ fontSize: 14, color: '#0f172a', fontWeight: 700 }}>
                {row[0] === '-' ? `条目 ${rowIndex + 1}` : row[0]}
              </div>
              <div
                style={{
                  display: 'grid',
                  gap: 8,
                  gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                }}
              >
                {headers.slice(1).map((label, columnIndex) => (
                  <div
                    key={`markdown-table-field-${rowIndex}-${columnIndex}`}
                    style={{
                      border: '1px solid #e2e8f0',
                      borderRadius: 10,
                      background: '#ffffff',
                      padding: '8px 9px',
                    }}
                  >
                    <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4 }}>{label}</div>
                    <div style={{ fontSize: 13, color: '#1f2937', lineHeight: 1.6 }}>{row[columnIndex + 1] || '-'}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

const baseMarkdownComponents: Components = {
  p: ({ children }) => <p style={{ margin: 0, padding: 0 }}>{children}</p>,
  li: ({ children }) => <li style={{ margin: 0, padding: 0, lineHeight: 1.6 }}>{children}</li>,
  h1: ({ children }) => <h1 style={{ margin: '4px 0 2px 0', fontSize: '1.5em', fontWeight: 600 }}>{children}</h1>,
  h2: ({ children }) => <h2 style={{ margin: '4px 0 2px 0', fontSize: '1.3em', fontWeight: 600 }}>{children}</h2>,
  h3: ({ children }) => <h3 style={{ margin: '4px 0 2px 0', fontSize: '1.1em', fontWeight: 600 }}>{children}</h3>,
  ol: ({ children }) => <ol style={{ margin: '2px 0', paddingLeft: '20px' }}>{children}</ol>,
  ul: ({ children }) => <ul style={{ margin: '2px 0', paddingLeft: '20px' }}>{children}</ul>,
  table: ({ children }) => <MarkdownTableAsCards>{children}</MarkdownTableAsCards>,
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

function getMarkdownText(children: React.ReactNode): string {
  return React.Children.toArray(children)
    .map((child) => (typeof child === 'string' ? child : ''))
    .join('');
}

export const enhancedMarkdownComponents: Components = {
  ...baseMarkdownComponents,
  p: ({ children }) => <p style={{ margin: '0 0 8px', padding: 0, lineHeight: 1.8 }}>{children}</p>,
  li: ({ children }) => <li style={{ margin: '2px 0', padding: 0, lineHeight: 1.7 }}>{children}</li>,
  blockquote: ({ children }) => (
    <blockquote
      style={{
        margin: '10px 0',
        padding: '8px 12px',
        borderLeft: '3px solid #38bdf8',
        background: '#f8fafc',
        color: '#334155',
      }}
    >
      {children}
    </blockquote>
  ),
  hr: () => <hr style={{ border: 0, borderTop: '1px solid #e2e8f0', margin: '14px 0' }} />,
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noreferrer" style={{ color: '#2563eb', textDecoration: 'underline' }}>
      {children}
    </a>
  ),
  img: ({ src, alt }) => (
    <img
      src={src || ''}
      alt={alt || ''}
      style={{ maxWidth: '100%', borderRadius: 12, margin: '10px 0', border: '1px solid #e2e8f0' }}
    />
  ),
  pre: ({ children }) => (
    <pre
      style={{
        margin: '10px 0',
        padding: '12px 14px',
        borderRadius: 12,
        background: '#0f172a',
        color: '#e2e8f0',
        overflowX: 'auto',
        whiteSpace: 'pre-wrap',
      }}
    >
      {children}
    </pre>
  ),
  code: (props) => {
    const { className, children } = props as React.HTMLAttributes<HTMLElement> & { children?: React.ReactNode };
    const text = getMarkdownText(children);
    const isBlock = Boolean(className?.includes('language-')) || text.includes('\n');

    if (isBlock) {
      return (
        <code
          className={className}
          style={{
            background: 'transparent',
            color: 'inherit',
            fontFamily: 'SF Mono, Monaco, Consolas, monospace',
            fontSize: '12px',
            whiteSpace: 'pre-wrap',
          }}
        >
          {children}
        </code>
      );
    }

    return (
      <code
        className={className}
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
    );
  },
};

const MARKDOWN_PREPARE_CACHE_LIMIT = 160;
const markdownPrepareCache = new Map<string, string>();

function cachePreparedMarkdownContent(content: string, prepared: string): string {
  markdownPrepareCache.set(content, prepared);
  if (markdownPrepareCache.size > MARKDOWN_PREPARE_CACHE_LIMIT) {
    const oldestKey = markdownPrepareCache.keys().next().value;
    if (oldestKey) markdownPrepareCache.delete(oldestKey);
  }
  return prepared;
}

function transformOutsideCodeFences(input: string, transformer: (segment: string) => string): string {
  return input
    .split(/(```[\s\S]*?```|~~~[\s\S]*?~~~)/g)
    .map((segment) => {
      if (segment.startsWith('```') || segment.startsWith('~~~')) return segment;
      return transformer(segment);
    })
    .join('');
}

export function prepareMarkdownContent(content: string): string {
  if (!content) return '';
  const cached = markdownPrepareCache.get(content);
  if (cached !== undefined) return cached;

  const cleaned = cleanContent(content);
  const prepared = transformOutsideCodeFences(cleaned, (segment) =>
    segment.replace(/<br\s*\/?>/gi, '\n').replace(/(证据来源\s*\n(?:\|.*\n)+)(?!\n)/g, '$1\n')
  );
  return cachePreparedMarkdownContent(content, prepared);
}

export interface ThinkExtractResult {
  visibleContent: string;
  thinkBlocks: string[];
  hasUnclosedThink: boolean;
}

export function extractThinkBlocks(content: string): ThinkExtractResult {
  if (!content) {
    return { visibleContent: '', thinkBlocks: [], hasUnclosedThink: false };
  }

  const normalized = content.replace(/\r\n?/g, '\n');
  const lowered = normalized.toLowerCase();
  const openTag = '<think>';
  const closeTag = '</think>';
  const visibleParts: string[] = [];
  const thinkBlocks: string[] = [];
  let cursor = 0;
  let hasUnclosedThink = false;

  while (cursor < normalized.length) {
    const thinkStart = lowered.indexOf(openTag, cursor);
    if (thinkStart === -1) {
      visibleParts.push(normalized.slice(cursor));
      break;
    }

    visibleParts.push(normalized.slice(cursor, thinkStart));
    const thinkContentStart = thinkStart + openTag.length;
    const thinkEnd = lowered.indexOf(closeTag, thinkContentStart);

    if (thinkEnd === -1) {
      const trailingThink = normalized.slice(thinkContentStart).trim();
      if (trailingThink) thinkBlocks.push(trailingThink);
      hasUnclosedThink = true;
      break;
    }

    const thinkText = normalized.slice(thinkContentStart, thinkEnd).trim();
    if (thinkText) thinkBlocks.push(thinkText);
    cursor = thinkEnd + closeTag.length;
  }

  return {
    visibleContent: visibleParts.join('').replace(/\n{3,}/g, '\n\n').trim(),
    thinkBlocks,
    hasUnclosedThink,
  };
}

export function formatThinkContent(thinkBlocks: string[]): string {
  return thinkBlocks.join('\n\n---\n\n');
}

export const MarkdownRenderer: React.FC<{ content: string }> = memo(function MarkdownRenderer({ content }) {
  const preparedContent = useMemo(() => prepareMarkdownContent(content), [content]);
  if (!preparedContent) return null;

  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={enhancedMarkdownComponents}>
      {preparedContent}
    </ReactMarkdown>
  );
});
