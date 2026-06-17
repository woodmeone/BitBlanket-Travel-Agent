// 【核心】旅行方案制品（Artifact）的构建与导出工具
// "制品"指的是 AI 生成的完整旅行方案数据，包括目的地、预算、行程、校验结果等
// 本文件负责：
//   1. 从制品数据中提取关键信息（目的地、预算摘要、校验状态等）
//   2. 构建用于分享、导出、对比的数据结构
//   3. 生成 HTML 格式的方案报告

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import type {
  ArtifactDeliveryBundle,
  ArtifactDeliveryDescriptor,
  ArtifactDeliverySection,
  ArtifactOverviewMetric,
  ExecutionReceipt,
  SubagentEvent,
  TripPlanArtifact,
} from '@/types';
import type { PlanVariant } from '@/utils/travelPlan';
import { subagentLabel } from './subagents';

// 字符串数组去重工具
// 例如：["北京", "北京", "上海"] → ["北京", "上海"]
function uniqueStrings(items: string[]): string[] {
  const seen = new Set<string>();   // Set 用来记录已经出现过的字符串
  return items.filter((item) => {
    const normalized = item.trim();       // 去掉首尾空格
    if (!normalized || seen.has(normalized)) return false;  // 空字符串或重复则过滤掉
    seen.add(normalized);
    return true;
  });
}

// 安全地将任意值转为字符串，非字符串类型返回空串
function trimText(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

// 判断一个值是否是普通对象（不是数组、不是 null）
// TypeScript 中 value is Record<string, unknown> 是类型守卫，
//   告诉编译器"如果这个函数返回 true，那么 value 就是 Record<string, unknown> 类型"
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

// 制品概览描述符——包含方案的核心摘要信息
export interface ArtifactOverviewDescriptor {
  title: string;                    // 方案标题，如"北京 / 上海旅行方案"
  summary: string;                  // 方案摘要文字
  metrics: ArtifactOverviewMetric[]; // 概览指标列表（目的地、预算、校验状态等）
  warnings: string[];               // 风险警告列表
  subagentTrail: string[];          // 子 Agent 协作轨迹，如 ["研究", "规划", "预算"]
}

// 构建制品描述符的选项
interface BuildArtifactDeliveryDescriptorOptions {
  fallbackContent?: string;   // 当制品为空时的备用内容
  fallbackTitle?: string;     // 当制品为空时的备用标题
}

// 构建制品交付包的选项（扩展了描述符选项）
interface BuildArtifactDeliveryBundleOptions extends BuildArtifactDeliveryDescriptorOptions {
  executionReceipt?: ExecutionReceipt | null;  // 执行回执，记录 AI 的执行过程
}

// 构建方案对比变体的选项
interface BuildArtifactCompareVariantOptions {
  fallbackContent?: string;
  fallbackTitle?: string;
  id: string;                                    // 变体的唯一标识
  messageTimestamp?: string | null;               // 消息时间戳
  runId?: string | null;                          // 运行 ID
  source: 'artifact-history' | 'artifact-current'; // 来源：历史方案 或 当前方案
  subagentEvents?: SubagentEvent[];               // 子 Agent 事件列表
}

// 【核心】从制品中提取目的地列表
// 应用场景：在概览面板显示"目的地：北京 / 上海"
export function artifactDestinations(artifact: TripPlanArtifact | null | undefined): string[] {
  if (!artifact) return [];
  return uniqueStrings(
    (artifact.research.destinations || [])
      .map((item) => trimText(item))
      .filter(Boolean)
  );
}

// 【核心】从制品中提取预算摘要文字
// 应用场景：在概览面板显示"预算估算约 ¥3000"
// 优先级：执行预算总额 > 已生成执行预算明细 > 预算评估完成 > 含回退/时效提醒
export function artifactBudgetSummary(artifact: TripPlanArtifact | null | undefined): string {
  if (!artifact) return '';

  const summary = isRecord(artifact.budget.summary) ? artifact.budget.summary : {};
  const executionBudget = isRecord(artifact.budget.executionBudget) ? artifact.budget.executionBudget : {};
  const toolCount = typeof summary.toolCount === 'number' ? summary.toolCount : typeof summary.tool_count === 'number' ? summary.tool_count : 0;
  const totalEstimate =
    typeof executionBudget.total === 'number'
      ? executionBudget.total
      : typeof executionBudget.totalBudget === 'number'
        ? executionBudget.totalBudget
        : typeof summary.totalBudget === 'number'
          ? summary.totalBudget
          : null;

  if (typeof totalEstimate === 'number' && Number.isFinite(totalEstimate) && totalEstimate > 0) {
    return `预算估算约 ¥${Math.round(totalEstimate)}`;  // 有具体金额时显示
  }
  if (Object.keys(executionBudget).length > 0) return '已生成执行预算明细';   // 有明细但无总额
  if (toolCount > 0) return `已完成预算评估（${toolCount} 个预算工具）`;       // 有工具调用记录
  if (artifact.budget.fallbackSteps > 0 || artifact.budget.staleResultCount > 0) return '预算评估已完成，含回退/时效提醒';
  return '';  // 无预算信息
}

// 从制品中提取校验状态标签
// 应用场景：在概览面板显示"校验通过"或"校验未通过"
export function artifactVerificationLabel(artifact: TripPlanArtifact | null | undefined): string {
  if (!artifact) return '';
  if (artifact.verification.passed === true) return '校验通过';
  if (artifact.verification.passed === false) return '校验未通过';
  if (trimText(artifact.verification.summary)) return trimText(artifact.verification.summary);
  return '';
}

// 从制品中提取摘要文字
// 按优先级依次尝试：研究摘要 > 行程说明 > 校验摘要 > AI 回答 > 备用内容
function artifactSummary(artifact: TripPlanArtifact | null | undefined, fallbackContent: string): string {
  if (!artifact) return trimText(fallbackContent);
  return (
    trimText(artifact.research.summary) ||
    trimText(artifact.itinerary.explanation) ||
    trimText(artifact.verification.summary) ||
    trimText(artifact.answer) ||
    trimText(fallbackContent)
  );
}

// 从子 Agent 事件列表中提取协作轨迹（去重后的中文标签列表）
function artifactSubagentTrail(subagentEvents: SubagentEvent[]): string[] {
  return uniqueStrings(subagentEvents.map((event) => subagentLabel(trimText(event.subagent))));
}

// 从执行回执中提取子 Agent 事件
// 执行回执记录了 AI 执行过程中的每个阶段（segment），这里将其转换为统一的 SubagentEvent 格式
function subagentEventsFromExecutionReceipt(executionReceipt: ExecutionReceipt | null | undefined): SubagentEvent[] {
  if (!executionReceipt?.segments?.length) return [];

  return executionReceipt.segments.reduce<SubagentEvent[]>((events, segment) => {
      const subagent = trimText(segment.subagent);
      if (!subagent) return events;

      events.push({
        subagent,
        sequence: typeof segment.sequence === 'number' ? segment.sequence : null,
        trigger: trimText(segment.trigger) || null,
        description: trimText(segment.description) || null,
        skills: uniqueStrings((segment.skills || []).map((skill) => trimText(skill)).filter(Boolean)),
        toolNames: uniqueStrings((segment.toolNames || segment.toolsUsed || []).map((tool) => trimText(tool)).filter(Boolean)),
        status: trimText(segment.status) || null,
        summary: trimText(segment.summary) || null,
      });
      return events;
    }, []);
}

// 合并子 Agent 事件：优先使用直接传入的事件，否则从执行回执中提取
function resolveDeliverySubagentEvents(
  subagentEvents: SubagentEvent[],
  executionReceipt: ExecutionReceipt | null | undefined
): SubagentEvent[] {
  return subagentEvents.length > 0 ? subagentEvents : subagentEventsFromExecutionReceipt(executionReceipt);
}

// 生成文件名的基础部分（不含扩展名）
// 例如：planId 为 "BJ-001" 时，生成 "travel-plan-BJ-001"
function artifactFilenameBase(planId: string, destinations: string[]): string {
  const rawFilenameBase = planId ? `travel-plan-${planId}` : `travel-plan-${destinations.join('-') || 'artifact'}`;
  // 清理文件名中的非法字符（Windows 不允许 \/:*?"<>|）
  const normalized = rawFilenameBase
    .replace(/[\\/:*?"<>|]+/g, '-')   // 非法字符替换为横线
    .replace(/\s+/g, '-')             // 空格替换为横线
    .replace(/-+/g, '-')              // 多个横线合并为一个
    .replace(/^-|-$/g, '');           // 去掉首尾横线
  return normalized || 'travel-plan';
}

// 【核心】构建概览指标列表
// 应用场景：在概览面板显示多个指标卡片，如"目的地：北京/上海"、"预算摘要：¥3000"等
function artifactMetrics(
  artifact: TripPlanArtifact,
  destinations: string[],
  planId: string,
  budgetLine: string,
  verificationLine: string
): ArtifactOverviewMetric[] {
  const evidenceCount = artifact.research.evidence.length;   // 证据条目数
  const stepCount = artifact.itinerary.steps.length;         // 结构化步骤数
  const toolCount = uniqueStrings([...(artifact.research.sourceTools || []), ...(artifact.toolsUsed || [])]).length;  // 使用的工具数

  // 构建指标数组，为 null 的指标会被过滤掉
  const rawMetrics: Array<ArtifactOverviewMetric | null> = [
    destinations.length > 0 ? { label: '目的地', value: destinations.join(' / '), tone: 'info' } : null,
    planId ? { label: '计划编号', value: planId, tone: 'default' } : null,
    budgetLine ? { label: '预算摘要', value: budgetLine, tone: 'warning' } : null,
    verificationLine
      ? {
          label: '校验状态',
          value: verificationLine,
          tone: artifact.verification.passed === false ? 'danger' : artifact.verification.passed ? 'success' : 'default',
          // tone 表示指标的颜色语气：danger=红色, success=绿色, warning=橙色, info=蓝色, default=灰色
        }
      : null,
    stepCount > 0 ? { label: '结构化步骤', value: `${stepCount}`, tone: 'info' } : null,
    evidenceCount > 0 ? { label: '证据条目', value: `${evidenceCount}`, tone: 'info' } : null,
    toolCount > 0 ? { label: '工具触达', value: `${toolCount}`, tone: 'default' } : null,
  ];

  return rawMetrics.filter((item) => item !== null);  // 过滤掉 null 值
}

// 从制品中提取风险警告列表
function artifactWarnings(artifact: TripPlanArtifact): string[] {
  return [
    artifact.verification.issues.length > 0 ? `检测到 ${artifact.verification.issues.length} 个待处理风险` : '',
    artifact.verification.shouldRetry ? '当前方案建议再次校验' : '',
    artifact.budget.staleResultCount > 0 ? `预算链路存在 ${artifact.budget.staleResultCount} 条时效结果` : '',
    artifact.budget.fallbackSteps > 0 ? `预算链路包含 ${artifact.budget.fallbackSteps} 个回退步骤` : '',
  ].filter(Boolean);  // 过滤掉空字符串
}

// 构建摘要行列表（用于分享和导出）
function artifactSummaryLines(
  destinations: string[],
  planId: string,
  budgetLine: string,
  verificationLine: string,
  subagentTrail: string[]
): string[] {
  return [
    destinations.length > 0 ? `目的地：${destinations.join('、')}` : '',
    planId ? `计划编号：${planId}` : '',
    budgetLine ? `预算：${budgetLine}` : '',
    verificationLine ? `校验：${verificationLine}` : '',
    subagentTrail.length > 0 ? `子 Agent：${subagentTrail.join(' -> ')}` : '',
  ].filter(Boolean);
}

// 构建纯文本分享内容
function artifactShareContent(
  title: string,
  summaryLines: string[],
  toolsUsed: string,
  researchSummary: string,
  summary: string,
  fallbackContent: string
): string {
  return [
    title,
    ...summaryLines,
    toolsUsed ? `工具：${toolsUsed}` : '',
    researchSummary ? `研究摘要：${researchSummary}` : '',
    summary || fallbackContent,
  ]
    .filter(Boolean)
    .join('\n');  // 用换行符连接各部分
}

// 构建 HTML 报告的章节列表
function artifactHtmlSections(
  summaryLines: string[],
  warnings: string[],
  subagentTrail: string[],
  summary: string
): ArtifactDeliverySection[] {
  const sections: ArtifactDeliverySection[] = [];

  if (summaryLines.length > 0) {
    sections.push({ key: 'overview', title: '方案概览', items: summaryLines });
  }
  if (summary) {
    sections.push({ key: 'summary', title: '行程摘要', items: [summary] });
  }
  if (warnings.length > 0) {
    sections.push({ key: 'warnings', title: '风险提示', items: warnings });
  }
  if (subagentTrail.length > 0) {
    sections.push({ key: 'subagents', title: '多 Agent 协作轨迹', items: [subagentTrail.join(' -> ')] });
  }

  return sections;
}

// HTML 特殊字符转义，防止 XSS 攻击
// 例如：<script> → &lt;script&gt;
function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

// 【核心】构建制品交付描述符
// 这是整个文件最核心的函数，将原始制品数据转换为结构化的展示信息
// 应用场景：概览面板、分享功能、导出功能都需要用到这个描述符
export function buildArtifactDeliveryDescriptor(
  artifact: TripPlanArtifact | null | undefined,
  subagentEvents: SubagentEvent[],
  { fallbackContent = '', fallbackTitle = '旅行方案' }: BuildArtifactDeliveryDescriptorOptions = {}
): ArtifactDeliveryDescriptor {
  const subagentTrail = artifactSubagentTrail(subagentEvents);
  const summary = artifactSummary(artifact, fallbackContent);

  // 制品为空时，返回最小化的描述符
  if (!artifact) {
    const summaryLines = summary ? [summary] : [];
    return {
      title: fallbackTitle,
      filenameBase: 'travel-plan',
      summary,
      summaryLines,
      metrics: [],
      warnings: [],
      subagentTrail,
      shareContent: [fallbackTitle, summary].filter(Boolean).join('\n'),
      htmlDocumentTitle: fallbackTitle,
      htmlSections: artifactHtmlSections(summaryLines, [], subagentTrail, summary),
    };
  }

  // 制品存在时，提取所有关键信息
  const destinations = artifactDestinations(artifact);
  const budgetLine = artifactBudgetSummary(artifact);
  const verificationLine = artifactVerificationLabel(artifact);
  const planId = trimText(artifact.itinerary.planId);
  const researchSummary = trimText(artifact.research.summary);
  const title = destinations.length > 0 ? `${destinations.slice(0, 2).join(' / ')}旅行方案` : fallbackTitle;
  const warnings = artifactWarnings(artifact);
  const summaryLines = artifactSummaryLines(destinations, planId, budgetLine, verificationLine, subagentTrail);
  const toolsUsed = uniqueStrings([...(artifact.research.sourceTools || []), ...(artifact.toolsUsed || [])]).join(' / ');

  return {
    title,
    filenameBase: artifactFilenameBase(planId, destinations),
    summary,
    summaryLines,
    metrics: artifactMetrics(artifact, destinations, planId, budgetLine, verificationLine),
    warnings,
    subagentTrail,
    shareContent: artifactShareContent(title, summaryLines, toolsUsed, researchSummary, summary, fallbackContent),
    htmlDocumentTitle: `${title} | BitBlanket Travel Agent`,
    htmlSections: artifactHtmlSections(summaryLines, warnings, subagentTrail, summary),
  };
}

// 构建制品的 HTML 报告页面
// 生成一个完整的 HTML 文档，包含标题、摘要、各章节内容
export function buildArtifactDeliveryHtml(
  artifact: TripPlanArtifact | null | undefined,
  subagentEvents: SubagentEvent[],
  options: BuildArtifactDeliveryDescriptorOptions = {}
): string {
  const descriptor = buildArtifactDeliveryDescriptor(artifact, subagentEvents, options);
  const summaryHtml = descriptor.summary ? `<p class="delivery-summary">${escapeHtml(descriptor.summary)}</p>` : '';
  const sectionsHtml = descriptor.htmlSections
    .map(
      (section) => `
        <section class="delivery-section">
          <h2>${escapeHtml(section.title)}</h2>
          <ul>${section.items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
        </section>
      `
    )
    .join('');

  return `<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>${escapeHtml(descriptor.htmlDocumentTitle)}</title>
    <style>
      body { margin: 0; font-family: "Segoe UI", "PingFang SC", "Hiragino Sans GB", sans-serif; background: #f8fafc; color: #0f172a; }
      main { max-width: 900px; margin: 0 auto; padding: 32px 24px 48px; }
      .hero { border-radius: 24px; padding: 24px 28px; background: linear-gradient(135deg, #082f49 0%, #0f766e 100%); color: #fff; }
      .hero h1 { margin: 0; font-size: 30px; line-height: 1.2; }
      .delivery-summary { margin: 14px 0 0; font-size: 15px; line-height: 1.7; opacity: 0.92; }
      .delivery-section { margin-top: 18px; padding: 18px 20px; border-radius: 18px; background: #fff; border: 1px solid #e2e8f0; }
      .delivery-section h2 { margin: 0 0 10px; font-size: 16px; }
      .delivery-section ul { margin: 0; padding-left: 18px; display: grid; gap: 8px; }
      .delivery-section li { line-height: 1.6; }
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <h1>${escapeHtml(descriptor.title)}</h1>
        ${summaryHtml}
      </section>
      ${sectionsHtml}
    </main>
  </body>
</html>`;
}

// 【核心】构建制品交付包
// 交付包是最终对外输出的完整数据，包含描述符、原始数据、HTML、分享内容
// 应用场景：导出方案、分享方案时使用
export function buildArtifactDeliveryBundle(
  artifact: TripPlanArtifact | null | undefined,
  subagentEvents: SubagentEvent[],
  { executionReceipt = null, fallbackContent = '', fallbackTitle = '旅行方案' }: BuildArtifactDeliveryBundleOptions = {}
): ArtifactDeliveryBundle {
  const resolvedSubagentEvents = resolveDeliverySubagentEvents(subagentEvents, executionReceipt);
  const descriptor = buildArtifactDeliveryDescriptor(artifact, resolvedSubagentEvents, {
    fallbackContent,
    fallbackTitle,
  });

  return {
    schemaVersion: '2026-03-29',    // 数据格式版本号，用于兼容性检查
    descriptor,                       // 结构化描述信息
    artifact: artifact ? (artifact as unknown as Record<string, unknown>) : null,            // 原始制品数据
    executionReceipt: executionReceipt ? (executionReceipt as unknown as Record<string, unknown>) : null,  // 执行回执
    htmlContent: buildArtifactDeliveryHtml(artifact, resolvedSubagentEvents, {  // HTML 报告
      fallbackContent,
      fallbackTitle,
    }),
    share: {
      title: descriptor.title,        // 分享标题
      content: descriptor.shareContent, // 分享文本内容
    },
  };
}

// 构建制品概览描述符（轻量版，只包含概览信息）
// 应用场景：概览面板只需要标题、摘要、指标、警告，不需要完整的 HTML 和分享内容
export function buildArtifactOverviewDescriptor(
  artifact: TripPlanArtifact | null | undefined,
  subagentEvents: SubagentEvent[]
): ArtifactOverviewDescriptor | null {
  if (!artifact) return null;
  const descriptor = buildArtifactDeliveryDescriptor(artifact, subagentEvents);

  return {
    title: descriptor.title,
    summary: descriptor.summary,
    metrics: descriptor.metrics,
    warnings: descriptor.warnings,
    subagentTrail: descriptor.subagentTrail,
  };
}

// 格式化时间戳为易读的日期时间格式
// 例如："2026-03-29T14:30:00Z" → "2026-03-29 14:30"
export function formatArtifactSnapshotLabel(timestamp: string | null | undefined): string {
  const value = trimText(timestamp);
  if (!value) return '-';
  if (value.includes('T')) {   // ISO 8601 格式的时间戳包含 T
    return value.replace('T', ' ').replace('Z', '').slice(0, 16);
  }
  return value;
}

// 【核心】构建方案对比变体
// 应用场景：在"多方案对比"标签页中，每个历史方案或当前方案都是一个"变体"
//   用户可以对比不同变体的目的地、预算、行程等差异
export function buildArtifactCompareVariant(
  artifact: TripPlanArtifact | null | undefined,
  {
    fallbackContent = '',
    fallbackTitle = '历史方案',
    id,
    messageTimestamp = null,
    runId = null,
    source,
    subagentEvents = [],
  }: BuildArtifactCompareVariantOptions
): PlanVariant | null {
  if (!artifact) return null;

  const destinations = artifactDestinations(artifact);
  const planId = trimText(artifact.itinerary.planId);
  const snapshotLabel = formatArtifactSnapshotLabel(messageTimestamp);
  const titleBase = destinations.length > 0 ? destinations.slice(0, 2).join(' / ') : fallbackTitle;
  // 标题格式：优先显示计划编号，其次显示时间戳
  const title = planId ? `${titleBase} · ${planId}` : snapshotLabel !== '-' ? `${titleBase} · ${snapshotLabel}` : titleBase;

  return {
    id,
    title,
    content: buildArtifactSharePayload(artifact, subagentEvents, fallbackContent).content,
    artifact,
    source,
    runId,
    messageTimestamp,
  };
}

// 构建编辑上下文提示词
// 应用场景：用户点击"继续编辑"时，需要告诉 AI 当前方案的关键信息
//   例如："请基于当前结构化旅行方案继续编辑：\n- 目的地：北京、上海\n- 预算：¥3000"
export function buildArtifactEditingContext(artifact: TripPlanArtifact | null | undefined): string {
  if (!artifact) return '';
  const descriptor = buildArtifactDeliveryDescriptor(artifact, []);
  const lines = [...descriptor.summaryLines];
  if (descriptor.summary && !lines.includes(descriptor.summary)) {
    lines.push(descriptor.summary);
  }

  if (lines.length === 0) return '';
  return `请基于当前结构化旅行方案继续编辑：\n${lines.map((line) => `- ${line}`).join('\n')}`;
}

// 构建分享内容载荷（标题 + 纯文本 + HTML）
export function buildArtifactSharePayload(
  artifact: TripPlanArtifact | null | undefined,
  subagentEvents: SubagentEvent[],
  fallbackContent: string
): { title: string; content: string; htmlContent: string } {
  const bundle = buildArtifactDeliveryBundle(artifact, subagentEvents, { fallbackContent });
  return {
    title: bundle.share.title,
    content: bundle.share.content,
    htmlContent: bundle.htmlContent,
  };
}

// 构建导出描述符（标题 + 文件名基础 + 摘要行）
// 应用场景：导出方案为文件时，需要知道文件名和内容摘要
export function buildArtifactExportDescriptor(
  artifact: TripPlanArtifact | null | undefined,
  subagentEvents: SubagentEvent[],
  fallbackTitle: string = '旅行方案'
): { title: string; filenameBase: string; summaryLines: string[] } {
  const descriptor = buildArtifactDeliveryDescriptor(artifact, subagentEvents, { fallbackTitle });
  return {
    title: descriptor.title,
    filenameBase: descriptor.filenameBase,
    summaryLines: descriptor.summaryLines,
  };
}
