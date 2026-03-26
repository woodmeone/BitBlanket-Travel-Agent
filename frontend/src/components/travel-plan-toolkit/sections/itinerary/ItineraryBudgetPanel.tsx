'use client';

import React from 'react';
import { Card } from 'antd';
import type { BudgetProjection, ConfidenceSummary } from '@/utils/travelPlan';
import type { BudgetMode, QuickRefineAction } from '../../shared';
import { BudgetConfidencePanel } from './budget-panel/BudgetConfidencePanel';
import { BudgetModeToolbar } from './budget-panel/BudgetModeToolbar';
import { BudgetQuickRefineBar } from './budget-panel/BudgetQuickRefineBar';
import { BudgetStatsSummary } from './budget-panel/BudgetStatsSummary';

interface ItineraryBudgetPanelProps {
  budgetMode: BudgetMode;
  budgetProjection: BudgetProjection;
  childFriendlyBudget: number;
  confidence: ConfidenceSummary;
  familyBudget: number;
  onBudgetModeChange: (mode: BudgetMode) => void;
  onExportImage: () => void;
  onQuickRefine: (action: QuickRefineAction) => void;
  onShare: () => void;
  quickRefineActions: QuickRefineAction[];
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
      <BudgetModeToolbar
        budgetMode={budgetMode}
        onBudgetModeChange={onBudgetModeChange}
        onExportImage={onExportImage}
        onShare={onShare}
      />
      <BudgetStatsSummary
        budgetProjection={budgetProjection}
        childFriendlyBudget={childFriendlyBudget}
        familyBudget={familyBudget}
      />
      <BudgetQuickRefineBar quickRefineActions={quickRefineActions} onQuickRefine={onQuickRefine} />
      <BudgetConfidencePanel confidence={confidence} />
    </div>
  </Card>
);
