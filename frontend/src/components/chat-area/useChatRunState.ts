// 【核心】useChatRunState 是聊天对话"运行状态"管理 Hook
//
// 核心职责：管理一次 AI 对话从"开始"到"结束"的完整生命周期状态，
// 包括：等待响应、思考中、工具调用、阶段推进、成功/失败/中断等。
//
// 场景举例：用户发送"帮我规划三亚5日游"后，
// 1. beginRun → 界面显示"等待中"+"思考中"
// 2. recordStage("分析需求") → 界面显示当前阶段
// 3. recordToolStart("search_hotel") → 界面显示"正在搜索酒店"
// 4. recordToolEnd("search_hotel") → 界面显示"酒店搜索完成"
// 5. completeRun → 界面恢复正常，显示最终回答
// 如果中途出错 → failRun 显示错误信息；用户点击停止 → stopRun 中断生成
'use client';

import { useState } from 'react';
import type { StreamStageEvent } from '@/types';
import { MAX_EVENT_LOGS, MAX_STAGE_LOGS, nowLabel, type RuntimeLog } from './shared';

// 返回值接口：useChatRunState 暴露给外部的状态和操作方法
interface UseChatRunStateResult {
  // 当前正在调用的工具名称，如 "search_hotel"；没有工具在调用时为 null
  currentTool: string | null;
  // 错误信息，执行失败时记录；没有错误时为 null
  error: string | null;
  // AI 是否正在"思考"中（即正在处理用户请求，尚未开始输出回答）
  isThinking: boolean;
  // 运行时日志列表，记录整个对话过程中的关键事件，用于界面展示执行过程
  runtimeLogs: RuntimeLog[];
  // 阶段历史记录，记录 AI 执行过程中经过的所有阶段（如"分析需求"、"搜索酒店"等）
  stageHistory: StreamStageEvent[];
  // 当前所处的阶段
  stageState: StreamStageEvent | null;
  // 是否正在等待 AI 响应（从发送消息到收到完整回答期间为 true）
  waitingForResponse: boolean;
  // 开始一次对话运行
  beginRun: (modeLabel: string) => void;
  // 对话运行成功完成
  completeRun: (label?: string, detail?: string) => void;
  // 对话运行失败
  failRun: (errorMessage: string) => void;
  // 添加一条运行时日志
  pushRuntimeLog: (label: string, detail?: string) => void;
  // 记录一个执行阶段
  recordStage: (stage: StreamStageEvent) => void;
  // 记录工具调用结束
  recordToolEnd: (toolName: string) => void;
  // 记录工具调用开始
  recordToolStart: (toolName: string) => void;
  // 重置所有运行状态（通常在开始全新对话时调用）
  resetRunState: () => void;
  // 设置思考状态（外部可手动控制）
  setThinking: (value: boolean) => void;
  // 用户主动中断对话运行
  stopRun: (detail?: string) => void;
}

export function useChatRunState(): UseChatRunStateResult {
  // 是否正在等待 AI 响应。用户发送消息后设为 true，收到完整回答后设为 false
  // 场景：用户发送"帮我规划三亚5日游" → true；AI 回答完毕 → false
  const [waitingForResponse, setWaitingForResponse] = useState(false);
  // AI 是否正在思考中。等待响应期间为 true，开始输出回答后设为 false
  const [isThinking, setIsThinking] = useState(false);
  // 错误信息。正常情况下为 null，执行出错时记录错误原因
  const [error, setError] = useState<string | null>(null);
  // 当前正在调用的工具名称。AI 调用工具（如搜索酒店）时设为工具名，调用结束后设为 null
  const [currentTool, setCurrentTool] = useState<string | null>(null);
  // 当前执行阶段。如"分析需求"、"生成行程"等
  const [stageState, setStageState] = useState<StreamStageEvent | null>(null);
  // 阶段历史记录数组，记录从开始到现在的所有阶段变化
  const [stageHistory, setStageHistory] = useState<StreamStageEvent[]>([]);
  // 运行时日志数组，记录所有关键事件（开始、阶段变化、工具调用、完成等）
  const [runtimeLogs, setRuntimeLogs] = useState<RuntimeLog[]>([]);

  // 【核心】添加一条运行时日志
  // 每条日志包含：唯一 ID、标签（如"开始执行"）、详情、时间
  // prev.slice(-MAX_EVENT_LOGS + 1) 保留最新的 N 条日志，防止日志过多占用内存
  // 场景：AI 开始搜索酒店 → pushRuntimeLog("工具启动", "search_hotel")
  const pushRuntimeLog = (label: string, detail?: string) => {
    const item: RuntimeLog = {
      // 生成唯一 ID：时间戳 + 随机字符串，确保每条日志 ID 不重复
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      label,
      detail,
      time: nowLabel(),
    };
    // [...prev.slice(-MAX_EVENT_LOGS + 1), item]：
    // 先取已有日志的最后 N-1 条，再追加新日志，保持总数不超过 N 条
    setRuntimeLogs((prev) => [...prev.slice(-MAX_EVENT_LOGS + 1), item]);
  };

  // 重置所有运行状态
  // 场景：用户开始全新的对话，需要清空上一轮的所有状态数据
  const resetRunState = () => {
    setWaitingForResponse(false);
    setIsThinking(false);
    setError(null);
    setCurrentTool(null);
    setStageState(null);
    setStageHistory([]);
    setRuntimeLogs([]);
  };

  // 【核心】开始一次对话运行
  // modeLabel: 执行模式标签，如"对话模式"、"规划模式"等
  // 场景：用户发送消息后调用，将界面切换到"等待响应"状态
  const beginRun = (modeLabel: string) => {
    setWaitingForResponse(true);
    setIsThinking(true);
    setError(null);
    setCurrentTool(null);
    setStageState(null);
    setStageHistory([]);
    setRuntimeLogs([]);
    pushRuntimeLog('开始执行', `模式: ${modeLabel}`);
  };

  // 【核心】记录一个执行阶段
  // 场景：AI 从"分析需求"阶段推进到"搜索酒店"阶段时调用
  // stageHistory 保留最新的 MAX_STAGE_LOGS 条记录，防止历史过长
  const recordStage = (stage: StreamStageEvent) => {
    setStageState(stage);
    setStageHistory((prev) => [...prev, stage].slice(-MAX_STAGE_LOGS));
    pushRuntimeLog('阶段', stage.label || stage.stage || '阶段更新');
  };

  // 【核心】记录工具调用开始
  // 场景：AI 开始调用"搜索酒店"工具 → recordToolStart("search_hotel")
  // 界面上会显示"正在使用工具：search_hotel"
  const recordToolStart = (toolName: string) => {
    setCurrentTool(toolName);
    pushRuntimeLog('工具启动', toolName);
  };

  // 【核心】记录工具调用结束
  // 场景："搜索酒店"工具执行完毕 → recordToolEnd("search_hotel")
  // currentTool 恢复为 null，界面不再显示工具调用状态
  const recordToolEnd = (toolName: string) => {
    setCurrentTool(null);
    pushRuntimeLog('工具完成', toolName);
  };

  // 【核心】对话运行成功完成
  // 场景：AI 已生成完整回答，如"三亚5日游行程如下..."
  // 将所有"进行中"的状态重置，记录完成日志
  const completeRun = (
    label = '结束',
    detail = '已生成最终回答'
  ) => {
    setWaitingForResponse(false);
    setIsThinking(false);
    setError(null);
    setCurrentTool(null);
    setStageState(null);
    pushRuntimeLog(label, detail);
  };

  // 【核心】对话运行失败
  // 场景：AI 调用搜索工具时网络超时，无法获取酒店信息
  // 记录错误原因，界面显示错误提示
  const failRun = (errorMessage: string) => {
    setWaitingForResponse(false);
    setIsThinking(false);
    setError(errorMessage);
    setCurrentTool(null);
    setStageState(null);
    pushRuntimeLog('执行失败', errorMessage);
  };

  // 【核心】用户主动中断对话运行
  // 场景：用户点击"停止生成"按钮，AI 正在输出回答但用户不需要了
  // 与 failRun 的区别：stopRun 是用户主动操作，不是错误；error 设为 null
  const stopRun = (detail = '用户中断本次生成') => {
    setWaitingForResponse(false);
    setIsThinking(false);
    setError(null);
    setCurrentTool(null);
    setStageState(null);
    pushRuntimeLog('已停止', detail);
  };

  return {
    currentTool,
    error,
    isThinking,
    runtimeLogs,
    stageHistory,
    stageState,
    waitingForResponse,
    beginRun,
    completeRun,
    failRun,
    pushRuntimeLog,
    recordStage,
    recordToolEnd,
    recordToolStart,
    resetRunState,
    setThinking: setIsThinking,
    stopRun,
  };
}
