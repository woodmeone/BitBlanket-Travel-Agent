// 实用信息（Practical）的语气样式配置
// 应用场景：实用信息卡片有"建议"、"注意"、"常规"三种语气，
//   例如"当地天气晴朗适合出行"是建议（绿色），"景区需提前预约"是注意（橙色）

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import type { PracticalInfoCard } from '@/utils/travelPlan';

// 根据信息语气（tone），返回对应的颜色样式
// tone='good' → 绿色（正面建议）；tone='warn' → 橙色（需要注意）；其他 → 灰色（常规信息）
export function practicalToneStyle(
  tone: PracticalInfoCard['tone']
): { background: string; border: string; color: string } {
  if (tone === 'good') return { background: '#ecfdf5', border: '#a7f3d0', color: '#065f46' };   // 绿色系：正面建议
  if (tone === 'warn') return { background: '#fff7ed', border: '#fed7aa', color: '#9a3412' };   // 橙色系：需要留意
  return { background: '#f8fafc', border: '#cbd5e1', color: '#334155' };                        // 灰色系：常规信息
}

// 根据信息语气（tone），返回中文标签
export function practicalToneLabel(tone: PracticalInfoCard['tone']): string {
  if (tone === 'good') return '建议';   // 正面建议
  if (tone === 'warn') return '注意';   // 需要注意
  return '常规';                        // 普通信息
}
