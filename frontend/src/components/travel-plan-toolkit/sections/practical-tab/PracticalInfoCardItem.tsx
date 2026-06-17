// 实用信息卡片项组件——单条实用信息的展示
// 应用场景：在实用信息网格中，每张卡片展示一条实用信息
//   例如：标题"当地天气" + 语气标签"建议" + 内容"晴朗适合出行"
//   卡片背景色随语气变化：建议=绿色、注意=橙色、常规=灰色

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import { InfoCircleOutlined } from '@ant-design/icons';
import type { PracticalInfoCard } from '@/utils/travelPlan';
import { practicalToneStyle } from '../../shared';
import { PracticalToneTag } from './PracticalToneTag';

// PracticalInfoCardItemProps 实用信息卡片项接收的参数
interface PracticalInfoCardItemProps {
  cardKey: string;                    // 卡片唯一标识键
  item: PracticalInfoCard;            // 实用信息数据
}

export const PracticalInfoCardItem: React.FC<PracticalInfoCardItemProps> = ({ cardKey, item }) => {
  const toneStyle = practicalToneStyle(item.tone);  // 获取语气对应的颜色样式

  return (
    <div
      key={cardKey}
      style={{
        borderRadius: 14,
        padding: 14,
        background: toneStyle.background,            // 背景色随语气变化
        border: `1px solid ${toneStyle.border}`,     // 边框色随语气变化
        color: toneStyle.color,                       // 文字色随语气变化
      }}
    >
      {/* 标题行：图标 + 标题 + 语气标签 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
          marginBottom: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <InfoCircleOutlined />
          <div style={{ fontWeight: 700 }}>{item.title}</div>
        </div>
        <PracticalToneTag tone={item.tone} />
      </div>
      {/* 详细内容 */}
      <div style={{ fontSize: 13, lineHeight: 1.7 }}>{item.value}</div>
    </div>
  );
};
