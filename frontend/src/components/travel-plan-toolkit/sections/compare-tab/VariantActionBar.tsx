// 方案选择操作栏组件
// 应用场景：在多方案对比表格下方，每个方案对应一个"选中"按钮
//   用户点击后，该方案被选中并进入细化编辑流程

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import { Button } from 'antd';
import type { PlanVariant } from '@/utils/travelPlan';

// VariantActionBarProps 操作栏接收的参数
interface VariantActionBarProps {
  variants: PlanVariant[];                              // 方案变体列表
  onChooseVariant: (variant: PlanVariant) => void;     // 选中某个方案的回调
}

export const VariantActionBar: React.FC<VariantActionBarProps> = ({ variants, onChooseVariant }) => (
  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
    {variants.map((variant) => (
      <Button key={variant.id} onClick={() => onChooseVariant(variant)}>
        选中"{variant.title}"继续细化
      </Button>
    ))}
  </div>
);
