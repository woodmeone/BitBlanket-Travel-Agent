// 'use client'：客户端组件声明，本组件需要根据实时数据动态渲染
'use client';

import React from 'react';
// Tag：标签组件，用于显示各种状态标记
import { Tag } from 'antd';
// 图标组件：BulbOutlined（灯泡）、ClockCircleOutlined（时钟）、ToolOutlined（工具）
import { BulbOutlined, ClockCircleOutlined, ToolOutlined } from '@ant-design/icons';
// StreamMetadata：流式响应的元数据类型（包含工具使用、验证状态等信息）
import type { StreamMetadata } from '@/services/api';
// 各种事件和数据的类型定义：
// PlanPreview：计划预览数据（Plan 模式下生成的执行计划）
// StreamStageEvent：流式阶段事件（如"正在搜索酒店"、"正在生成行程"等阶段）
// SubagentEvent：子 Agent 事件（子 Agent 的启动、完成等状态变化）
// TripPlanArtifact：行程计划产物（最终生成的完整行程方案）
import type { PlanPreview, StreamStageEvent, SubagentEvent, TripPlanArtifact } from '@/types';
// buildSubagentEventKey：为子 Agent 事件生成唯一 key 的工具函数
import { buildSubagentEventKey } from '@/utils/subagentEvents';
// normalizeStepLabel：标准化步骤标签的显示文字
// subagentLabel：获取子 Agent 的显示名称
// RuntimeLog：运行时日志条目的类型定义
import { normalizeStepLabel, subagentLabel, type RuntimeLog } from './shared';

// ExecutionInsightsProps：执行洞察面板接收的属性
// 这个面板展示 AI 对话过程中的各种运行状态信息
interface ExecutionInsightsProps {
  isStreaming: boolean;              // 是否正在流式输出（AI 正在回复）
  isThinking: boolean;               // AI 是否正在思考（还没开始输出文字）
  currentTool: string | null;        // 当前正在调用的工具名称，如 "search_hotel"
  stageState: StreamStageEvent | null;     // 当前阶段状态
  stageHistory: StreamStageEvent[];        // 历史阶段记录列表
  runtimeLogs: RuntimeLog[];               // 运行时日志列表
  planPreview: PlanPreview | null;         // 计划预览数据
  metadata: StreamMetadata | null;         // 流式响应元数据
  artifact: TripPlanArtifact | null;       // 最终生成的行程产物
  activeSubagent: string | null;           // 当前活跃的子 Agent 标识
  subagentEvents: SubagentEvent[];         // 子 Agent 事件列表
}

// 【核心】ExecutionInsights：执行洞察面板组件
// 作用：在 AI 回复过程中，实时展示执行状态、阶段进度、计划预览、子 Agent 轨迹等信息
// 应用场景：用户发送"帮我规划3天成都旅行"后，面板会显示：
//   - 当前阶段："正在搜索景点" → 进度 60%
//   - 使用的工具："search_attraction"
//   - 计划预览：第1步查天气、第2步搜酒店...
//   - 子 Agent 轨迹：hotel_agent 启动 → 完成
const ExecutionInsights: React.FC<ExecutionInsightsProps> = ({
  isStreaming,
  isThinking,
  currentTool,
  stageState,
  stageHistory,
  runtimeLogs,
  planPreview,
  metadata,
  artifact,
  activeSubagent,
  subagentEvents,
}) => {
  // shouldShow：判断是否需要显示这个面板
  // 只有当存在任何运行状态信息时才显示，避免空白面板
  // Boolean()：将值转为布尔值，非空/非零/非null 的值转为 true
  const shouldShow =
    isStreaming ||
    isThinking ||
    Boolean(currentTool) ||
    Boolean(planPreview) ||
    stageHistory.length > 0 ||
    runtimeLogs.length > 0 ||
    Boolean(metadata) ||
    Boolean(artifact) ||
    subagentEvents.length > 0;

  // 没有需要展示的信息时，不渲染任何内容
  if (!shouldShow) return null;

  // 进度值处理：将 0~1 的小数转为百分比文字
  const progressValue = stageState?.progress;
  const progressText =
    typeof progressValue === 'number' && Number.isFinite(progressValue)
      ? `${Math.round(Math.max(0, Math.min(100, progressValue * 100)))}%`  // 限制在 0~100% 范围内
      : '进行中';  // 如果没有具体进度数值，显示"进行中"

  return (
    // 面板容器：带渐变背景和阴影的卡片样式
    <div
      style={{
        margin: '0 16px 16px',
        padding: '12px',
        background: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)',  // 白色到浅灰的渐变
        borderRadius: '14px',
        border: '1px solid rgba(37, 99, 235, 0.14)',  // 半透明蓝色边框
        boxShadow: '0 4px 12px rgba(15, 23, 42, 0.06)',  // 轻微阴影
      }}
    >
      {/* 状态标签行：显示当前运行的各种状态 */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '10px' }}>
        {/* 流式状态：运行中=蓝色，已结束=灰色 */}
        <Tag color={isStreaming ? 'blue' : 'default'}>{isStreaming ? '运行中' : '已结束'}</Tag>
        {/* 思考状态：AI 正在推理但还没输出文字时显示 */}
        {isThinking && <Tag color="purple">思考中</Tag>}
        {/* 当前工具：显示 AI 正在调用的工具名称 */}
        {currentTool && <Tag color="gold">工具: {currentTool}</Tag>}
        {/* 当前阶段：如"搜索景点"、"生成行程" */}
        {stageState?.label && <Tag color="cyan">阶段: {stageState.label}</Tag>}
        {/* 活跃子 Agent：如"hotel_agent"（酒店搜索代理） */}
        {activeSubagent && <Tag color="geekblue">子 Agent: {subagentLabel(activeSubagent)}</Tag>}
        {/* 行程产物标识：显示生成的行程计划 ID */}
        {artifact?.itinerary.planId && <Tag color="purple">Artifact #{artifact.itinerary.planId}</Tag>}
      </div>

      {/* 阶段进度条：显示当前阶段的名称和进度百分比 */}
      {stageState && (
        <div
          style={{
            marginBottom: '10px',
            padding: '8px 10px',
            borderRadius: '10px',
            background: '#eff6ff',  // 浅蓝色背景
            fontSize: '12px',
            color: '#1d4ed8',
            display: 'flex',
            justifyContent: 'space-between',  // 两端对齐：左边阶段名，右边进度
            alignItems: 'center',
          }}
        >
          <span>{stageState.label || stageState.stage || '阶段更新'}</span>
          <span>{progressText}</span>
        </div>
      )}

      {/* Plan 预览区域：在 Plan 模式下显示 AI 生成的执行计划 */}
      {planPreview && (
        <div
          style={{
            marginBottom: '10px',
            padding: '10px',
            borderRadius: '10px',
            background: '#f5f3ff',  // 浅紫色背景
            border: '1px solid rgba(124, 58, 237, 0.2)',
          }}
        >
          {/* 计划标题 */}
          <div style={{ fontSize: '12px', color: '#6d28d9', marginBottom: '6px', fontWeight: 600 }}>
            Plan 预览 {planPreview.planId ? `#${planPreview.planId}` : ''}
          </div>
          {/* 意图和校验状态 */}
          <div style={{ fontSize: '12px', color: '#5b21b6', marginBottom: '6px' }}>
            意图: {planPreview.intent || '未知'} | 校验: {planPreview.validationStatus || '未知'}
          </div>
          {/* 计划说明 */}
          {planPreview.explanation && (
            <div style={{ fontSize: '12px', color: '#4c1d95', marginBottom: '6px' }}>{planPreview.explanation}</div>
          )}
          {/* 执行步骤列表，最多显示前6步 */}
          {planPreview.steps.length > 0 && (
            <ol style={{ margin: '0 0 0 18px', padding: 0, fontSize: '12px', color: '#4c1d95', lineHeight: 1.7 }}>
              {planPreview.steps.slice(0, 6).map((step, index) => (
                <li key={`${index}-${normalizeStepLabel(step, index)}`}>{normalizeStepLabel(step, index)}</li>
              ))}
            </ol>
          )}
        </div>
      )}

      {/* Artifact / 子 Agent 轨迹区域：展示最终产物信息和子 Agent 的执行记录 */}
      {(artifact || subagentEvents.length > 0) && (
        <div
          style={{
            marginBottom: '10px',
            padding: '10px',
            borderRadius: '10px',
            background: '#ecfeff',  // 浅青色背景
            border: '1px solid rgba(8, 145, 178, 0.18)',
          }}
        >
          <div style={{ fontSize: '12px', color: '#0f766e', marginBottom: '8px', fontWeight: 600 }}>
            Artifact / 子 Agent 轨迹
          </div>

          {/* 行程产物信息标签 */}
          {artifact && (
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '8px' }}>
              {/* 意图标签：如 "plan_itinerary" */}
              <Tag color="blue">Intent: {artifact.intent.name || 'general'}</Tag>
              {/* 校验结果：通过=绿色，未通过=红色，待定=灰色 */}
              <Tag color={artifact.verification.passed === false ? 'red' : artifact.verification.passed ? 'green' : 'default'}>
                校验: {artifact.verification.passed === false ? '未通过' : artifact.verification.passed ? '通过' : '待定'}
              </Tag>
              {/* 使用的工具数量 */}
              <Tag color="gold">Tools: {artifact.toolsUsed.length}</Tag>
              {/* 证据数量：AI 搜索到的支撑信息条数 */}
              {artifact.research.evidence.length > 0 && <Tag color="cyan">Evidence: {artifact.research.evidence.length}</Tag>}
            </div>
          )}

          {/* 子 Agent 事件时间线：按时间倒序显示（最新的在最上面） */}
          {subagentEvents.length > 0 && (
            <div style={{ display: 'grid', gap: '6px' }}>
              {subagentEvents
                .slice()          // 浅拷贝，避免修改原数组
                .reverse()        // 倒序排列，最新事件在上方
                .map((event, index) => (
                  <div key={buildSubagentEventKey(event, index)} style={{ fontSize: '12px', color: '#155e75' }}>
                    {/* 时间戳 + 子 Agent 名称 + 状态/触发器 + 技能列表 + 摘要 */}
                    [{event.timestamp || '--:--:--'}] {subagentLabel(event.subagent)}
                    {event.status ? ` -> ${event.status}` : ` -> ${event.trigger || 'started'}`}
                    {event.skills?.length ? ` | ${event.skills.join(', ')}` : ''}
                    {event.summary ? ` | ${event.summary}` : ''}
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

      {/* 底部双栏：执行时间线 + 运行诊断 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
        {/* 左栏：执行时间线，显示运行过程中的关键事件 */}
        <div style={{ background: '#f8fafc', borderRadius: '10px', padding: '10px' }}>
          <div style={{ fontSize: '12px', color: '#334155', marginBottom: '6px', fontWeight: 600 }}>
            <ClockCircleOutlined style={{ marginRight: 6 }} />
            执行时间线
          </div>
          <div style={{ maxHeight: '140px', overflow: 'auto', display: 'grid', gap: '6px' }}>
            {runtimeLogs.length === 0 && <div style={{ fontSize: '12px', color: '#94a3b8' }}>等待事件...</div>}
            {/* 日志倒序显示（最新的在上方） */}
            {runtimeLogs
              .slice()
              .reverse()
              .map((item) => (
                <div key={item.id} style={{ fontSize: '12px', color: '#334155' }}>
                  [{item.time}] {item.label}
                  {item.detail ? ` / ${item.detail}` : ''}
                </div>
              ))}
          </div>
        </div>

        {/* 右栏：运行诊断，显示统计数据 */}
        <div style={{ background: '#f8fafc', borderRadius: '10px', padding: '10px' }}>
          <div style={{ fontSize: '12px', color: '#334155', marginBottom: '6px', fontWeight: 600 }}>
            <ToolOutlined style={{ marginRight: 6 }} />
            运行诊断
          </div>
          <div style={{ fontSize: '12px', color: '#475569', lineHeight: 1.8 }}>
            <div>阶段更新: {stageHistory.length} 次</div>
            <div>工具调用: {metadata?.toolsUsed?.length || 0} 个</div>
            {/* 验证状态：检查 AI 的输出是否通过了预设的校验规则 */}
            <div>
              验证状态:{' '}
              {metadata?.verificationPassed === null || metadata?.verificationPassed === undefined
                ? '未知'
                : metadata.verificationPassed
                  ? '通过'
                  : '未通过'}
            </div>
            {/* 过期结果：由于数据更新导致之前的结果已失效的数量 */}
            <div>过期结果: {metadata?.staleResultCount || 0}</div>
            {/* 回退次数：工具调用失败后回退重试的次数 */}
            <div>回退次数: {metadata?.fallbackSteps || 0}</div>
            {metadata?.planId && <div>计划 ID: {metadata.planId}</div>}
            <div>子 Agent 事件: {subagentEvents.length}</div>
            {/* Research 摘要：AI 搜索研究的结果概要 */}
            {artifact?.research.summary && <div>Research: {artifact.research.summary}</div>}
          </div>
        </div>
      </div>

      {/* 底部说明文字：标注数据来源 */}
      <div style={{ marginTop: '8px', fontSize: '11px', color: '#64748b' }}>
        <BulbOutlined style={{ marginRight: 6 }} />
        以上内容来自后端 SSE 事件: stage、plan_preview、subagent_start / subagent_end、artifact_patch、tool_start / tool_end、metadata
      </div>
    </div>
  );
};

export default ExecutionInsights;
