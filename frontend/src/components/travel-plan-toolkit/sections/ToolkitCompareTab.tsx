// 多方案对比标签页组件
// 应用场景：用户生成了多个旅行方案后，在此标签页横向对比各方案的差异
//   包含：对比表格（目的地、预算、校验状态等）和方案选择操作栏

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import type { PlanVariant } from '@/utils/travelPlan';
import { CompareEmptyState } from './compare-tab/CompareEmptyState';
import { VariantActionBar } from './compare-tab/VariantActionBar';
import { VariantComparisonTable } from './compare-tab/VariantComparisonTable';

// ToolkitCompareTabProps 对比标签页接收的参数
interface ToolkitCompareTabProps {
  loading?: boolean;                                       // 是否正在加载历史方案
  source?: 'artifact-history' | 'text';                    // 方案来源：制品历史 或 纯文本
  variants: PlanVariant[];                                 // 待对比的方案变体列表
  onChooseVariant: (variant: PlanVariant) => void;        // 选中某个方案的回调
}

export const ToolkitCompareTab: React.FC<ToolkitCompareTabProps> = ({
  loading = false,
  source = 'text',
  variants,
  onChooseVariant,
}) => {
  // 加载中且无方案时，显示加载提示
  if (loading && variants.length === 0) {
    return <div style={{ fontSize: 13, color: '#64748b' }}>正在加载当前会话的 artifact 历史方案...</div>;
  }
  // 方案少于2个时，显示空状态提示
  if (variants.length < 2) return <CompareEmptyState />;

  return (
    <div style={{ display: 'grid', gap: 12 }}>
      {/* 来源提示 */}
      {source === 'artifact-history' && (
        <div style={{ fontSize: 12, color: '#0f766e' }}>当前对比结果基于本会话 persisted artifact history。</div>
      )}
      {/* 对比表格 */}
      <VariantComparisonTable variants={variants} />
      {/* 方案选择操作栏 */}
      <VariantActionBar variants={variants} onChooseVariant={onChooseVariant} />
    </div>
  );
};
