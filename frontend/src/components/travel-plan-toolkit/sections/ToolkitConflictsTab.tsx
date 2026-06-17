// 冲突检测标签页组件
// 应用场景：展示行程中检测到的所有冲突风险，按天分组显示
//   包含：冲突总数摘要标签 + 每日冲突卡片列表

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import type { DayPlanCard, ItineraryConflict } from '@/utils/travelPlan';
import type { CardEntry } from './types';
import { ConflictSummaryTag } from './conflicts-tab/ConflictSummaryTag';
import { DayConflictCard } from './conflicts-tab/DayConflictCard';

// ToolkitConflictsTabProps 冲突标签页接收的参数
interface ToolkitConflictsTabProps {
  cardEntries: CardEntry[];                                              // 每日行程卡片入口数据
  conflictMap: Map<string, ItineraryConflict[]>;                         // 按天分组的冲突映射
  messageId: string;                                                     // 消息 ID
  totalConflicts: number;                                                // 冲突总数
  onOneClickFix: (dayKey: string, dayIndex: number, day: DayPlanCard) => void;  // 一键修复回调
}

export const ToolkitConflictsTab: React.FC<ToolkitConflictsTabProps> = ({
  cardEntries,
  conflictMap,
  messageId,
  totalConflicts,
  onOneClickFix,
}) => (
  <div style={{ display: 'grid', gap: 10 }}>
    {/* 冲突总数摘要标签 */}
    <ConflictSummaryTag totalConflicts={totalConflicts} />
    {/* 每日冲突卡片列表 */}
    {cardEntries.map(({ day, dayIndex, dayKey }) => (
      <DayConflictCard
        key={`${messageId}-conflict-${dayKey}`}
        conflicts={conflictMap.get(dayKey) || []}
        day={day}
        dayIndex={dayIndex}
        dayKey={dayKey}
        messageId={messageId}
        onOneClickFix={onOneClickFix}
      />
    ))}
  </div>
);
