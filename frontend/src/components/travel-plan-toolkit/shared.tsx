// 【核心】统一导出文件——把 shared/ 目录下的所有工具函数和类型集中导出
// 其他文件只需要 import from './shared' 就能使用所有工具，不用逐个文件导入
// 这种模式叫"桶文件"（barrel file），是前端项目常见的组织方式

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

// 导出类型定义
export type { BudgetMode, CompareRow, QuickRefineAction } from './shared/types';
// 导出预算模式转换工具
export { sliderToMode, modeToSliderValue } from './shared/budget';
// 导出时间线组件和小贴士处理工具
export { compactTips, PeriodTimeline } from './shared/timeline';
// 导出风险格式化工具
export { formatDistance, riskColor } from './shared/risk';
// 导出实用信息样式工具
export { practicalToneStyle, practicalToneLabel } from './shared/practical';
// 导出提醒阶段样式工具
export { reminderPhaseMeta } from './shared/reminders';
// 导出清单状态样式工具
export { checklistStatusMeta } from './shared/checklist';
// 导出子 Agent 标签映射
export { subagentLabel } from './shared/subagents';
// 导出行程内容识别工具
export { looksLikeItineraryContent } from './shared/content';
// 导出制品构建与导出工具
export {
  artifactBudgetSummary,
  buildArtifactCompareVariant,
  buildArtifactDeliveryBundle,
  buildArtifactDeliveryDescriptor,
  buildArtifactDeliveryHtml,
  artifactDestinations,
  formatArtifactSnapshotLabel,
  artifactVerificationLabel,
  buildArtifactExportDescriptor,
  buildArtifactOverviewDescriptor,
  buildArtifactEditingContext,
  buildArtifactSharePayload,
} from './shared/artifact';
