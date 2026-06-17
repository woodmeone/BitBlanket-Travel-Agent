// 预算统计摘要组件
// 应用场景：在预算面板中展示预算的各类统计数据
//   包括：总预算、住宿/餐饮/交通占比、人均预估、家庭总价、亲子轻量版、日均预算

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import { Card, Statistic, Tag } from 'antd';
import type { BudgetProjection } from '@/utils/travelPlan';

// BudgetStatsSummaryProps 预算统计摘要接收的参数
interface BudgetStatsSummaryProps {
  budgetProjection: BudgetProjection;  // 预算预测数据
  childFriendlyBudget: number;         // 亲子轻量版预算
  familyBudget: number;                // 家庭总价预算
}

export const BudgetStatsSummary: React.FC<BudgetStatsSummaryProps> = ({
  budgetProjection,
  childFriendlyBudget,
  familyBudget,
}) => (
  <div style={{ display: 'grid', gap: 10 }}>
    {/* 预算占比标签行 */}
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
      <Tag color="blue">总预算：¥{budgetProjection.totalBudget}</Tag>
      <Tag color="cyan">住宿：{Math.round(budgetProjection.hotelShare * 100)}%</Tag>
      <Tag color="orange">餐饮：{Math.round(budgetProjection.foodShare * 100)}%</Tag>
      <Tag color="purple">交通：{Math.round(budgetProjection.trafficShare * 100)}%</Tag>
    </div>

    {/* 四个统计卡片，自适应网格布局 */}
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
        gap: 10,
      }}
    >
      <Card size="small" styles={{ body: { padding: 10 } }}>
        <Statistic title="人均预估" value={budgetProjection.totalBudget} prefix="¥" styles={{ content: { fontSize: 18 } }} />
      </Card>
      <Card size="small" styles={{ body: { padding: 10 } }}>
        <Statistic title="家庭总价" value={familyBudget} prefix="¥" styles={{ content: { fontSize: 18 } }} />
      </Card>
      <Card size="small" styles={{ body: { padding: 10 } }}>
        <Statistic title="亲子轻量版" value={childFriendlyBudget} prefix="¥" styles={{ content: { fontSize: 18 } }} />
      </Card>
      <Card size="small" styles={{ body: { padding: 10 } }}>
        <Statistic title="日均预算" value={budgetProjection.perDayBudget} prefix="¥" styles={{ content: { fontSize: 18 } }} />
      </Card>
    </div>
  </div>
);
