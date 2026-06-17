// 'use client' —— 客户端组件声明
'use client';

import React from 'react';
// Button —— 按钮，Card —— 卡片容器，Space —— 间距容器，Table —— 表格组件
import { Button, Card, Space, Table } from 'antd';
// ColumnsType —— Ant Design 表格列定义的类型
import type { ColumnsType } from 'antd/es/table';
// SwapOutlined —— 交换图标，用于"让助手对比"按钮
import { SwapOutlined } from '@ant-design/icons';
// CitySummary —— 城市摘要数据类型
import type { CitySummary } from '@/types';
// 从 shared.tsx 引入工具函数和类型
import { buildCityProfile, budgetLabel, buildComparePrompt, type CompareTableRow, seasonLabel, walkLabel } from '../shared';

// CityExplorerComparePanelProps —— 城市对比面板的属性类型
interface CityExplorerComparePanelProps {
  compareCities: CitySummary[];          // 对比池中的城市列表（最多3个）
  onClearCompare: () => void;            // 清空对比池的回调
  onUsePrompt: (prompt: string) => void; // 使用 AI 提示词的回调
}

// 【核心】CityExplorerComparePanel —— 城市对比面板组件
// 功能：以表格形式并排展示最多3个城市的对比数据
// 对比维度包括：地区、预算、适合天数、步行强度、合适季节、旅行气质、编辑建议
// 应用场景：用户把成都、重庆、西安加入对比池后，
//           可以一目了然地看到三个城市在预算、步行强度等方面的差异，
//           也可以点击"让助手对比"让 AI 做更深入的分析
export const CityExplorerComparePanel: React.FC<CityExplorerComparePanelProps> = ({
  compareCities,
  onClearCompare,
  onUsePrompt,
}) => {
  // 对比池为空时不渲染任何内容
  if (compareCities.length === 0) return null;

  // 【核心】compareColumns —— 表格列定义
  // 第一列是"对比项"名称，后续每列对应一个城市
  // ColumnsType<CompareTableRow> 是 Ant Design 表格列的 TypeScript 类型
  const compareColumns: ColumnsType<CompareTableRow> = [
    {
      title: '对比项',          // 列标题
      dataIndex: 'metric',      // 对应数据中的 metric 字段
      key: 'metric',
      width: 140,
      fixed: 'left',            // 固定在左侧，水平滚动时不移动
      render: (value: string) => <span style={{ fontWeight: 700, color: '#1f2937' }}>{value}</span>,
    },
    // ... 是展开运算符，把数组中的每个元素"展开"到当前位置
    // 这里为每个对比城市动态生成一列
    ...compareCities.map((city) => ({
      title: city.name,                    // 列标题是城市名称
      dataIndex: ['values', city.id],      // 对应数据中 values[city.id]
      key: city.id,
      width: 220,
      render: (_value: string, row: CompareTableRow) => (
        <div style={{ whiteSpace: 'pre-wrap', color: '#334155', lineHeight: 1.7 }}>{row.values[city.id] || '-'}</div>
      ),
    })),
  ];

  // 【核心】compareRows —— 表格行数据
  // 每行代表一个对比维度，values 记录每个城市在该维度的值
  // Object.fromEntries() 把 [city.id, 值] 数组转成 { city.id: 值 } 对象
  const compareRows: CompareTableRow[] = [
    {
      key: 'region',
      metric: '地区',
      values: Object.fromEntries(compareCities.map((city) => [city.id, city.region])),
    },
    {
      key: 'budget',
      metric: '预算',
      values: Object.fromEntries(
        compareCities.map((city) => [city.id, `¥${city.avg_budget_per_day} / ${budgetLabel(buildCityProfile(city).budgetLevel)}`])
      ),
    },
    {
      key: 'days',
      metric: '适合天数',
      values: Object.fromEntries(compareCities.map((city) => [city.id, buildCityProfile(city).tripDuration])),
    },
    {
      key: 'walk',
      metric: '步行强度',
      values: Object.fromEntries(compareCities.map((city) => [city.id, walkLabel(buildCityProfile(city).walkIntensity)])),
    },
    {
      key: 'season',
      metric: '合适季节',
      values: Object.fromEntries(compareCities.map((city) => [city.id, seasonLabel(city.best_seasons)])),
    },
    {
      key: 'style',
      metric: '旅行气质',
      values: Object.fromEntries(compareCities.map((city) => [city.id, buildCityProfile(city).styleLabel])),
    },
    {
      key: 'note',
      metric: '编辑建议',
      values: Object.fromEntries(compareCities.map((city) => [city.id, buildCityProfile(city).recommendation])),
    },
  ];

  return (
    // 卡片容器：暖黄色边框和背景，与对比池的视觉风格一致
    <Card
      size="small"
      style={{ borderRadius: 16, border: '1px solid #fde68a', background: 'linear-gradient(180deg, #fffdf2 0%, #ffffff 100%)' }}
      styles={{ body: { padding: 14 } }}
    >
      {/* 标题行：左侧标题 + 说明，右侧操作按钮 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
        <div>
          {/* 城市对比池标题 */}
          <div style={{ fontSize: 15, fontWeight: 700, color: '#92400e' }}>{/* 城市对比池 */}{'城市对比池'}</div>
          <div style={{ fontSize: 12, color: '#78716c' }}>
            {/* 最多放3个真实城市，快速比较后直接继续规划 */}
            {'最多放 3 个真实城市，快速比较后直接继续规划。'}
          </div>
        </div>
        <Space wrap>
          {/* "让助手对比"按钮 —— 把对比池城市名发给 AI 做深度分析 */}
          <Button icon={<SwapOutlined />} onClick={() => onUsePrompt(buildComparePrompt(compareCities.map((city) => city.name)))}>
            {'让助手对比'}
          </Button>
          {/* "清空"按钮 —— 清空对比池 */}
          <Button onClick={onClearCompare}>{'清空'}</Button>
        </Space>
      </div>
      {/* 对比表格：不分页，行 key 为 key 字段，水平滚动宽度 780px */}
      <Table size="small" pagination={false} rowKey="key" columns={compareColumns} dataSource={compareRows} scroll={{ x: 780 }} />
    </Card>
  );
};
