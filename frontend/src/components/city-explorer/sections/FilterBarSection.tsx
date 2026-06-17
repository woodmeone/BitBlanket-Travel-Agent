// 'use client' —— 客户端组件声明
'use client';

import React from 'react';
// Button —— 按钮，Select —— 下拉选择框，Space —— 间距容器（自动给子元素加间距）
import { Button, Select, Space } from 'antd';
// QUICK_FILTERS —— 快速筛选按钮配置列表，QuickFilterKey —— 快速筛选标识类型
import { QUICK_FILTERS, type QuickFilterKey } from '../shared';

// CityExplorerFilterBarProps —— 筛选栏的属性类型
// 这个组件需要接收很多状态和回调函数，因为筛选逻辑由父组件管理（状态提升模式）
interface CityExplorerFilterBarProps {
  isFilterLoading: boolean;                          // 筛选项是否正在加载
  onUsePrompt: (prompt: string) => void;             // 使用 AI 提示词的回调
  regions: string[];                                 // 可选地区列表，如 ['华东', '华南', '西南']
  selectedQuickFilters: QuickFilterKey[];            // 当前激活的快速筛选项
  selectedRegion: string | undefined;                // 当前选中的地区
  selectedTags: string[];                            // 当前选中的标签列表
  tags: string[];                                    // 可选标签列表，如 ['美食', '文艺', '夜市']
  toggleQuickFilter: (filterKey: QuickFilterKey) => void; // 切换快速筛选项的回调
  setSelectedRegion: (value: string | undefined) => void; // 设置选中地区的回调
  setSelectedTags: (value: string[]) => void;            // 设置选中标签的回调
}

// 【核心】CityExplorerFilterBar —— 城市筛选栏组件
// 功能：提供三种筛选方式
//   1. 地区下拉框 —— 选择地区（如"华东"），单选
//   2. 标签下拉框 —— 选择标签（如"美食"、"文艺"），多选
//   3. 快速筛选按钮 —— 按场景快速过滤（如"周末可去"、"预算友好"）
// 还有一个"让助手帮我选"按钮，把当前筛选条件发给 AI 助手
// 应用场景：用户想找"华东地区、美食优先、预算友好"的城市，
//           可以先选地区"华东"，再点"美食优先"和"预算友好"按钮
export const CityExplorerFilterBar: React.FC<CityExplorerFilterBarProps> = ({
  isFilterLoading,
  onUsePrompt,
  regions,
  selectedQuickFilters,
  selectedRegion,
  selectedTags,
  tags,
  toggleQuickFilter,
  setSelectedRegion,
  setSelectedTags,
}) => (
  // 筛选栏容器：圆角卡片，白色渐变背景
  <div
    style={{
      border: '1px solid #dbe4ee',
      borderRadius: 16,
      background: 'linear-gradient(180deg, rgba(255,255,255,0.9) 0%, #f8fbff 100%)',
      padding: 12,
      display: 'grid',
      gap: 10,
    }}
  >
    {/* 第一行：地区选择 + 标签选择 + AI 助手按钮 */}
    {/* Space 组件自动给子元素之间加间距，wrap 允许换行 */}
    <Space wrap size={[10, 10]}>
      {/* 地区下拉框 —— 单选，可清空 */}
      <Select
        allowClear // 允许清空已选值
        loading={isFilterLoading} // 加载中时显示加载动画
        placeholder="按地区筛选城市"
        style={{ width: 190 }}
        value={selectedRegion}
        onChange={(value) => setSelectedRegion(value)} // 选中后更新父组件状态
        // 把字符串数组转成 Select 需要的 { label, value } 格式
        options={regions.map((item) => ({ label: item, value: item }))}
      />
      {/* 标签下拉框 —— 多选 */}
      <Select
        mode="multiple" // mode="multiple" 允许选择多个值
        loading={isFilterLoading}
        placeholder="按标签缩小范围"
        style={{ width: 340, maxWidth: '100%' }}
        value={selectedTags}
        onChange={(value) => setSelectedTags(value)}
        options={tags.map((item) => ({ label: item, value: item }))}
      />
      {/* "让助手帮我选"按钮 —— 点击后发送 AI 提示词 */}
      <Button
        type="primary"
        style={{
          borderRadius: 999,
          border: 'none',
          background: 'linear-gradient(135deg, #0369a1 0%, #0f766e 100%)',
          boxShadow: '0 8px 20px rgba(14, 116, 144, 0.28)',
        }}
        onClick={() =>
          onUsePrompt(
            '请基于当前真实策展城市库，结合已选地区、标签和场景偏好，帮我筛出更适合的目的地，并说明推荐理由和不推荐的边界。'
          )
        }
      >
        让助手帮我选
      </Button>
    </Space>

    {/* 第二行：快速筛选按钮组 */}
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
      {/* 遍历 QUICK_FILTERS 数组，为每个筛选项生成一个按钮 */}
      {QUICK_FILTERS.map((filter) => {
        // 检查当前筛选项是否已激活（用户已点击）
        const active = selectedQuickFilters.includes(filter.key);
        return (
          <Button
            key={filter.key}
            size="small"
            type={active ? 'primary' : 'default'} // 激活时用 primary 样式（蓝色），否则用 default（白色）
            onClick={() => toggleQuickFilter(filter.key)} // 点击切换激活状态
            style={
              active
                ? {
                    // 激活状态：渐变背景 + 阴影
                    borderRadius: 999,
                    fontWeight: 700,
                    background: 'linear-gradient(135deg, #0284c7 0%, #0f766e 100%)',
                    borderColor: 'transparent',
                    boxShadow: '0 8px 16px rgba(2, 132, 199, 0.24)',
                  }
                : {
                    // 未激活状态：白色背景 + 灰色边框
                    borderRadius: 999,
                    borderColor: '#cbd5e1',
                    color: '#334155',
                    background: '#ffffff',
                  }
            }
          >
            {filter.label}
          </Button>
        );
      })}
    </div>
  </div>
);
