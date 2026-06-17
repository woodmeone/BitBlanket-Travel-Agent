// 每日冲突卡片组件
// 应用场景：在冲突检测标签页中，每天对应一张卡片，展示当天的所有行程冲突

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import { Card } from 'antd';
import type { DayPlanCard, ItineraryConflict } from '@/utils/travelPlan';
import { ConflictCardContent } from './ConflictCardContent';

// DayConflictCardProps 每日冲突卡片接收的参数
interface DayConflictCardProps {
  conflicts: ItineraryConflict[];                                              // 当天的冲突列表
  day: DayPlanCard;                                                            // 当天的行程数据
  dayIndex: number;                                                            // 天数索引
  dayKey: string;                                                              // 当天的唯一标识键
  messageId: string;                                                           // 消息 ID
  onOneClickFix: (dayKey: string, dayIndex: number, day: DayPlanCard) => void; // 一键修复冲突的回调
}

export const DayConflictCard: React.FC<DayConflictCardProps> = ({
  conflicts,
  day,
  dayIndex,
  dayKey,
  messageId,
  onOneClickFix,
}) => (
  <Card key={`${messageId}-conflict-${dayKey}`} size="small" title={day.dayLabel}>
    <ConflictCardContent conflicts={conflicts} day={day} dayIndex={dayIndex} dayKey={dayKey} onOneClickFix={onOneClickFix} />
  </Card>
);
