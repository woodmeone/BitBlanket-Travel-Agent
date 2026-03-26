'use client';

import React from 'react';
import type { PlanVariant } from '@/utils/travelPlan';
import { CompareEmptyState } from './compare-tab/CompareEmptyState';
import { VariantActionBar } from './compare-tab/VariantActionBar';
import { VariantComparisonTable } from './compare-tab/VariantComparisonTable';

interface ToolkitCompareTabProps {
  loading?: boolean;
  source?: 'artifact-history' | 'text';
  variants: PlanVariant[];
  onChooseVariant: (variant: PlanVariant) => void;
}

export const ToolkitCompareTab: React.FC<ToolkitCompareTabProps> = ({
  loading = false,
  source = 'text',
  variants,
  onChooseVariant,
}) => {
  if (loading && variants.length === 0) {
    return <div style={{ fontSize: 13, color: '#64748b' }}>正在加载当前会话的 artifact 历史方案...</div>;
  }
  if (variants.length < 2) return <CompareEmptyState />;

  return (
    <div style={{ display: 'grid', gap: 12 }}>
      {source === 'artifact-history' && (
        <div style={{ fontSize: 12, color: '#0f766e' }}>当前对比结果基于本会话 persisted artifact history。</div>
      )}
      <VariantComparisonTable variants={variants} />
      <VariantActionBar variants={variants} onChooseVariant={onChooseVariant} />
    </div>
  );
};
