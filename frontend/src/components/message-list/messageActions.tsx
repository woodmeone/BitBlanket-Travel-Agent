/* 【核心】消息操作按钮模块 —— 提供复制、导出图片等操作按钮，以及辅助函数 */
/* 'use client' 表示这是一个客户端组件，只在浏览器端运行 */
'use client';

/* useState：React 状态钩子，用于创建可变数据 */
import React, { useState } from 'react';
/* App：ant-design 提供的应用上下文，useApp() 可以获取 message 等全局方法 */
import { App } from 'antd';
/* 图标组件：对勾（复制成功）、复制、文件图片（导出图片） */
import { CheckOutlined, CopyOutlined, FileImageOutlined } from '@ant-design/icons';
/* html2canvas：第三方库，可以将网页 DOM 元素截图为 Canvas（画布），再转为图片 */
import html2canvas from 'html2canvas';
/* 导入 Markdown 内容预处理函数，用于提取标题 */
import { prepareMarkdownContent } from './markdownRenderer';

/* 【核心】从消息内容中推导导出图片的标题 */
/* 应用场景：当用户点击"导出图片"按钮时，需要给图片起一个有意义的文件名 */
/* 例如：AI 回答的第一行是"## 东京3日游攻略"，则导出标题为"东京3日游攻略" */
/* 如果找不到有意义的行，就用默认标题"旅行方案分享" */
export function deriveExportTitle(content: string): string {
  /* 先预处理 Markdown 内容，然后按行分割 */
  const firstMeaningfulLine = prepareMarkdownContent(content)
    .split('\n')                              // 按换行符分割成数组
    .map((line) => line.trim())               // 去掉每行首尾空格
    /* 找到第一个"有意义"的行：非空、不是表格分隔符(|开头)、不是分隔线(-开头)、不是引用(>开头) */
    .find((line) => line && !line.startsWith('|') && !line.startsWith('-') && !line.startsWith('>'));

  /* 如果没有找到有意义的行，返回默认标题 */
  if (!firstMeaningfulLine) return '旅行方案分享';
  /* 去掉 Markdown 标题标记（如 ## ），截取前28个字符 */
  const normalized = firstMeaningfulLine.replace(/^#+\s*/, '').slice(0, 28).trim();
  return normalized || '旅行方案分享';
}

/* 子 Agent 名称中英文映射 */
/* 应用场景：AI 内部用英文名标识不同的子 Agent，但展示给用户时需要翻译成中文 */
/* 例如：diagnostics 中显示"规划 → 研究 → 预算 → 校验"而不是"planning → research → budget → verification" */
export function formatSubagentLabel(name: string): string {
  if (name === 'planning') return '规划';       // 规划 Agent：负责行程规划
  if (name === 'research') return '研究';       // 研究 Agent：负责信息搜索
  if (name === 'budget') return '预算';         // 预算 Agent：负责费用估算
  if (name === 'verification') return '校验';   // 校验 Agent：负责结果验证
  return name;  // 未识别的名称原样返回
}

/* 【核心】复制按钮组件 —— 点击后将消息内容复制到剪贴板 */
/* 应用场景：用户看到 AI 的旅行方案后，想复制文字内容发给别人，点击此按钮即可一键复制 */
export const CopyButton: React.FC<{ content: string }> = ({ content }) => {
  /* copied 状态：是否已复制成功，用于切换图标（复制→对勾） */
  const [copied, setCopied] = useState(false);
  /* message 是 ant-design 的消息提示工具，可以在页面顶部弹出小提示 */
  const { message } = App.useApp();

  /* 处理复制操作 */
  async function handleCopy() {
    try {
      /* navigator.clipboard.writeText 是浏览器提供的剪贴板 API，将文本写入剪贴板 */
      await navigator.clipboard.writeText(content);
      setCopied(true);                          // 标记为已复制
      message.success('已复制到剪贴板');          // 弹出成功提示
      setTimeout(() => setCopied(false), 1500);  /* 1.5秒后恢复为未复制状态 */
    } catch {
      message.error('复制失败，请手动复制');      /* 弹出失败提示 */
    }
  }

  return (
    <button
      onClick={handleCopy}
      title={copied ? '已复制' : '复制'}  /* 鼠标悬停时显示的提示文字 */
      style={{
        background: 'transparent',  /* 透明背景 */
        border: 'none',
        cursor: 'pointer',
        padding: '4px 8px',
        borderRadius: '4px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: copied ? '#52c41a' : 'inherit',  /* 复制成功变绿色 */
        transition: 'all 0.2s ease',             /* 颜色变化有0.2秒过渡动画 */
      }}
    >
      {/* 复制成功显示对勾图标，否则显示复制图标 */}
      {copied ? <CheckOutlined style={{ fontSize: '14px' }} /> : <CopyOutlined style={{ fontSize: '14px' }} />}
    </button>
  );
};

/* 【核心】导出图片按钮组件 —— 将 AI 回答内容截图并下载为 PNG 图片 */
/* 应用场景：用户想把 AI 生成的旅行方案保存为图片分享到微信/朋友圈，点击此按钮即可生成精美分享卡 */
/* 实现原理：创建一个临时的 DOM 容器，放入品牌头部+消息内容，用 html2canvas 截图后下载 */
export const ExportImageButton: React.FC<{
  targetRef: React.RefObject<HTMLDivElement | null>;  // 要截图的 DOM 元素引用
  filename: string;        // 下载的文件名（不含扩展名）
  title: string;           // 分享卡上显示的标题
  exportedAt: string;      // 导出时间，显示在分享卡上
}> = ({ targetRef, filename, title, exportedAt }) => {
  /* exporting 状态：是否正在导出中，防止重复点击 */
  const [exporting, setExporting] = useState(false);
  const { message } = App.useApp();

  /* 处理导出操作 */
  async function handleExport() {
    /* 如果目标元素不存在或正在导出中，直接返回 */
    if (!targetRef.current || exporting) return;

    /* exportShell 是临时创建的 DOM 容器，用于组装截图内容 */
    let exportShell: HTMLDivElement | null = null;

    try {
      setExporting(true);
      /* 创建一个隐藏的临时容器，放在屏幕外（left: -10000px），用户看不到 */
      exportShell = document.createElement('div');
      exportShell.style.position = 'fixed';
      exportShell.style.left = '-10000px';
      exportShell.style.top = '0';
      exportShell.style.width = '920px';     /* 固定宽度，保证截图效果一致 */
      exportShell.style.padding = '28px';
      exportShell.style.background = 'linear-gradient(180deg, #f8fbff 0%, #ffffff 28%, #f8fafc 100%)';
      exportShell.style.boxSizing = 'border-box';

      /* 创建分享卡的头部区域（品牌信息 + 标题 + 时间） */
      const header = document.createElement('div');
      header.style.display = 'flex';
      header.style.justifyContent = 'space-between';
      header.style.alignItems = 'center';
      header.style.gap = '16px';
      header.style.padding = '18px 20px';
      header.style.marginBottom = '18px';
      header.style.borderRadius = '20px';
      header.style.background = 'linear-gradient(135deg, #082f49 0%, #0f766e 100%)';  /* 深色渐变背景 */
      header.style.color = '#ffffff';

      /* 品牌区域：Logo + 文字 */
      const brand = document.createElement('div');
      brand.style.display = 'flex';
      brand.style.alignItems = 'center';
      brand.style.gap = '12px';

      /* Logo 图标：显示"ST"字样 */
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

      /* 品牌文字：主标题 + 副标题 */
      const brandText = document.createElement('div');
      const brandTitle = document.createElement('div');
      brandTitle.textContent = 'BitBlanket Travel Agent';
      brandTitle.style.fontSize = '16px';
      brandTitle.style.fontWeight = '700';
      const brandSubtitle = document.createElement('div');
      brandSubtitle.textContent = 'AI 旅行方案分享卡';
      brandSubtitle.style.fontSize = '12px';
      brandSubtitle.style.opacity = '0.82';
      brandText.appendChild(brandTitle);
      brandText.appendChild(brandSubtitle);

      brand.appendChild(logo);
      brand.appendChild(brandText);

      /* 右侧元信息：标题 + 导出时间 */
      const meta = document.createElement('div');
      meta.style.textAlign = 'right';
      const metaTitle = document.createElement('div');
      metaTitle.textContent = title;
      metaTitle.style.fontSize = '18px';
      metaTitle.style.fontWeight = '700';
      const metaTime = document.createElement('div');
      metaTime.textContent = `导出时间 ${exportedAt}`;
      metaTime.style.fontSize = '12px';
      metaTime.style.opacity = '0.82';
      meta.appendChild(metaTitle);
      meta.appendChild(metaTime);

      header.appendChild(brand);
      header.appendChild(meta);

      /* 克隆消息卡片 DOM，作为截图的内容区域 */
      const clonedCard = targetRef.current.cloneNode(true) as HTMLDivElement;
      clonedCard.style.maxWidth = '100%';

      /* 将头部和内容组装到临时容器中 */
      exportShell.appendChild(header);
      exportShell.appendChild(clonedCard);
      /* 将临时容器添加到页面 body 中（虽然不可见，但 html2canvas 需要它在 DOM 中才能截图） */
      document.body.appendChild(exportShell);

      /* 【核心】使用 html2canvas 将临时容器截图为 Canvas */
      /* scale: 2 表示2倍分辨率，让图片更清晰 */
      const canvas = await html2canvas(exportShell, {
        scale: 2,
        backgroundColor: '#f8fbff',
        useCORS: true,  /* 允许跨域图片（如网络图片） */
      });
      /* 将 Canvas 转为 PNG 图片的下载链接，并自动触发下载 */
      const link = document.createElement('a');
      link.href = canvas.toDataURL('image/png');  /* 将画布转为 Base64 格式的 PNG 图片数据 */
      link.download = `${filename}.png`;           /* 设置下载文件名 */
      link.click();                                 /* 模拟点击，触发浏览器下载 */
      message.success('回答已导出为图片');
    } catch {
      message.error('导出图片失败，请重试');
    } finally {
      /* 无论成功还是失败，都要清理临时 DOM 容器，避免内存泄漏 */
      if (exportShell?.parentNode) exportShell.parentNode.removeChild(exportShell);
      setExporting(false);
    }
  }

  return (
    <button
      onClick={handleExport}
      title={exporting ? '导出中' : '导出图片'}
      style={{
        background: 'transparent',
        border: 'none',
        cursor: exporting ? 'wait' : 'pointer',  /* 导出中鼠标变成等待图标 */
        padding: '4px 8px',
        borderRadius: '4px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: exporting ? '#2563eb' : 'inherit',  /* 导出中变蓝色 */
        transition: 'all 0.2s ease',
      }}
      disabled={exporting}  /* 导出中禁用按钮，防止重复点击 */
    >
      <FileImageOutlined style={{ fontSize: '14px' }} />
    </button>
  );
};
