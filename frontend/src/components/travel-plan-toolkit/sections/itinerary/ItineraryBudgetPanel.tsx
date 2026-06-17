// 预算面板组件——展示行程的预算概览和操作工具
// 应用场景：在行程标签页中，用户可以查看预算统计、切换预算模式、快速微调预算

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import { Card } from 'antd';
import type { BudgetProjection, ConfidenceSummary } from '@/utils/travelPlan';
import type { BudgetMode, QuickRefineAction } from '../../shared';
import { BudgetConfidencePanel } from './budget-panel/BudgetConfidencePanel';
import { BudgetModeToolbar } from './budget-panel/BudgetModeToolbar';
import { BudgetQuickRefineBar } from './budget-panel/BudgetQuickRefineBar';
import { BudgetStatsSummary } from './budget-panel/BudgetStatsSummary';

// ItineraryBudgetPanelProps 预算面板接收的参数
interface ItineraryBudgetPanelProps {
  budgetMode: BudgetMode;                                  // 当前预算模式（省钱/平衡/舒适）
  budgetProjection: BudgetProjection;                      // 预算预测数据
  childFriendlyBudget: number;                             // 亲子轻量版预算
  confidence: ConfidenceSummary;                           // 预算结果可信度
  familyBudget: number;                                    // 家庭总价预算
  onBudgetModeChange: (mode: BudgetMode) => void;          // 切换预算模式的回调
  onExportImage: () => void;                                // 导出图片的回调
  onQuickRefine: (action: QuickRefineAction) => void;      // 快速微调的回调
  onShare: () => void;                                      // 分享的回调
  quickRefineActions: QuickRefineAction[];                  // 快速微调操作列表
}

export const ItineraryBudgetPanel: React.FC<ItineraryBudgetPanelProps> = ({
  budgetMode,
  budgetProjection,
  childFriendlyBudget,
  confidence,
  familyBudget,
  onBudgetModeChange,
  onExportImage,
  onQuickRefine,
  onShare,
  quickRefineActions,
}) => (
  <Card size="small">
    <div style={{ display: 'grid', gap: 10 }}>
      {/* 预算模式工具栏（滑块 + 导出/分享按钮） */}
      <BudgetModeToolbar
        budgetMode={budgetMode}
        onBudgetModeChange={onBudgetModeChange}
        onExportImage={onExportImage}
        onShare={onShare}
      />
      {/* 预算统计摘要（人均、家庭、亲子、日均） */}
      <BudgetStatsSummary
        budgetProjection={budgetProjection}
        childFriendlyBudget={childFriendlyBudget}
        familyBudget={familyBudget}
      />
      {/* 快速微调按钮栏 */}
      <BudgetQuickRefineBar quickRefineActions={quickRefineActions} onQuickRefine={onQuickRefine} />
      {/* 预算可信度面板 */}
      <BudgetConfidencePanel confidence={confidence} />
    </div>
  </Card>
);
