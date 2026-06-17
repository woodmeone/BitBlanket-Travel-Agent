// 出发提醒（Reminders）的阶段样式配置
// 应用场景：提醒卡片上需要标注"这是出发前几天的提醒"，不同阶段用不同颜色区分

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import type { ReminderItem } from '@/utils/travelPlan';

// 根据提醒的阶段（phase），返回对应的颜色和副标题
// phase 是 ReminderItem 类型中的 phase 字段，表示提醒距离出发的时间
// 例如：T-1 表示出发前1天，T-3 表示出发前3天，T-7 表示出发前1周
export function reminderPhaseMeta(phase: ReminderItem['phase']): { color: string; subtitle: string } {
  if (phase === 'T-1') return { color: 'volcano', subtitle: '出发前一天' };   // 火山红色，最紧急
  if (phase === 'T-3') return { color: 'cyan', subtitle: '出发前三天' };       // 青色，中等紧急
  return { color: 'blue', subtitle: '出发前一周' };                            // 蓝色，提前提醒
}
