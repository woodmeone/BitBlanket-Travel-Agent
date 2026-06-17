// 【核心】标签页组件的统一导出文件（桶文件）
// 旅行行程工具包包含8个标签页组件，通过这个文件集中导出
// 上层组件只需要 import from './sections' 即可使用所有标签页

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

export { ToolkitOverviewPanel } from './sections/ToolkitOverviewPanel';       // 行程概览面板
export { ToolkitItineraryTab } from './sections/ToolkitItineraryTab';       // 每日行程标签页
export { ToolkitCompareTab } from './sections/ToolkitCompareTab';           // 多方案对比标签页
export { ToolkitChecklistTab } from './sections/ToolkitChecklistTab';       // 执行清单标签页
export { ToolkitFavoritesTab } from './sections/ToolkitFavoritesTab';       // 景点收藏标签页
export { ToolkitPracticalTab } from './sections/ToolkitPracticalTab';       // 实用信息标签页
export { ToolkitRemindersTab } from './sections/ToolkitRemindersTab';       // 出发提醒标签页
export { ToolkitConflictsTab } from './sections/ToolkitConflictsTab';       // 冲突检测标签页
