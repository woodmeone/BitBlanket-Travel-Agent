'use client';

import React from 'react';
import { Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { PlanVariant } from '@/utils/travelPlan';
import type { CompareRow } from '../../shared';
import {
  artifactBudgetSummary,
  artifactDestinations,
  artifactVerificationLabel,
  formatArtifactSnapshotLabel,
} from '../../shared';

interface VariantComparisonTableProps {
  variants: PlanVariant[];
}

function buildTextCompareRows(variants: PlanVariant[]): CompareRow[] {
  return [
    {
      key: 'positioning',
      metric: '方案定位',
      values: Object.fromEntries(variants.map((variant) => [variant.id, variant.title])),
    },
    {
      key: 'highlights',
      metric: '核心亮点',
      values: Object.fromEntries(
        variants.map((variant) => {
          const lines = variant.content
            .split('\n')
            .map((line) => line.trim())
            .filter(Boolean);
          return [variant.id, lines.slice(0, 3).join('；') || '-'];
        })
      ),
    },
    {
      key: 'suitable',
      metric: '适合人群',
      values: Object.fromEntries(
        variants.map((variant) => {
          const lower = variant.title.toLowerCase();
          if (lower.includes('省')) return [variant.id, '预算优先 / 行程紧凑'];
          if (lower.includes('舒') || lower.includes('轻松')) return [variant.id, '体验优先 / 节奏轻松'];
          return [variant.id, '综合平衡 / 首次出行'];
        })
      ),
    },
  ];
}

function buildArtifactCompareRows(variants: PlanVariant[]): CompareRow[] {
  return [
    {
      key: 'title',
      metric: '方案',
      values: Object.fromEntries(variants.map((variant) => [variant.id, variant.title])),
    },
    {
      key: 'destinations',
      metric: '目的地',
      values: Object.fromEntries(
        variants.map((variant) => [variant.id, artifactDestinations(variant.artifact).join(' / ') || '-'])
      ),
    },
    {
      key: 'budget',
      metric: '预算摘要',
      values: Object.fromEntries(variants.map((variant) => [variant.id, artifactBudgetSummary(variant.artifact) || '-'])),
    },
    {
      key: 'verification',
      metric: '校验状态',
      values: Object.fromEntries(
        variants.map((variant) => [variant.id, artifactVerificationLabel(variant.artifact) || '-'])
      ),
    },
    {
      key: 'evidence',
      metric: '证据条目',
      values: Object.fromEntries(
        variants.map((variant) => [variant.id, `${variant.artifact?.research.evidence.length ?? 0}`])
      ),
    },
    {
      key: 'steps',
      metric: '结构化步骤',
      values: Object.fromEntries(
        variants.map((variant) => [variant.id, `${variant.artifact?.itinerary.steps.length ?? 0}`])
      ),
    },
    {
      key: 'updated',
      metric: '快照时间',
      values: Object.fromEntries(
        variants.map((variant) => [variant.id, formatArtifactSnapshotLabel(variant.messageTimestamp)])
      ),
    },
  ];
}

function buildCompareRows(variants: PlanVariant[]): CompareRow[] {
  return variants.some((variant) => Boolean(variant.artifact))
    ? buildArtifactCompareRows(variants)
    : buildTextCompareRows(variants);
}

function buildCompareColumns(variants: PlanVariant[]): ColumnsType<CompareRow> {
  return [
    {
      title: '对比项',
      dataIndex: 'metric',
      key: 'metric',
      width: 120,
      fixed: 'left',
    },
    ...variants.map((variant) => ({
      title: variant.title,
      dataIndex: ['values', variant.id],
      key: variant.id,
      render: (_: string, row: CompareRow) => row.values[variant.id] || '-',
    })),
  ];
}

export const VariantComparisonTable: React.FC<VariantComparisonTableProps> = ({ variants }) => (
  <Table
    size="small"
    pagination={false}
    rowKey="key"
    columns={buildCompareColumns(variants)}
    dataSource={buildCompareRows(variants)}
    scroll={{ x: 720 }}
  />
);
