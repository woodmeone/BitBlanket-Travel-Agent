// 小贴士展示区块组件
// 应用场景：每日行程卡片底部展示当天的旅行小贴士，如"记得带防晒霜"
//   支持展开/收起，收起时只显示2条

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import { Button } from 'antd';

// ItineraryTipsBlockProps 小贴士区块接收的参数
interface ItineraryTipsBlockProps {
  dayKey: string;                    // 当天的唯一标识键
  hiddenTipCount: number;            // 隐藏的小贴士数量
  tipsExpanded: boolean;             // 是否展开全部小贴士
  visibleTips: string[];             // 当前可见的小贴士列表
  onToggleTips: (dayKey: string) => void;  // 切换展开/收起的回调
}

export const ItineraryTipsBlock: React.FC<ItineraryTipsBlockProps> = ({
  dayKey,
  hiddenTipCount,
  tipsExpanded,
  visibleTips,
  onToggleTips,
}) => {
  if (visibleTips.length === 0) return null;  // 没有小贴士时不渲染

  return (
    <div style={{ display: 'grid', gap: 4 }}>
      {visibleTips.map((tip, index) => (
        <div key={`${dayKey}-tip-${index}`} style={{ fontSize: 12, color: '#0f766e' }}>
          小贴士：{tip}
        </div>
      ))}
      {/* 展开更多 / 收起 按钮 */}
      {hiddenTipCount > 0 && (
        <Button type="link" size="small" style={{ width: 'fit-content', padding: 0 }} onClick={() => onToggleTips(dayKey)}>
          {tipsExpanded ? '收起' : `展开更多（${hiddenTipCount}）`}
        </Button>
      )}
    </div>
  );
};
