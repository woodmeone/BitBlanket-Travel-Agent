// 冲突风险相关的格式化工具
// 应用场景：行程冲突检测中，需要把距离数值格式化成易读的文字，以及根据风险等级显示不同颜色

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import type { ItineraryConflict } from '@/utils/travelPlan';

// 将米为单位的距离转换为"X.X km"格式
// 例如：formatDistance(3500) → "3.5 km"；formatDistance(0) → "-"
export function formatDistance(distanceM: number | undefined): string {
  if (!distanceM || distanceM <= 0) return '-';
  return `${(distanceM / 1000).toFixed(1)} km`;
}

// 【核心】根据冲突严重程度返回对应的颜色
// severity='high' → 红色（严重冲突，如两个景点时间重叠）
// severity='medium' → 琥珀色（中等冲突，如景点间距离太远）
// severity='low' → 棕色（轻微冲突，如行程偏紧凑）
export function riskColor(severity: ItineraryConflict['severity']): string {
  if (severity === 'high') return '#dc2626';    // 红色：高风险
  if (severity === 'medium') return '#d97706';  // 琥珀色：中风险
  return '#b45309';                             // 棕色：低风险
}
