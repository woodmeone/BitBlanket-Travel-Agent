'use client';

import { useState } from 'react';
import type { StreamStageEvent } from '@/types';
import { MAX_EVENT_LOGS, MAX_STAGE_LOGS, nowLabel, type RuntimeLog } from './shared';

interface UseChatRunStateResult {
  currentTool: string | null;
  error: string | null;
  isThinking: boolean;
  runtimeLogs: RuntimeLog[];
  stageHistory: StreamStageEvent[];
  stageState: StreamStageEvent | null;
  waitingForResponse: boolean;
  beginRun: (modeLabel: string) => void;
  completeRun: (label?: string, detail?: string) => void;
  failRun: (errorMessage: string) => void;
  pushRuntimeLog: (label: string, detail?: string) => void;
  recordStage: (stage: StreamStageEvent) => void;
  recordToolEnd: (toolName: string) => void;
  recordToolStart: (toolName: string) => void;
  resetRunState: () => void;
  setThinking: (value: boolean) => void;
  stopRun: (detail?: string) => void;
}

export function useChatRunState(): UseChatRunStateResult {
  const [waitingForResponse, setWaitingForResponse] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentTool, setCurrentTool] = useState<string | null>(null);
  const [stageState, setStageState] = useState<StreamStageEvent | null>(null);
  const [stageHistory, setStageHistory] = useState<StreamStageEvent[]>([]);
  const [runtimeLogs, setRuntimeLogs] = useState<RuntimeLog[]>([]);

  const pushRuntimeLog = (label: string, detail?: string) => {
    const item: RuntimeLog = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      label,
      detail,
      time: nowLabel(),
    };
    setRuntimeLogs((prev) => [...prev.slice(-MAX_EVENT_LOGS + 1), item]);
  };

  const resetRunState = () => {
    setWaitingForResponse(false);
    setIsThinking(false);
    setError(null);
    setCurrentTool(null);
    setStageState(null);
    setStageHistory([]);
    setRuntimeLogs([]);
  };

  const beginRun = (modeLabel: string) => {
    setWaitingForResponse(true);
    setIsThinking(true);
    setError(null);
    setCurrentTool(null);
    setStageState(null);
    setStageHistory([]);
    setRuntimeLogs([]);
    pushRuntimeLog('\u5f00\u59cb\u6267\u884c', `\u6a21\u5f0f: ${modeLabel}`);
  };

  const recordStage = (stage: StreamStageEvent) => {
    setStageState(stage);
    setStageHistory((prev) => [...prev, stage].slice(-MAX_STAGE_LOGS));
    pushRuntimeLog('\u9636\u6bb5', stage.label || stage.stage || '\u9636\u6bb5\u66f4\u65b0');
  };

  const recordToolStart = (toolName: string) => {
    setCurrentTool(toolName);
    pushRuntimeLog('\u5de5\u5177\u542f\u52a8', toolName);
  };

  const recordToolEnd = (toolName: string) => {
    setCurrentTool(null);
    pushRuntimeLog('\u5de5\u5177\u5b8c\u6210', toolName);
  };

  const completeRun = (
    label = '\u7ed3\u675f',
    detail = '\u5df2\u751f\u6210\u6700\u7ec8\u56de\u7b54'
  ) => {
    setWaitingForResponse(false);
    setIsThinking(false);
    setError(null);
    setCurrentTool(null);
    setStageState(null);
    pushRuntimeLog(label, detail);
  };

  const failRun = (errorMessage: string) => {
    setWaitingForResponse(false);
    setIsThinking(false);
    setError(errorMessage);
    setCurrentTool(null);
    setStageState(null);
    pushRuntimeLog('\u6267\u884c\u5931\u8d25', errorMessage);
  };

  const stopRun = (detail = '\u7528\u6237\u4e2d\u65ad\u672c\u6b21\u751f\u6210') => {
    setWaitingForResponse(false);
    setIsThinking(false);
    setError(null);
    setCurrentTool(null);
    setStageState(null);
    pushRuntimeLog('\u5df2\u505c\u6b62', detail);
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
