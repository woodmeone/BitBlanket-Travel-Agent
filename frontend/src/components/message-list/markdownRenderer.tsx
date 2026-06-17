/* 【核心】Markdown 渲染器模块 —— 将 Markdown 文本转换为美观的富文本展示 */
/* Markdown 是一种用纯文本编写格式化内容的标记语言，例如用 # 表示标题、用 ** 表示加粗 */
/* 这个模块负责：1. 预处理（修复格式问题）2. 渲染（将 Markdown 转为 HTML 展示）3. 思考块提取 */
'use client';

/* memo：性能优化，避免不必要的重新渲染 */
/* useMemo：缓存计算结果 */
import React, { memo, useMemo } from 'react';
/* ReactMarkdown：第三方库，将 Markdown 文本解析并渲染为 React 组件 */
import ReactMarkdown from 'react-markdown';
/* Components：react-markdown 的类型定义，用于自定义各元素的渲染方式 */
import type { Components } from 'react-markdown';
/* remarkGfm：插件，支持 GitHub 风格的 Markdown 扩展语法（如表格、删除线、任务列表） */
import remarkGfm from 'remark-gfm';

/* 【核心】解析管道表格的一行，提取各单元格内容 */
/* 管道表格就是用 | 分隔的表格，例如：| 城市 | 天数 | 费用 | */
/* 应用场景：AI 生成的旅行方案中经常包含表格数据，需要正确解析才能展示 */
function parsePipeCells(line: string): string[] {
  return line
    .trim()                           // 去掉首尾空格
    .replace(/｜/g, '|')              // 把全角竖线（｜）替换为半角竖线（|）
    .replace(/^\|+/, '')              // 去掉行首的竖线
    .replace(/\|+$/, '')              // 去掉行尾的竖线
    .split('|')                       // 按竖线分割成数组
    .map((cell) => cell.replace(/\s+/g, ' ').trim())  // 合并多余空格并去首尾空格
    .filter(Boolean);                 // 过滤掉空字符串
}

/* 判断一行是否是 Markdown 表格的分隔行 */
/* 分隔行格式如：| --- | --- | --- |，用于分隔表头和表体 */
function isTableSeparatorLine(line: string): boolean {
  return /^\|\s*:?-{3,}:?(?:\s*\|\s*:?-{3,}:?)+\s*\|$/.test(line.trim());
}

/* 生成表格分隔行，例如：| --- | --- | */
/* columnCount：列数 */
function buildTableSeparator(columnCount: number): string {
  return `| ${Array.from({ length: Math.max(columnCount, 2) }, () => '---').join(' | ')} |`;
}

/* 将 HTML 换行标签（<br>）替换为真正的换行符 */
/* 应用场景：AI 有时会在 Markdown 中混用 HTML 标签，需要统一处理 */
function normalizeHtmlBreaks(input: string): string {
  return input.replace(/<br\s*\/?>/gi, '\n');
}

/* 修正伪分隔符：将双竖线（||）替换为换行+竖线，统一表格格式 */
function normalizePseudoSeparators(input: string): string {
  return input.replace(/｜/g, '|').replace(/[ \t]*\|\|[ \t]*/g, '\n| ').replace(/\n{3,}/g, '\n\n');
}

/* 【核心】规范化管道表格块 —— 将格式不规范的表格文本修复为标准 Markdown 表格 */
/* 应用场景：AI 生成的表格可能缺少分隔行，或者格式不规范，需要自动修复才能正确渲染 */
/* 例如：输入 "城市 | 天数\n东京 | 3天" → 输出 "| 城市 | 天数 |\n| --- | --- |\n| 东京 | 3天 |" */
function normalizePipeTableBlocks(input: string): string {
  const lines = input.split('\n');
  const output: string[] = [];

  let index = 0;
  /* 逐行扫描，识别表格块 */
  while (index < lines.length) {
    const firstCells = parsePipeCells(lines[index]);
    /* 判断当前行是否看起来像表格行（至少2个单元格且包含竖线） */
    const firstLooksLikeRow = firstCells.length >= 2 && lines[index].includes('|');

    if (!firstLooksLikeRow) {
      output.push(lines[index]);
      index += 1;
      continue;
    }

    /* 收集连续的表格行 */
    const tableRows: string[] = [];
    let rowIndex = index;
    while (rowIndex < lines.length) {
      const cells = parsePipeCells(lines[rowIndex]);
      const looksLikeRow = cells.length >= 2 && lines[rowIndex].includes('|');
      if (!looksLikeRow) break;
      /* 将每行格式化为标准格式：| 单元格1 | 单元格2 | */
      tableRows.push(`| ${cells.join(' | ')} |`);
      rowIndex += 1;
    }

    if (tableRows.length >= 2) {
      /* 至少2行才构成有效表格 */
      const headerColumns = parsePipeCells(tableRows[0]).length;
      if (isTableSeparatorLine(tableRows[1])) {
        /* 第二行已经是分隔行，直接使用 */
        output.push(...tableRows);
      } else {
        /* 缺少分隔行，自动插入 */
        output.push(tableRows[0], buildTableSeparator(headerColumns), ...tableRows.slice(1));
      }
    } else {
      /* 只有1行，不构成表格，转为键值对格式 */
      const singleCells = parsePipeCells(tableRows[0] || '');
      if (singleCells.length >= 2) {
        /* 例如："| 东京 | 3天 |" → "- **东京**：3天" */
        output.push(`- **${singleCells[0]}**：${singleCells.slice(1).join(' / ')}`);
      } else {
        output.push(...tableRows);
      }
    }

    index = rowIndex;
  }

  return output.join('\n');
}

/* 在"证据来源"表格后添加空行，确保后续内容不被误识别为表格的一部分 */
function normalizeEvidenceBlocks(input: string): string {
  return input.replace(/(证据来源\s*\n(?:\|.*\n)+)(?!\n)/g, '$1\n');
}

/* 【核心】内容清理函数 —— 对原始 Markdown 内容进行一系列规范化处理 */
/* 处理流程：统一换行符 → 替换特殊空格 → 去行尾空格 → 处理HTML换行 → 修正伪分隔符 → 修正表格 → 修正证据块 */
function cleanContent(content: string): string {
  if (!content) return '';

  /* 统一换行符为 \n，替换不间断空格为普通空格，去掉行尾空格 */
  const normalized = content.replace(/\r\n?/g, '\n').replace(/\u00a0/g, ' ').replace(/[ \t]+$/gm, '');

  /* 按顺序应用各规范化函数 */
  return normalizeEvidenceBlocks(normalizePipeTableBlocks(normalizePseudoSeparators(normalizeHtmlBreaks(normalized)))).trim();
}

/* 递归获取 React 节点中的纯文本内容 */
/* 应用场景：需要从 React 渲染的表格中提取纯文本，用于卡片式展示 */
/* 例如：<td>东京</td> → "东京" */
function getNodeText(node: React.ReactNode): string {
  if (node === null || node === undefined || typeof node === 'boolean') return '';
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map((item) => getNodeText(item)).join('');
  /* React.isValidElement 判断是否是 React 元素（如 <div>、<span> 等） */
  if (React.isValidElement(node)) {
    const element = node as React.ReactElement<{ children?: React.ReactNode }>;
    /* 递归获取子元素的文本 */
    return getNodeText(element.props.children);
  }
  return '';
}

/* 【核心】从 React 渲染的表格中提取所有行的数据 */
/* 应用场景：将 Markdown 表格转为卡片式展示时，需要先提取表格数据 */
/* 例如：从 <table><tr><th>城市</th><th>天数</th></tr><tr><td>东京</td><td>3天</td></tr></table> */
/* 提取出 [["城市", "天数"], ["东京", "3天"]] */
function extractMarkdownTableRows(node: React.ReactNode, rows: string[][] = []): string[][] {
  /* React.Children.forEach 遍历 React 子元素 */
  React.Children.forEach(node, (child) => {
    if (!React.isValidElement(child)) return;

    const element = child as React.ReactElement<{ children?: React.ReactNode }>;
    /* 获取元素的标签名，如 'tr'、'td'、'th' */
    const elementType = typeof element.type === 'string' ? element.type : '';

    if (elementType === 'tr') {
      /* 遇到表格行（<tr>），提取所有单元格内容 */
      const cells: string[] = [];
      React.Children.forEach(element.props.children, (cellNode) => {
        if (!React.isValidElement(cellNode)) return;
        const cellElement = cellNode as React.ReactElement<{ children?: React.ReactNode }>;
        const cellType = typeof cellElement.type === 'string' ? cellElement.type : '';
        /* 只处理表头（<th>）和单元格（<td>） */
        if (cellType !== 'th' && cellType !== 'td') return;

        const text = getNodeText(cellElement.props.children).replace(/\s+/g, ' ').trim();
        cells.push(text);
      });
      if (cells.length > 0) rows.push(cells);
      return;
    }

    /* 如果不是 <tr>，递归查找子元素中的 <tr> */
    extractMarkdownTableRows(element.props.children, rows);
  });

  return rows;
}

/* 【核心】Markdown 表格卡片化展示组件 —— 将标准表格渲染为美观的卡片布局 */
/* 应用场景：AI 生成的旅行方案中的表格数据（如行程表、费用明细），用卡片展示比表格更美观 */
/* 例如：2列表格渲染为"键-值"卡片，3列及以上渲染为"标题+多字段"卡片 */
const MarkdownTableAsCards: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  /* 从 React 表格元素中提取行数据 */
  const rows = extractMarkdownTableRows(children);
  if (rows.length === 0) return null;

  /* 第一行作为表头 */
  const header = rows[0];
  /* 过滤掉全空的行 */
  const bodyRows = rows.slice(1).filter((row) => row.some((cell) => cell.trim().length > 0));
  if (bodyRows.length === 0) return null;

  /* 统一列数，不足的补空 */
  const columnCount = Math.max(2, header.length, ...bodyRows.map((row) => row.length));
  const headers = Array.from({ length: columnCount }, (_, index) => header[index] || `字段${index + 1}`);
  const normalizedBody = bodyRows.map((row) => Array.from({ length: columnCount }, (_, index) => row[index] || '-'));
  /* 2列及以下视为键值对，3列及以上视为多字段卡片 */
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
            /* 键值对模式：上方显示标签，下方显示值 */
            <div style={{ display: 'grid', gap: 4 }}>
              <div style={{ fontSize: 11, color: '#64748b', fontWeight: 700, letterSpacing: 0.2 }}>
                {row[0] === '-' ? headers[0] : row[0]}
              </div>
              <div style={{ fontSize: 14, color: '#0f172a', fontWeight: 600, lineHeight: 1.6 }}>{row[1] || '-'}</div>
            </div>
          ) : (
            /* 多字段模式：第一列作为标题，其余列作为字段卡片 */
            <div style={{ display: 'grid', gap: 8 }}>
              <div style={{ fontSize: 14, color: '#0f172a', fontWeight: 700 }}>
                {row[0] === '-' ? `条目 ${rowIndex + 1}` : row[0]}
              </div>
              <div
                style={{
                  display: 'grid',
                  gap: 8,
                  /* auto-fit 自适应列数，每列最小140px */
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

/* 基础 Markdown 组件样式映射 —— 定义各 Markdown 元素的默认渲染样式 */
/* Components 类型是 react-markdown 提供的，用于自定义各 HTML 元素的渲染方式 */
/* 例如：p 对应段落 <p>，h1 对应一级标题 <h1>，table 对应表格 <table> */
const baseMarkdownComponents: Components = {
  /* 段落：去掉默认的上下边距 */
  p: ({ children }) => <p style={{ margin: 0, padding: 0 }}>{children}</p>,
  /* 列表项：去掉默认的上下边距 */
  li: ({ children }) => <li style={{ margin: 0, padding: 0, lineHeight: 1.6 }}>{children}</li>,
  /* 各级标题：缩小默认的上下边距和字号 */
  h1: ({ children }) => <h1 style={{ margin: '4px 0 2px 0', fontSize: '1.5em', fontWeight: 600 }}>{children}</h1>,
  h2: ({ children }) => <h2 style={{ margin: '4px 0 2px 0', fontSize: '1.3em', fontWeight: 600 }}>{children}</h2>,
  h3: ({ children }) => <h3 style={{ margin: '4px 0 2px 0', fontSize: '1.1em', fontWeight: 600 }}>{children}</h3>,
  /* 有序列表和无序列表：缩小边距，设置左内边距 */
  ol: ({ children }) => <ol style={{ margin: '2px 0', paddingLeft: '20px' }}>{children}</ol>,
  ul: ({ children }) => <ul style={{ margin: '2px 0', paddingLeft: '20px' }}>{children}</ul>,
  /* 【核心】表格：替换为卡片化展示组件，而不是默认的 HTML 表格 */
  table: ({ children }) => <MarkdownTableAsCards>{children}</MarkdownTableAsCards>,
  /* 表头单元格：浅灰背景 */
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
  /* 表格数据单元格 */
  td: ({ children }) => <td style={{ border: '1px solid #e5e7eb', padding: '6px 8px' }}>{children}</td>,
  /* 行内代码：灰色背景、等宽字体 */
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

/* 从 React 子元素中提取纯文本（仅限直接的字符串子元素） */
function getMarkdownText(children: React.ReactNode): string {
  return React.Children.toArray(children)
    .map((child) => (typeof child === 'string' ? child : ''))
    .join('');
}

/* 【核心】增强版 Markdown 组件样式映射 —— 在基础样式上增加了更多元素的样式定制 */
/* 包括：引用块、分隔线、链接、图片、代码块等 */
export const enhancedMarkdownComponents: Components = {
  /* 展开基础样式（段落、列表、标题等） */
  ...baseMarkdownComponents,
  /* 段落：增加底部间距和行高，提升阅读体验 */
  p: ({ children }) => <p style={{ margin: '0 0 8px', padding: 0, lineHeight: 1.8 }}>{children}</p>,
  /* 列表项：增加行高 */
  li: ({ children }) => <li style={{ margin: '2px 0', padding: 0, lineHeight: 1.7 }}>{children}</li>,
  /* 引用块：左侧蓝色竖线 + 浅灰背景 */
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
  /* 分隔线：细灰色线 */
  hr: () => <hr style={{ border: 0, borderTop: '1px solid #e2e8f0', margin: '14px 0' }} />,
  /* 链接：蓝色文字 + 下划线，点击在新标签页打开 */
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noreferrer" style={{ color: '#2563eb', textDecoration: 'underline' }}>
      {children}
    </a>
  ),
  /* 图片：圆角、最大宽度100%、细边框 */
  img: ({ src, alt }) => (
    <img
      src={src || ''}
      alt={alt || ''}
      style={{ maxWidth: '100%', borderRadius: 12, margin: '10px 0', border: '1px solid #e2e8f0' }}
    />
  ),
  /* 代码块：深色背景（模拟终端风格） */
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
  /* 【核心】代码元素：区分行内代码和代码块，分别应用不同样式 */
  /* 行内代码：灰色背景（如 `变量名`） */
  /* 代码块：透明背景，继承父级 pre 的深色背景 */
  code: (props) => {
    const { className, children } = props as React.HTMLAttributes<HTMLElement> & { children?: React.ReactNode };
    const text = getMarkdownText(children);
    /* 判断是否是代码块：有语言标记（如 ```python）或包含换行符 */
    const isBlock = Boolean(className?.includes('language-')) || text.includes('\n');

    if (isBlock) {
      /* 代码块样式：透明背景，继承 pre 的深色背景 */
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

    /* 行内代码样式：灰色背景 */
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

/* Markdown 预处理缓存的最大条目数 */
const MARKDOWN_PREPARE_CACHE_LIMIT = 160;
/* 缓存 Map：键是原始内容，值是预处理后的内容 */
/* 应用场景：同一条消息可能被多次渲染（如滚动时），缓存可以避免重复的预处理计算 */
const markdownPrepareCache = new Map<string, string>();

/* 将预处理结果写入缓存，如果缓存超过上限则删除最早的条目 */
function cachePreparedMarkdownContent(content: string, prepared: string): string {
  markdownPrepareCache.set(content, prepared);
  if (markdownPrepareCache.size > MARKDOWN_PREPARE_CACHE_LIMIT) {
    /* Map 保持插入顺序，第一个键就是最早插入的 */
    const oldestKey = markdownPrepareCache.keys().next().value;
    if (oldestKey) markdownPrepareCache.delete(oldestKey);
  }
  return prepared;
}

/* 【核心】在代码围栏外部应用转换函数 */
/* 代码围栏就是用 ``` 或 ~~~ 包裹的代码块，里面的内容不应该被转换 */
/* 例如：代码块中的 | 不应该被当作表格竖线处理 */
function transformOutsideCodeFences(input: string, transformer: (segment: string) => string): string {
  return input
    /* 用正则表达式将文本按代码围栏分割，代码围栏内的段落保持不变 */
    .split(/(```[\s\S]*?```|~~~[\s\S]*?~~~)/g)
    .map((segment) => {
      /* 如果是代码围栏，不转换 */
      if (segment.startsWith('```') || segment.startsWith('~~~')) return segment;
      /* 非代码围栏部分，应用转换函数 */
      return transformer(segment);
    })
    .join('');
}

/* 【核心】Markdown 内容预处理函数 —— 对原始内容进行清理和规范化，然后缓存结果 */
/* 这是 Markdown 渲染前的关键步骤，确保内容格式正确 */
export function prepareMarkdownContent(content: string): string {
  if (!content) return '';
  /* 先查缓存，如果已经预处理过则直接返回 */
  const cached = markdownPrepareCache.get(content);
  if (cached !== undefined) return cached;

  /* 清理内容 */
  const cleaned = cleanContent(content);
  /* 在代码围栏外部进行额外处理（替换 HTML 换行、修正证据块格式） */
  const prepared = transformOutsideCodeFences(cleaned, (segment) =>
    segment.replace(/<br\s*\/?>/gi, '\n').replace(/(证据来源\s*\n(?:\|.*\n)+)(?!\n)/g, '$1\n')
  );
  return cachePreparedMarkdownContent(content, prepared);
}

/* 思考块提取结果的类型定义 */
export interface ThinkExtractResult {
  visibleContent: string;     // 可见内容（去掉思考标签后的正文）
  thinkBlocks: string[];      // 思考内容数组（每个 </think>... 对应一个元素）
  hasUnclosedThink: boolean;  // 是否有未闭合的思考标签（流式输出时可能还在生成中）
}

/* 【核心】思考块提取函数 —— 从消息内容中分离"思考过程"和"可见正文" */
/* 应用场景：AI 在生成回答时，可能会先输出一段"思考过程"（用 </think>... 标签包裹），然后再输出正文 */
/* 例如：输入 "让我想想...这是我的建议" → 输出 { visibleContent: "这是我的建议", thinkBlocks: ["让我想想..."] } */
/* 这个设计让用户可以选择性地查看 AI 的思考过程，而不会被干扰 */
export function extractThinkBlocks(content: string): ThinkExtractResult {
  if (!content) {
    return { visibleContent: '', thinkBlocks: [], hasUnclosedThink: false };
  }

  /* 统一换行符 */
  const normalized = content.replace(/\r\n?/g, '\n');
  /* 转为小写用于标签匹配（不区分大小写） */
  const lowered = normalized.toLowerCase();
  const openTag = '</think>';
  const closeTag = '</think>';
  const visibleParts: string[] = [];   // 收集可见内容片段
  const thinkBlocks: string[] = [];    // 收集思考内容
  let cursor = 0;                      // 当前扫描位置
  let hasUnclosedThink = false;        // 是否有未闭合的思考标签

  /* 逐段扫描，提取思考块和可见内容 */
  while (cursor < normalized.length) {
    /* 查找下一个思考开始标签 */
    const thinkStart = lowered.indexOf(openTag, cursor);
    if (thinkStart === -1) {
      /* 没有更多思考标签，剩余内容都是可见的 */
      visibleParts.push(normalized.slice(cursor));
      break;
    }

    /* 思考标签之前的内容是可见的 */
    visibleParts.push(normalized.slice(cursor, thinkStart));
    const thinkContentStart = thinkStart + openTag.length;
    /* 查找思考结束标签 */
    const thinkEnd = lowered.indexOf(closeTag, thinkContentStart);

    if (thinkEnd === -1) {
      /* 没有找到结束标签，说明思考还在进行中（流式输出） */
      const trailingThink = normalized.slice(thinkContentStart).trim();
      if (trailingThink) thinkBlocks.push(trailingThink);
      hasUnclosedThink = true;
      break;
    }

    /* 提取思考内容 */
    const thinkText = normalized.slice(thinkContentStart, thinkEnd).trim();
    if (thinkText) thinkBlocks.push(thinkText);
    /* 移动游标到结束标签之后 */
    cursor = thinkEnd + closeTag.length;
  }

  return {
    /* 合并可见内容，去除多余空行 */
    visibleContent: visibleParts.join('').replace(/\n{3,}/g, '\n\n').trim(),
    thinkBlocks,
    hasUnclosedThink,
  };
}

/* 将多个思考块合并为一段文本，用分隔线连接 */
/* 应用场景：当 AI 的回答中包含多段思考时，用分隔线区分 */
export function formatThinkContent(thinkBlocks: string[]): string {
  return thinkBlocks.join('\n\n---\n\n');
}

/* 【核心】Markdown 渲染器组件 —— 将 Markdown 文本渲染为美观的富文本 */
/* 用 memo 包裹避免不必要的重新渲染 */
/* 应用场景：所有消息内容（用户消息和 AI 回复）都通过这个组件渲染 */
export const MarkdownRenderer: React.FC<{ content: string }> = memo(function MarkdownRenderer({ content }) {
  /* 预处理内容并缓存结果 */
  const preparedContent = useMemo(() => prepareMarkdownContent(content), [content]);
  /* 如果预处理后内容为空，不渲染 */
  if (!preparedContent) return null;

  return (
    /* ReactMarkdown 是核心渲染组件 */
    /* remarkPlugins={[remarkGfm]} 启用 GitHub 风格 Markdown 扩展 */
    /* components={enhancedMarkdownComponents} 使用自定义的样式映射 */
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={enhancedMarkdownComponents}>
      {preparedContent}
    </ReactMarkdown>
  );
});
