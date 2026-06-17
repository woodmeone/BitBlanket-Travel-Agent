// 提醒阶段标签组件
// 应用场景：在提醒卡片中，显示提醒的阶段（T-1/T-3/T-7）和对应的中文副标题
//   例如：T-1 标签旁边显示"出发前一天"

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import { Tag } from 'antd';
import type { ReminderItem } from '@/utils/travelPlan';
import { reminderPhaseMeta } from '../../shared';

// ReminderPhaseTagProps 阶段标签接收的参数
interface ReminderPhaseTagProps {
  phase: ReminderItem['phase'];  // 提醒阶段，如 "T-1"、"T-3"、"T-7"
}

export const ReminderPhaseTag: React.FC<ReminderPhaseTagProps> = ({ phase }) => {
  const meta = reminderPhaseMeta(phase);  // 获取阶段对应的颜色和副标题
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
      <Tag color={meta.color} style={{ marginInlineEnd: 0 }}>
        {phase}
      </Tag>
      <span style={{ fontSize: 12, color: '#64748b', fontWeight: 500 }}>{meta.subtitle}</span>
    </div>
  );
};
