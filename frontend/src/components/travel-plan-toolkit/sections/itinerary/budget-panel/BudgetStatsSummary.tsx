'use client';

import React from 'react';
import { Card, Statistic, Tag } from 'antd';
import type { BudgetProjection } from '@/utils/travelPlan';

interface BudgetStatsSummaryProps {
  budgetProjection: BudgetProjection;
  childFriendlyBudget: number;
  familyBudget: number;
}

export const BudgetStatsSummary: React.FC<BudgetStatsSummaryProps> = ({
  budgetProjection,
  childFriendlyBudget,
  familyBudget,
}) => (
  <div style={{ display: 'grid', gap: 10 }}>
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
      <Tag color="blue">总预算：¥{budgetProjection.totalBudget}</Tag>
      <Tag color="cyan">住宿：{Math.round(budgetProjection.hotelShare * 100)}%</Tag>
      <Tag color="orange">餐饮：{Math.round(budgetProjection.foodShare * 100)}%</Tag>
      <Tag color="purple">交通：{Math.round(budgetProjection.trafficShare * 100)}%</Tag>
    </div>

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
