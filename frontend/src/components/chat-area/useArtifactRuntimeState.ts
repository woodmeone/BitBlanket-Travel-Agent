// 'use client' 是 Next.js 的指令，表示此文件仅在浏览器端运行
'use client';

// React 的类型和 Hook 导入
// Dispatch<SetStateAction<T>> 是 useState 返回的 setter 函数的类型
// MutableRefObject<T> 是 useRef 返回的可变引用对象的类型
import type { Dispatch, MutableRefObject, SetStateAction } from 'react';
import { useRef, useState } from 'react';
// 项目类型定义
import type { ArtifactPatch, PlanPreview, SubagentEvent, TripPlanArtifact } from '@/types';
// 合并行程数据的工具函数
import { mergeTripPlanArtifact } from '@/utils/agentArtifacts';
import { MAX_SUBAGENT_EVENTS, nowLabel } from './shared';

// 【核心】Artifact 运行时状态接口
// Artifact 是"行程结构化数据"的统称，包含行程安排、预算、校验结果等
// "运行时状态"指的是在 AI 生成行程的过程中，实时维护和更新的中间状态
// 应用场景：AI 正在生成行程时，每收到一段新数据就更新 artifactState，界面实时展示最新进度
interface ArtifactRuntimeState {
  activeSubagent: string | null;         // 当前正在运行的子智能体名称，null 表示没有子智能体在运行
  artifactRef: MutableRefObject<TripPlanArtifact | null>;  // artifact 的引用（ref），用于在回调中获取最新值，避免闭包陷阱
  artifactState: TripPlanArtifact | null;  // artifact 的响应式状态，变化时触发界面重新渲染
  planPreview: PlanPreview | null;       // 方案预览数据，用于在对比模式下展示多个方案的摘要
  subagentEvents: SubagentEvent[];       // 子智能体事件列表，记录各子智能体的启动、完成等状态变化
  subagentEventsRef: MutableRefObject<SubagentEvent[]>;  // 子智能体事件的引用，同样用于避免闭包陷阱
  applyArtifactPatch: (patch: ArtifactPatch | TripPlanArtifact | null | undefined) => void;  // 【核心】应用增量更新到 artifact
  recordSubagentEvent: (event: SubagentEvent) => void;  // 记录一个子智能体事件
  resetArtifactRuntimeState: () => void;  // 重置所有运行时状态（切换会话或开始新对话时调用）
  setPlanPreview: Dispatch<SetStateAction<PlanPreview | null>>;  // 设置方案预览的 setter 函数
}

// 【核心】Artifact 运行时状态管理 Hook
// Hook 是 React 的特殊函数，以 use 开头，用于在组件中添加状态和副作用
// 这个 Hook 封装了 AI 生成行程过程中的所有实时状态管理逻辑
//
// 为什么同时用 useState 和 useRef？
//   - useState：值变化会触发界面重新渲染，用于需要展示给用户的数据
//   - useRef：值变化不会触发重新渲染，用于在回调函数中获取最新值
//   - 在异步回调（如流式数据处理的回调）中，如果用 useState 的值，可能拿到的是旧的（闭包陷阱）
//     所以需要用 ref 来保证始终获取最新值
//
// 应用场景举例：
//   1. AI 开始生成行程 → 调用 recordSubagentEvent 记录"规划"子智能体启动
//   2. AI 逐步返回行程数据 → 调用 applyArtifactPatch 将增量数据合并到 artifact
//   3. 界面实时展示最新行程 → 因为 artifactState 变化触发重新渲染
//   4. 用户切换到另一个会话 → 调用 resetArtifactRuntimeState 清空状态
export function useArtifactRuntimeState(): ArtifactRuntimeState {
  // artifact 的响应式状态，变化时界面重新渲染
  const [artifactState, setArtifactState] = useState<TripPlanArtifact | null>(null);
  // 子智能体事件的响应式状态
  const [subagentEvents, setSubagentEvents] = useState<SubagentEvent[]>([]);
  // 当前活跃的子智能体名称
  const [activeSubagent, setActiveSubagent] = useState<string | null>(null);
  // 方案预览数据
  const [planPreview, setPlanPreview] = useState<PlanPreview | null>(null);

  // artifact 的引用，用于在回调中获取最新值（避免闭包陷阱）
  const artifactRef = useRef<TripPlanArtifact | null>(null);
  // 子智能体事件的引用，同样用于避免闭包陷阱
  const subagentEventsRef = useRef<SubagentEvent[]>([]);
  // 子智能体事件的自增 key，用于生成唯一的 clientKey
  const subagentEventKeyRef = useRef(0);

  // 【核心】应用增量更新到 artifact
  // patch 可以是增量补丁（ArtifactPatch）、完整的 artifact、或 null
  // mergeTripPlanArtifact 会智能合并：把新数据合并到现有 artifact 上，而非简单替换
  // 应用场景：AI 流式返回行程数据时，每次返回一小段，需要逐步合并到完整的行程中
  //   例如：先收到第1天行程 → 合并；再收到第2天行程 → 合并；最终形成完整行程
  const applyArtifactPatch = (patch: ArtifactPatch | TripPlanArtifact | null | undefined) => {
    const merged = mergeTripPlanArtifact(artifactRef.current, patch);
    // 同时更新 ref（供回调使用）和 state（供界面渲染使用）
    artifactRef.current = merged;
    setArtifactState(merged);
  };

  // 记录一个子智能体事件
  // 子智能体是 AI 内部的分工角色，每个子智能体启动/完成时都会产生一个事件
  // 应用场景：AI 开始规划行程时产生"规划启动"事件，规划完成时产生"规划完成"事件
  const recordSubagentEvent = (event: SubagentEvent) => {
    // 自增 key，确保每个事件有唯一标识
    subagentEventKeyRef.current += 1;
    // 给事件打上时间戳和唯一 key
    const stamped: SubagentEvent = {
      ...event,
      timestamp: event.timestamp || nowLabel(),  // 如果事件没有时间戳，使用当前时间
      // clientKey 用于 React 列表渲染的 key 属性，确保每个事件有唯一标识
      // Date.now() 返回当前时间的毫秒数，配合自增 key 确保唯一性
      clientKey: event.clientKey || `subagent-event-${Date.now()}-${subagentEventKeyRef.current}`,
    };
    // 保留最新的 MAX_SUBAGENT_EVENTS 条事件，丢弃更早的
    // slice(-MAX_SUBAGENT_EVENTS + 1) 取最后 N-1 条，加上新事件共 N 条
    const nextEvents = [...subagentEventsRef.current.slice(-MAX_SUBAGENT_EVENTS + 1), stamped];
    // 同时更新 ref 和 state
    subagentEventsRef.current = nextEvents;
    setSubagentEvents(nextEvents);
    // 如果事件有 status 字段（表示子智能体完成），则清除当前活跃子智能体
    // 否则，将当前活跃子智能体设置为事件中的子智能体名称
    if (event.status) {
      // 只有当事件来源的子智能体与当前活跃子智能体一致时，才清除
      setActiveSubagent((current) => (current === event.subagent ? null : current));
      return;
    }
    setActiveSubagent(event.subagent);
  };

  // 重置所有运行时状态
  // 应用场景：切换会话、开始新对话时，需要清空之前的行程数据和子智能体事件
  const resetArtifactRuntimeState = () => {
    artifactRef.current = null;
    subagentEventsRef.current = [];
    subagentEventKeyRef.current = 0;
    setArtifactState(null);
    setSubagentEvents([]);
    setActiveSubagent(null);
    setPlanPreview(null);
  };

  return {
    activeSubagent,
    artifactRef,
    artifactState,
    planPreview,
    subagentEvents,
    subagentEventsRef,
    applyArtifactPatch,
    recordSubagentEvent,
    resetArtifactRuntimeState,
    setPlanPreview,
  };
}
