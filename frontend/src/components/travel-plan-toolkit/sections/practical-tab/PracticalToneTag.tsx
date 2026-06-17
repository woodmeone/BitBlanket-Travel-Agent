// 实用信息语气标签组件
// 应用场景：在实用信息卡片中，显示信息的语气类型标签
//   例如："建议"（绿色）、"注意"（橙色）、"常规"（灰色）

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import type { PracticalInfoCard } from '@/utils/travelPlan';
import { practicalToneLabel, practicalToneStyle } from '../../shared';

// PracticalToneTagProps 语气标签接收的参数
interface PracticalToneTagProps {
  tone: PracticalInfoCard['tone'];  // 信息语气：'good' | 'warn' | 其他
}

export const PracticalToneTag: React.FC<PracticalToneTagProps> = ({ tone }) => {
  const toneStyle = practicalToneStyle(tone);  // 获取语气对应的颜色样式
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        borderRadius: 999,                       // 胶囊形状
        padding: '2px 8px',
        fontSize: 11,
        fontWeight: 700,
        border: `1px solid ${toneStyle.border}`,
        background: '#ffffffb8',                 // 半透明白色背景
        color: toneStyle.color,
      }}
    >
      {practicalToneLabel(tone)}
    </span>
  );
};
