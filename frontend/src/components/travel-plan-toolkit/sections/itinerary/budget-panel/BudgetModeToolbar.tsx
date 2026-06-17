// 预算模式工具栏组件
// 应用场景：在预算面板顶部，提供预算模式切换滑块和导出/分享按钮
//   用户拖动滑块在"省钱-均衡-舒适"之间切换，右侧有导出图片和分享按钮

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import { Button, Slider, Space, Tag, Tooltip } from 'antd';
import { FileImageOutlined, FundOutlined, ShareAltOutlined } from '@ant-design/icons';
import { modeToSliderValue, sliderToMode, type BudgetMode } from '../../../shared';

// BudgetModeToolbarProps 预算模式工具栏接收的参数
interface BudgetModeToolbarProps {
  budgetMode: BudgetMode;                              // 当前预算模式
  onBudgetModeChange: (mode: BudgetMode) => void;     // 切换预算模式的回调
  onExportImage: () => void;                            // 导出图片的回调
  onShare: () => void;                                  // 分享的回调
}

// 根据预算模式返回标签颜色
function budgetModeColor(mode: BudgetMode): 'blue' | 'gold' | 'green' {
  if (mode === 'saving') return 'blue';     // 省钱 → 蓝色
  if (mode === 'balanced') return 'gold';   // 均衡 → 金色
  return 'green';                           // 舒适 → 绿色
}

// 根据预算模式返回中文标签
function budgetModeLabel(mode: BudgetMode): string {
  if (mode === 'saving') return '省钱';
  if (mode === 'balanced') return '均衡';
  return '舒适';
}

export const BudgetModeToolbar: React.FC<BudgetModeToolbarProps> = ({
  budgetMode,
  onBudgetModeChange,
  onExportImage,
  onShare,
}) => (
  <div style={{ display: 'grid', gap: 10 }}>
    {/* 顶部行：左侧显示预算档位标签，右侧显示导出和分享按钮 */}
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
      <Space>
        <FundOutlined style={{ color: '#0f766e' }} />
        <span style={{ fontSize: 13, color: '#334155' }}>预算档位</span>
        <Tag color={budgetModeColor(budgetMode)}>{budgetModeLabel(budgetMode)}</Tag>
      </Space>
      <Space>
        {/* Tooltip 是鼠标悬停时显示的提示文字 */}
        <Tooltip title="导出图片长图">
          <Button aria-label="导出旅行方案图片" size="small" icon={<FileImageOutlined />} onClick={onExportImage} />
        </Tooltip>
        <Tooltip title="生成可分享短链">
          <Button aria-label="分享旅行方案" size="small" icon={<ShareAltOutlined />} onClick={onShare} />
        </Tooltip>
      </Space>
    </div>

    {/* 预算模式滑块，0-100，标记点在10(省钱)、50(均衡)、90(舒适) */}
    <Slider
      min={0}
      max={100}
      value={modeToSliderValue(budgetMode)}
      marks={{ 10: '省钱', 50: '均衡', 90: '舒适' }}
      onChange={(value) => onBudgetModeChange(sliderToMode(Array.isArray(value) ? value[0] : value))}
    />
  </div>
);
