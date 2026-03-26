'use client';

import React from 'react';
import type { PracticalInfoCard } from '@/utils/travelPlan';
import { PracticalInfoGrid } from './practical-tab/PracticalInfoGrid';

interface ToolkitPracticalTabProps {
  messageId: string;
  practicalInfo: PracticalInfoCard[];
}

export const ToolkitPracticalTab: React.FC<ToolkitPracticalTabProps> = ({ messageId, practicalInfo }) => (
  <PracticalInfoGrid messageId={messageId} practicalInfo={practicalInfo} />
);
