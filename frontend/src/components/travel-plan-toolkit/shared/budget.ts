// 预算模式与滑块数值的转换工具
// 应用场景：用户在预算面板上拖动滑块时，需要把滑块的数字（0-100）转换成"省钱/平衡/舒适"三种模式

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import type { BudgetMode } from './types';

// 【核心】将滑块数值转换为预算模式
// 例如：用户把滑块拖到 20 → 返回 'saving'（省钱模式）；拖到 80 → 返回 'comfort'（舒适模式）
export function sliderToMode(value: number): BudgetMode {
  if (value <= 33) return 'saving';   // 滑块值 ≤33 → 省钱模式
  if (value >= 67) return 'comfort';  // 滑块值 ≥67 → 舒适模式
  return 'balanced';                  // 中间值 → 平衡模式
}

// 将预算模式转换为滑块数值（反向操作）
// 用于初始化滑块位置：当模式是"省钱"时，滑块显示在 10 的位置
export function modeToSliderValue(mode: BudgetMode): number {
  if (mode === 'saving') return 10;    // 省钱模式 → 滑块在 10
  if (mode === 'comfort') return 90;   // 舒适模式 → 滑块在 90
  return 50;                           // 平衡模式 → 滑块在中间 50
}
