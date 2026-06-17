// 各标签页（Tab）组件共用的类型定义
// 这里的类型主要服务于每日行程卡片的渲染

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import type { DayPlanCard } from '@/utils/travelPlan';

// CardEntry 每日行程卡片的入口数据
// 应用场景：在行程标签页中，每一天对应一张卡片，CardEntry 封装了卡片需要的所有信息
export interface CardEntry {
  day: DayPlanCard;      // 当天的行程数据（景点、时间、小贴士等）
  dayIndex: number;      // 天数索引（从0开始），如第1天=0，第2天=1
  dayKey: string;        // 当天的唯一标识键，如"day-0"、"day-1"，用于 React 渲染时的 key
}
