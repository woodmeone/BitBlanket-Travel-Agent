/* 【核心】消息区段子模块 —— 定义聊天消息中的特殊展示区块（推理过程、思考过程、诊断面板） */
/* 'use client' 表示这是一个客户端组件，只在浏览器端运行，不会在服务器端渲染 */
'use client';

/* import：从 React 库导入需要的功能 */
/* useMemo 是 React 的"记忆"钩子，用来缓存计算结果，避免每次渲染都重新计算 */
/* useState 是 React 的"状态"钩子，用来创建可变数据，数据变化时组件会自动刷新 */
import React, { useMemo, useState } from 'react';
/* 从 ant-design 图标库导入图标组件：灯泡、向下箭头、向上箭头 */
import { BulbOutlined, DownOutlined, UpOutlined } from '@ant-design/icons';
/* 导入 Message 类型定义，用于约束数据的结构 */
import type { Message } from '@/types';
/* 导入 Markdown 渲染器，用于将 Markdown 文本渲染为富文本 */
import { MarkdownRenderer } from './markdownRenderer';
/* 导入子 Agent 标签格式化函数，用于把英文子 Agent 名字翻译成中文 */
import { formatSubagentLabel } from './messageActions';

/* 【核心】推理过程区块 —— 展示 AI 的"深度推理"过程 */
/* 应用场景：当 AI 使用了"深度思考"模式回答问题时，会把推理过程展示在这个可折叠区块中 */
/* 例如：用户问"帮我规划一个3天的日本旅行"，AI 会先推理"需要考虑交通、住宿、预算..."，这些推理内容就显示在这里 */
/* React.FC 是 React 函数组件的类型写法，<> 里是组件接收的参数类型 */
export const ReasoningBlock: React.FC<{
  reasoning: string;          // 推理过程的文本内容
  messageId: string;          // 消息的唯一标识，用于控制展开/折叠状态
  isExpanded: boolean;        // 当前是否处于展开状态
  onToggle: (messageId: string) => void;  // 切换展开/折叠的回调函数
  isStreaming?: boolean;      // 是否正在流式输出（AI 还在生成内容）
}> = ({ reasoning, messageId, isExpanded, onToggle, isStreaming = false }) => {
  /* Boolean(reasoning) 判断推理内容是否为空字符串 */
  const hasReasoning = Boolean(reasoning);
  /* 用正则表达式从推理文本中提取时间戳，例如 "[Timestamp: 2024-01-01 12:00:00]" */
  const timestampMatch = reasoning.match(/\[Timestamp: ([^\]]+)\]/);
  const timestamp = timestampMatch ? timestampMatch[1] : null;
  /* 【核心】useMemo 缓存清理后的推理文本：去掉时间戳标记，只保留纯推理内容 */
  /* 依赖项 [reasoning] 表示只有 reasoning 变化时才重新计算 */
  const cleaned = useMemo(() => reasoning.replace(/\[Timestamp: [^\]]+\]\n?\n?/g, '').trim(), [reasoning]);

  /* 如果没有推理内容，不渲染任何东西 */
  if (!hasReasoning) return null;

  return (
    <div
      style={{
        marginBottom: '12px',
        /* 流式输出时用蓝色渐变背景，否则用灰色渐变背景，给用户视觉提示 */
        background: isStreaming
          ? 'linear-gradient(135deg, #e0f2fe 0%, #f0f9ff 100%)'
          : 'linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%)',
        borderRadius: '12px',
        border: '1px solid rgba(114, 46, 209, 0.15)',
        overflow: 'hidden',  /* 隐藏超出圆角的内容 */
      }}
    >
      {/* 可点击的标题栏，点击后展开/折叠推理内容 */}
      <div
        onClick={() => onToggle(messageId)}
        style={{
          display: 'flex',         /* 弹性布局，让图标、文字、箭头水平排列 */
          alignItems: 'center',    /* 垂直居中对齐 */
          padding: '10px 14px',
          cursor: 'pointer',       /* 鼠标变成手指形状，提示可点击 */
          userSelect: 'none',      /* 禁止选中文字，避免点击时误选 */
          background: isStreaming
            ? 'linear-gradient(135deg, #e8f4fd 0%, #dbeafe 100%)'
            : 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
        }}
      >
        {/* 灯泡图标，紫色 */}
        <BulbOutlined style={{ color: '#722ed1', marginRight: '8px' }} />
        {/* 标题文字：流式输出时显示"深度思考中..."，否则显示"推理过程" */}
        <span style={{ fontSize: '13px', color: '#1f2937', flex: 1, fontWeight: 500 }}>
          {isStreaming ? '深度思考中...' : '推理过程'}
        </span>
        {/* 非流式输出时显示时间戳 */}
        {timestamp && !isStreaming && (
          <span style={{ fontSize: '11px', color: '#9ca3af', marginRight: '8px' }}>{timestamp}</span>
        )}
        {/* 展开/折叠箭头图标 */}
        {isExpanded ? <UpOutlined style={{ color: '#722ed1' }} /> : <DownOutlined style={{ color: '#722ed1' }} />}
      </div>

      {/* 展开时显示推理内容 */}
      {isExpanded && (
        <div
          style={{
            padding: '14px',
            background: '#ffffff',
            fontFamily: 'SF Mono, Monaco, Inconsolata, monospace',  /* 等宽字体，适合显示代码/推理 */
            fontSize: '12px',
            lineHeight: 1.8,
            whiteSpace: 'pre-wrap',    /* 保留换行和空格，但允许自动换行 */
            maxHeight: '350px',        /* 最大高度 350px */
            overflow: 'auto',          /* 超出时显示滚动条 */
            color: '#4b5563',
            borderTop: '1px dashed rgba(114, 46, 209, 0.1)',  /* 虚线分隔线 */
          }}
        >
          {/* 用 Markdown 渲染器展示清理后的推理内容 */}
          <MarkdownRenderer content={cleaned} />
        </div>
      )}
    </div>
  );
};

/* 【核心】思考过程区块 —— 展示 AI 的"思考"过程（区别于推理，思考是更轻量的内部过程） */
/* 应用场景：AI 在生成回答前会先"思考"，比如"用户想去日本旅行，我需要先查一下航班信息..." */
/* 与 ReasoningBlock 的区别：ReasoningBlock 是深度推理（紫色主题），ThinkBlock 是普通思考（黄色主题） */
export const ThinkBlock: React.FC<{ content: string; isStreaming?: boolean }> = ({ content, isStreaming = false }) => {
  /* useState 创建一个局部状态变量 expanded，默认 false（折叠状态） */
  /* setExpanded 是修改 expanded 的函数，调用后组件会重新渲染 */
  const [expanded, setExpanded] = useState(false);
  /* 如果没有思考内容，不渲染 */
  if (!content) return null;

  return (
    <div
      style={{
        marginBottom: '12px',
        borderRadius: '12px',
        border: '1px solid rgba(180, 83, 9, 0.2)',  /* 橙色边框 */
        background: 'linear-gradient(135deg, #fffbeb 0%, #fff7ed 100%)',  /* 暖黄色渐变背景 */
        overflow: 'hidden',
      }}
    >
      {/* 可点击的标题按钮 */}
      <button
        type="button"
        /* 点击时切换展开状态：prev 是当前值，!prev 取反（true↔false） */
        onClick={() => setExpanded((prev) => !prev)}
        style={{
          width: '100%',
          border: 'none',
          background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',           /* 子元素之间的间距 */
          cursor: 'pointer',
          padding: '10px 12px',
          color: '#78350f',     /* 深棕色文字 */
          fontSize: '13px',
          fontWeight: 600,
        }}
      >
        <BulbOutlined />
        {/* 流式输出时显示"思考中（可展开）"，否则显示"思考过程（可展开）" */}
        <span style={{ flex: 1, textAlign: 'left' }}>{isStreaming ? '思考中（可展开）' : '思考过程（可展开）'}</span>
        {expanded ? <UpOutlined /> : <DownOutlined />}
      </button>

      {/* 展开时显示思考内容 */}
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

/* 【核心】诊断面板 —— 展示 AI 回答的诊断信息（工具使用情况、验证状态等） */
/* 应用场景：当 AI 调用了多个子 Agent（如规划 Agent、研究 Agent、预算 Agent）来回答问题时， */
/* 诊断面板会展示这些 Agent 的执行情况，让用户了解 AI 是如何协作完成任务的 */
/* 例如：验证状态"通过"表示 AI 的回答经过了校验，过期结果"0条"表示没有使用过时信息 */
export const DiagnosticsPanel: React.FC<{ diagnostics?: Message['diagnostics'] }> = ({ diagnostics }) => {
  /* 如果没有诊断数据，不渲染 */
  if (!diagnostics) return null;

  /* 从诊断数据中提取各项信息 */
  const toolsUsed = diagnostics.toolsUsed || [];           // 使用的工具列表
  const verification = diagnostics.verificationPassed;     // 验证是否通过
  const staleCount = Number(diagnostics.staleResultCount || 0);   // 过期结果数量
  const fallbackSteps = Number(diagnostics.fallbackSteps || 0);   // 备源切换次数（主数据源失败时切换到备用源的次数）
  const artifact = diagnostics.artifact;                   // 生成的旅行方案产物
  const subagentEvents = diagnostics.subagentEvents || []; // 子 Agent 执行事件列表

  return (
    <div
      style={{
        marginTop: '10px',
        padding: '10px 12px',
        borderRadius: '10px',
        border: '1px solid rgba(15, 23, 42, 0.08)',
        background: '#f8fafc',
        display: 'grid',    /* 网格布局，让各信息项整齐排列 */
        gap: '6px',
      }}
    >
      {/* 验证状态：null/undefined 显示"未知"，true 显示"通过"，false 显示"未通过" */}
      <div style={{ fontSize: '12px', color: '#334155' }}>
        验证状态: {verification === null || verification === undefined ? '未知' : verification ? '通过' : '未通过'}
      </div>
      {/* 过期结果数量 */}
      <div style={{ fontSize: '12px', color: '#334155' }}>过期结果: {staleCount} 条</div>
      {/* 备源切换次数 */}
      <div style={{ fontSize: '12px', color: '#334155' }}>备源切换: {fallbackSteps} 次</div>
      {/* 使用的工具列表，用逗号分隔 */}
      <div style={{ fontSize: '12px', color: '#334155', wordBreak: 'break-all' }}>
        工具列表: {toolsUsed.length > 0 ? toolsUsed.join(', ') : '无'}
      </div>
      {/* 如果有旅行方案产物，显示计划 ID */}
      {artifact?.itinerary.planId && (
        <div style={{ fontSize: '12px', color: '#334155' }}>Artifact 计划ID: {artifact.itinerary.planId}</div>
      )}
      {/* 如果有子 Agent 事件，显示子 Agent 的执行流程，用箭头连接 */}
      {/* 例如："规划 → 研究 → 预算 → 校验" */}
      {subagentEvents.length > 0 && (
        <div style={{ fontSize: '12px', color: '#334155' }}>
          子 Agent: {subagentEvents.map((event) => formatSubagentLabel(event.subagent)).join(' → ')}
        </div>
      )}
    </div>
  );
};
