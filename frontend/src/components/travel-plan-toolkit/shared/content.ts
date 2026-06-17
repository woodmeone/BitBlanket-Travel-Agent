// 行程内容识别工具
// 应用场景：当 AI 返回的内容可能是纯文本也可能是结构化行程时，
//   需要判断内容是否"看起来像行程"，以决定用哪种方式展示

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import type { DayPlanCard } from '@/utils/travelPlan';

// 【核心】判断一段文本内容是否看起来像行程安排
// 判断逻辑：
//   1. 如果已经有2张以上的结构化日程卡片，直接认为是行程内容
//   2. 如果文本中包含"上午"、"下午"、"预算"、"第X天"等行程关键词，也认为是行程内容
// 例如："上午游览故宫，下午逛王府井" → 返回 true
// 例如："今天天气不错" → 返回 false
export function looksLikeItineraryContent(content: string, cards: DayPlanCard[]): boolean {
  if (cards.length >= 2) return true;
  if (/(上午|下午|晚上|预算|小贴士|tips|day\s*\d+|第.{1,4}天|方案|路线|景点)/i.test(content)) return true;
  return false;
}
