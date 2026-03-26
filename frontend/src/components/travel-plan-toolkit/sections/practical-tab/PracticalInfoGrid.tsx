'use client';

import React from 'react';
import type { PracticalInfoCard } from '@/utils/travelPlan';
import { PracticalInfoCardItem } from './PracticalInfoCardItem';

interface PracticalInfoGridProps {
  messageId: string;
  practicalInfo: PracticalInfoCard[];
}

export const PracticalInfoGrid: React.FC<PracticalInfoGridProps> = ({ messageId, practicalInfo }) => (
  <div
    style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
      gap: 10,
    }}
  >
    {practicalInfo.map((item) => (
      <PracticalInfoCardItem key={`${messageId}-practical-${item.id}`} cardKey={`${messageId}-practical-${item.id}`} item={item} />
    ))}
  </div>
);
