// 【核心】多方案对比表格组件
// 应用场景：用户生成了多个旅行方案后，在"多方案对比"标签页中
//   以表格形式横向对比各方案的定位、亮点、预算、校验状态等指标
//   例如：对比"省钱版"和"轻松版"的目的地、预算、证据条目等

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
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

// VariantComparisonTableProps 对比表格接收的参数
interface VariantComparisonTableProps {
  variants: PlanVariant[];  // 待对比的方案变体列表
}

// 基于纯文本内容构建对比行（当方案没有结构化制品数据时使用）
// 对比项：方案定位、核心亮点、适合人群
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
      // 提取方案内容的前3行作为亮点
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
      // 根据方案标题中的关键词推断适合人群
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

// 基于结构化制品数据构建对比行（当方案有制品数据时使用，信息更丰富）
// 对比项：方案、目的地、预算摘要、校验状态、证据条目、结构化步骤、快照时间
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

// 根据方案是否有制品数据，选择合适的对比行构建方式
function buildCompareRows(variants: PlanVariant[]): CompareRow[] {
  return variants.some((variant) => Boolean(variant.artifact))
    ? buildArtifactCompareRows(variants)   // 有制品数据 → 使用详细对比
    : buildTextCompareRows(variants);       // 无制品数据 → 使用文本对比
}

// 构建表格列定义
// 第一列是"对比项"，后面每个方案一列
function buildCompareColumns(variants: PlanVariant[]): ColumnsType<CompareRow> {
  return [
    {
      title: '对比项',
      dataIndex: 'metric',
      key: 'metric',
      width: 120,
      fixed: 'left',   // 对比项列固定在左侧，横向滚动时不会消失
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
    pagination={false}     // 不分页，一次展示所有对比行
    rowKey="key"
    columns={buildCompareColumns(variants)}
    dataSource={buildCompareRows(variants)}
    scroll={{ x: 720 }}   // 表格宽度超过720px时允许横向滚动
  />
);
