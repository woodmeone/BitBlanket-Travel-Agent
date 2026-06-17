// 'use client' —— 客户端组件声明
'use client';

import React from 'react';
// Button —— 按钮，Card —— 卡片容器，Drawer —— 抽屉（从屏幕侧边滑出的面板），Space —— 间距容器，Tag —— 标签
import { Button, Card, Drawer, Space, Tag } from 'antd';
// EnvironmentOutlined —— 定位图标，用于抽屉标题
import { EnvironmentOutlined } from '@ant-design/icons';
// CityDetail —— 城市详情数据类型（比 CitySummary 更详细，包含景点列表等），CitySummary —— 城市摘要类型
import type { CityDetail, CitySummary } from '@/types';
// 从 shared.tsx 引入工具函数和类型
import { budgetLabel, buildComparePrompt, buildPlanPrompt, type DerivedCityProfile, seasonLabel, walkLabel } from '../shared';

// CityExplorerDetailDrawerProps —— 城市详情抽屉的属性类型
interface CityExplorerDetailDrawerProps {
  activeCityDetail: CityDetail | null;        // 当前查看的城市详情数据，null 表示未打开
  activeDetailProfile: DerivedCityProfile | null; // 当前城市的画像数据
  favoriteCities: CitySummary[];              // 候选池城市列表（用于"和候选城市对比"功能）
  isDetailOpen: boolean;                      // 抽屉是否打开
  onClose: () => void;                        // 关闭抽屉的回调
  onUsePrompt: (prompt: string) => void;      // 使用 AI 提示词的回调
}

// 【核心】CityExplorerDetailDrawer —— 城市详情抽屉组件
// 功能：从右侧滑出展示城市的详细信息，包括：
//   1. 城市气质 —— 描述和推荐语
//   2. 预算卡片 —— 人均预算、家庭预算、最佳季节
//   3. 怎么玩更顺 —— 旅行节奏建议、雨天策略、体力管理
//   4. 核心景点 —— 景点列表（名称、类型、时长、门票、区位、备注）
//   5. 下一步 —— "直接规划"和"和候选城市对比"按钮
// 应用场景：用户在城市卡片上点击"详情"按钮后，右侧滑出此抽屉，
//           可以查看更完整的城市信息并直接发起旅行规划
export const CityExplorerDetailDrawer: React.FC<CityExplorerDetailDrawerProps> = ({
  activeCityDetail,
  activeDetailProfile,
  favoriteCities,
  isDetailOpen,
  onClose,
  onUsePrompt,
}) => (
  // Drawer 是 Ant Design 的抽屉组件，从屏幕右侧滑出
  // open 控制是否显示，onClose 是关闭回调，size="large" 使用大尺寸
  <Drawer
    title={
      <span>
        <EnvironmentOutlined style={{ marginRight: 8 }} />
        {activeCityDetail?.name || '城市详情'} {/* ?. 是可选链操作符，如果 activeCityDetail 为 null 不会报错 */}
      </span>
    }
    open={isDetailOpen}
    onClose={onClose}
    size="large"
  >
    {/* 只有当城市详情和画像数据都存在时才渲染内容 */}
    {activeCityDetail && activeDetailProfile && (
      <div style={{ display: 'grid', gap: 14 }}>
        {/* 第一部分：城市气质 —— 描述 + 推荐语 + 标签 */}
        <Card size="small" style={{ borderRadius: 14 }}>
          <div style={{ display: 'grid', gap: 10 }}>
            {/* 城市气质标题 */}
            <div style={{ fontSize: 16, fontWeight: 700, color: '#0f172a' }}>{/* 城市气质 */}{'城市气质'}</div>
            {/* 城市描述 */}
            <div style={{ color: '#334155', lineHeight: 1.8 }}>{activeCityDetail.description}</div>
            {/* 编辑推荐语 */}
            <div style={{ fontSize: 13, color: '#475569' }}>{activeDetailProfile.recommendation}</div>
            {/* 标签组：预算、天数、气质、步行、真实策展 */}
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <Tag color="blue">{budgetLabel(activeDetailProfile.budgetLevel)}</Tag>
              <Tag color="green">{activeDetailProfile.tripDuration}</Tag>
              <Tag color="purple">{activeDetailProfile.styleLabel}</Tag>
              <Tag color="cyan">{walkLabel(activeDetailProfile.walkIntensity)}</Tag>
              <Tag color="gold">{'真实策展'}</Tag>
            </div>
          </div>
        </Card>

        {/* 第二部分：三列预算卡片 —— 人均预算、家庭预算、最佳季节 */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 10 }}>
          {/* 人均每日预算 */}
          <Card size="small" styles={{ body: { padding: 12 } }}>
            {/* 人均预算标签 */}
            <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>{/* 人均预算 */}{'人均预算'}</div>
            <div style={{ fontSize: 24, fontWeight: 700, color: '#111827' }}>{`¥${activeCityDetail.avg_budget_per_day}`}</div>
          </Card>
          {/* 家庭预算 —— 按人均预算 × 2.4 估算 */}
          <Card size="small" styles={{ body: { padding: 12 } }}>
            {/* 家庭预算标签 */}
            <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>{/* 家庭预算 */}{'家庭预算'}</div>
            <div style={{ fontSize: 24, fontWeight: 700, color: '#111827' }}>{`¥${Math.round(activeCityDetail.avg_budget_per_day * 2.4)}`}</div>
          </Card>
          {/* 最佳季节 */}
          <Card size="small" styles={{ body: { padding: 12 } }}>
            {/* 最佳季节标签 */}
            <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>{/* 最佳季节 */}{'最佳季节'}</div>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#111827' }}>{seasonLabel(activeCityDetail.best_seasons)}</div>
          </Card>
        </div>

        {/* 第三部分：怎么玩更顺 —— 旅行节奏建议 */}
        <Card size="small" title={'怎么玩更顺'}>
          <div style={{ display: 'grid', gap: 8, fontSize: 13, color: '#475569' }}>
            {/* 推荐节奏 */}
            <div>{`推荐节奏：${activeDetailProfile.tripDuration}，先安排核心片区，再做跨区延展。`}</div>
            {/* 雨天策略：根据城市是否雨天友好，给出不同建议 */}
            <div>
              {activeDetailProfile.rainFriendly
                ? '雨天策略：可保留大部分行程，优先馆和街区。'
                : '雨天策略：建议预留 1-2 个室内备选点。'}
            </div>
            {/* 体力管理 */}
            <div>
              {`体力管理：${walkLabel(activeDetailProfile.walkIntensity)}，不要把高密度打卡全堆在同一天。`}
            </div>
          </div>
        </Card>

        {/* 第四部分：核心景点列表 */}
        <Card size="small" title={'核心景点'}>
          <div style={{ display: 'grid', gap: 8 }}>
            {/* 遍历景点数组，为每个景点生成一个信息卡片 */}
            {activeCityDetail.attractions.map((attraction) => (
              <div
                key={attraction.name}
                style={{
                  border: '1px solid #e2e8f0',
                  borderRadius: 12,
                  padding: '10px 12px',
                  background: '#ffffff',
                }}
              >
                {/* 景点名称 + 类型标签 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
                  <div style={{ fontWeight: 700, color: '#1f2937' }}>{attraction.name}</div>
                  <Tag color="geekblue">{attraction.type}</Tag>
                </div>
                {/* 景点信息：建议停留时长 / 门票 / 区位 */}
                <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                  {`建议停留 ${attraction.duration} / 门票 ¥${attraction.ticket}${attraction.district ? ` / ${attraction.district}` : ''}`}
                </div>
                {/* 景点备注（如有） */}
                {attraction.note && <div style={{ fontSize: 12, color: '#475569', marginTop: 4 }}>{attraction.note}</div>}
              </div>
            ))}
          </div>
        </Card>

        {/* 第五部分：下一步操作 */}
        <Card size="small" title={'下一步'}>
          <Space wrap>
            {/* "直接规划这座城市"按钮 —— 生成该城市的3天旅行计划 */}
            <Button type="primary" onClick={() => onUsePrompt(buildPlanPrompt(activeCityDetail.name))}>
              {'直接规划这座城市'}
            </Button>
            {/* "和候选城市对比"按钮 —— 把当前城市和候选池前2个城市一起对比 */}
            {/* slice(0, 2) 只取候选池前2个城市，加上当前城市最多3个 */}
            <Button onClick={() => onUsePrompt(buildComparePrompt([activeCityDetail.name, ...favoriteCities.slice(0, 2).map((city) => city.name)]))}>
              {'和候选城市对比'}
            </Button>
          </Space>
        </Card>
      </div>
    )}
  </Drawer>
);
