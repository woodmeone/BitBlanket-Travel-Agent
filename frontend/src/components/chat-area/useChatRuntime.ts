'use client';

import React, { useEffect, useRef, useState } from 'react';
import { App } from 'antd';
import { useAppContext } from '@/context/AppContext';
import { chatClient, sessionClient, shareClient, type StreamMetadata } from '@/services/api';
import type { ArtifactPatch, PlanPreview, StreamStageEvent, SubagentEvent, TripPlanArtifact } from '@/types';
import { logger } from '@/utils/logger';
import { mergeTripPlanArtifact } from '@/utils/agentArtifacts';
import {
  ANSWER_CHARS_PER_TICK,
  buildEnhancedPrompt,
  MAX_EVENT_LOGS,
  MAX_STAGE_LOGS,
  MAX_SUBAGENT_EVENTS,
  messageTimestamp,
  nowLabel,
  REASONING_CHARS_PER_TICK,
  STREAM_FLUSH_INTERVAL_MS,
  subagentLabel,
  takeChars,
  type ActiveView,
  type ComparePlanCount,
  type RuntimeLog,
} from './shared';

interface UseChatRuntimeResult {
  activeSubagent: string | null;
  activeView: ActiveView;
  artifactState: TripPlanArtifact | null;
  budgetUpperLimit: number | null;
  chatMode: ReturnType<typeof useAppContext>['chatMode'];
  compareModeEnabled: boolean;
  comparePlanCount: ComparePlanCount;
  currentTool: string | null;
  error: string | null;
  inputValue: string;
  isStreaming: boolean;
  isThinking: boolean;
  messages: ReturnType<typeof useAppContext>['messages'];
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  metadata: StreamMetadata | null;
  planPreview: PlanPreview | null;
  reasoningExpanded: Record<string, boolean>;
  runtimeLogs: RuntimeLog[];
  selectedConstraintCount: number;
  selectedConstraints: string[];
  stageHistory: StreamStageEvent[];
  stageState: StreamStageEvent | null;
  streamingMessage: string;
  streamingReasoning: string;
  subagentEvents: SubagentEvent[];
  waitingForResponse: boolean;
  handleContinueRefine: (prompt: string) => void;
  handlePickQuickStartPrompt: (prompt: string) => void;
  handleSend: () => Promise<void>;
  handleStop: () => void;
  handleUsePromptFromExplorer: (prompt: string) => void;
  setActiveView: React.Dispatch<React.SetStateAction<ActiveView>>;
  setBudgetUpperLimit: React.Dispatch<React.SetStateAction<number | null>>;
  setChatMode: ReturnType<typeof useAppContext>['setChatMode'];
  setCompareModeEnabled: React.Dispatch<React.SetStateAction<boolean>>;
  setComparePlanCount: React.Dispatch<React.SetStateAction<ComparePlanCount>>;
  setInputValue: React.Dispatch<React.SetStateAction<string>>;
  setSelectedConstraints: React.Dispatch<React.SetStateAction<string[]>>;
  toggleReasoning: (messageId: string) => void;
}

export function useChatRuntime(): UseChatRuntimeResult {
  const {
    currentSessionId,
    setCurrentSessionId,
    messages,
    addMessage,
    isStreaming,
    setIsStreaming,
    setStopStreaming,
    refreshSessions,
    chatMode,
    setChatMode,
    setMessages,
  } = useAppContext();
  const { message } = App.useApp();

  const [activeView, setActiveView] = useState<ActiveView>('chat');
  const [inputValue, setInputValue] = useState('');
  const [streamingMessage, setStreamingMessage] = useState('');
  const [streamingReasoning, setStreamingReasoning] = useState('');
  const [waitingForResponse, setWaitingForResponse] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reasoningExpanded, setReasoningExpanded] = useState<Record<string, boolean>>({});
  const [currentTool, setCurrentTool] = useState<string | null>(null);
  const [stageState, setStageState] = useState<StreamStageEvent | null>(null);
  const [stageHistory, setStageHistory] = useState<StreamStageEvent[]>([]);
  const [runtimeLogs, setRuntimeLogs] = useState<RuntimeLog[]>([]);
  const [planPreview, setPlanPreview] = useState<PlanPreview | null>(null);
  const [artifactState, setArtifactState] = useState<TripPlanArtifact | null>(null);
  const [subagentEvents, setSubagentEvents] = useState<SubagentEvent[]>([]);
  const [activeSubagent, setActiveSubagent] = useState<string | null>(null);
  const [selectedConstraints, setSelectedConstraints] = useState<string[]>([]);
  const [budgetUpperLimit, setBudgetUpperLimit] = useState<number | null>(null);
  const [compareModeEnabled, setCompareModeEnabled] = useState(false);
  const [comparePlanCount, setComparePlanCount] = useState<ComparePlanCount>(2);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const stopRef = useRef(false);
  const skipNextSessionResetRef = useRef(false);
  const metadataRef = useRef<StreamMetadata | null>(null);
  const artifactRef = useRef<TripPlanArtifact | null>(null);
  const subagentEventsRef = useRef<SubagentEvent[]>([]);
  const fullResponseRef = useRef('');
  const fullReasoningRef = useRef('');
  const reasoningTimestampRef = useRef('');
  const subagentEventKeyRef = useRef(0);
  const streamQueueRef = useRef({ answer: '', reasoning: '' });
  const flushTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const scrollRafRef = useRef<number | null>(null);
  const hasHandledShareRef = useRef(false);

  const pushRuntimeLog = (label: string, detail?: string) => {
    const item: RuntimeLog = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      label,
      detail,
      time: nowLabel(),
    };
    setRuntimeLogs((prev) => [...prev.slice(-MAX_EVENT_LOGS + 1), item]);
  };

  const applyArtifactPatch = (patch: ArtifactPatch | TripPlanArtifact | null | undefined) => {
    const merged = mergeTripPlanArtifact(artifactRef.current, patch);
    artifactRef.current = merged;
    setArtifactState(merged);
  };

  const recordSubagentEvent = (event: SubagentEvent) => {
    subagentEventKeyRef.current += 1;
    const stamped: SubagentEvent = {
      ...event,
      timestamp: event.timestamp || nowLabel(),
      clientKey: event.clientKey || `subagent-event-${Date.now()}-${subagentEventKeyRef.current}`,
    };
    const nextEvents = [...subagentEventsRef.current.slice(-MAX_SUBAGENT_EVENTS + 1), stamped];
    subagentEventsRef.current = nextEvents;
    setSubagentEvents(nextEvents);
    if (event.status) {
      setActiveSubagent((current) => (current === event.subagent ? null : current));
      return;
    }
    setActiveSubagent(event.subagent);
  };

  const scheduleScrollToBottom = () => {
    if (scrollRafRef.current !== null) return;
    scrollRafRef.current = window.requestAnimationFrame(() => {
      scrollRafRef.current = null;
      messagesEndRef.current?.scrollIntoView({ behavior: 'auto', block: 'end' });
    });
  };

  const stopFlushTimer = () => {
    if (flushTimerRef.current !== null) {
      clearInterval(flushTimerRef.current);
      flushTimerRef.current = null;
    }
  };

  const flushStreamingQueue = () => {
    let didUpdate = false;

    if (streamQueueRef.current.reasoning) {
      const [chunk, rest] = takeChars(streamQueueRef.current.reasoning, REASONING_CHARS_PER_TICK);
      streamQueueRef.current.reasoning = rest;
      if (chunk) {
        didUpdate = true;
        setStreamingReasoning((prev) => prev + chunk);
      }
    }

    if (streamQueueRef.current.answer) {
      const [chunk, rest] = takeChars(streamQueueRef.current.answer, ANSWER_CHARS_PER_TICK);
      streamQueueRef.current.answer = rest;
      if (chunk) {
        didUpdate = true;
        setStreamingMessage((prev) => prev + chunk);
      }
    }

    if (didUpdate) scheduleScrollToBottom();
    if (!streamQueueRef.current.answer && !streamQueueRef.current.reasoning) stopFlushTimer();
  };

  const startFlushTimer = () => {
    if (flushTimerRef.current !== null) return;
    flushTimerRef.current = setInterval(flushStreamingQueue, STREAM_FLUSH_INTERVAL_MS);
  };

  const enqueueAnswer = (content: string) => {
    if (!content) return;
    streamQueueRef.current.answer += content;
    startFlushTimer();
  };

  const enqueueReasoning = (content: string) => {
    if (!content) return;
    streamQueueRef.current.reasoning += content;
    startFlushTimer();
  };

  const drainStreamingQueueToRefs = () => {
    if (streamQueueRef.current.answer) {
      fullResponseRef.current += streamQueueRef.current.answer;
      streamQueueRef.current.answer = '';
    }
    if (streamQueueRef.current.reasoning) {
      fullReasoningRef.current += streamQueueRef.current.reasoning;
      streamQueueRef.current.reasoning = '';
    }
  };

  const clearStreamRuntimeRefs = () => {
    stopFlushTimer();
    streamQueueRef.current.answer = '';
    streamQueueRef.current.reasoning = '';
    fullResponseRef.current = '';
    fullReasoningRef.current = '';
    reasoningTimestampRef.current = '';
  };

  const clearArtifactRuntimeState = () => {
    artifactRef.current = null;
    subagentEventsRef.current = [];
    subagentEventKeyRef.current = 0;
    metadataRef.current = null;
    setArtifactState(null);
    setSubagentEvents([]);
    setActiveSubagent(null);
    setPlanPreview(null);
  };

  useEffect(() => {
    return () => {
      stopFlushTimer();
      if (scrollRafRef.current !== null) {
        window.cancelAnimationFrame(scrollRafRef.current);
        scrollRafRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (hasHandledShareRef.current) return;

    const params = new URLSearchParams(window.location.search);
    const shareId = params.get('share');
    if (!shareId) return;

    hasHandledShareRef.current = true;
    const loadSharedContent = async () => {
      try {
        const result = await shareClient.getShareDetail(shareId);
        setCurrentSessionId(null);
        setMessages([
          {
            role: 'assistant',
            content: result.content,
            timestamp: messageTimestamp(),
          },
        ]);
        setActiveView('chat');
        message.success('已打开分享方案');
      } catch (error) {
        message.error(`加载分享失败: ${error instanceof Error ? error.message : '未知错误'}`);
      }
    };

    loadSharedContent();
  }, [message, setCurrentSessionId, setMessages]);

  const streamScrollMarker = `${Math.floor(streamingMessage.length / 8)}-${Math.floor(
    streamingReasoning.length / 12
  )}`;
  useEffect(() => {
    scheduleScrollToBottom();
  }, [messages.length, streamScrollMarker, isThinking, waitingForResponse, currentTool, runtimeLogs.length]);

  useEffect(() => {
    if (skipNextSessionResetRef.current) {
      skipNextSessionResetRef.current = false;
      return;
    }

    clearStreamRuntimeRefs();
    setStreamingMessage('');
    setStreamingReasoning('');
    setWaitingForResponse(false);
    setIsThinking(false);
    setError(null);
    setIsStreaming(false);
    setStopStreaming(false);
    setCurrentTool(null);
    setStageState(null);
    setStageHistory([]);
    setRuntimeLogs([]);
    clearArtifactRuntimeState();
    stopRef.current = false;
  }, [currentSessionId, setIsStreaming, setStopStreaming]);

  const toggleReasoning = (messageId: string) => {
    setReasoningExpanded((prev) => ({ ...prev, [messageId]: !prev[messageId] }));
  };

  const selectedConstraintCount =
    selectedConstraints.length + (budgetUpperLimit && budgetUpperLimit > 0 ? 1 : 0) + (compareModeEnabled ? 1 : 0);

  const handleSend = async () => {
    const trimmed = inputValue.trim();
    if (!trimmed) {
      message.warning('请输入内容');
      return;
    }

    try {
      const enrichedPrompt = buildEnhancedPrompt(trimmed, {
        selectedConstraints,
        budgetUpperLimit,
        compareModeEnabled,
        comparePlanCount,
      });
      const isFirstMessage = !currentSessionId || messages.length === 0;
      let sessionId = currentSessionId;
      if (!sessionId) {
        const data = await sessionClient.createSession();
        sessionId = data.session_id;
        skipNextSessionResetRef.current = true;
        setCurrentSessionId(sessionId);
      }

      addMessage({
        role: 'user',
        content: trimmed,
        timestamp: messageTimestamp(),
      });

      clearStreamRuntimeRefs();
      setInputValue('');
      setIsStreaming(true);
      setStopStreaming(false);
      setWaitingForResponse(true);
      setIsThinking(true);
      setError(null);
      setCurrentTool(null);
      setStreamingMessage('');
      setStreamingReasoning('');
      setStageState(null);
      setStageHistory([]);
      setRuntimeLogs([]);
      clearArtifactRuntimeState();
      stopRef.current = false;
      pushRuntimeLog('开始执行', `模式: ${chatMode.toUpperCase()}`);

      if (isFirstMessage && sessionId) {
        try {
          const sessionName = trimmed.slice(0, 15) + (trimmed.length > 15 ? '...' : '');
          await sessionClient.updateSessionName(sessionId, sessionName);
        } catch (err) {
          logger.error('设置会话名称失败:', err);
        }
      }

      await chatClient.fetchStreamChat(
        { message: enrichedPrompt, display_message: trimmed, session_id: sessionId, mode: chatMode },
        {
          onSessionId: (sid) => {
            if (!currentSessionId) {
              skipNextSessionResetRef.current = true;
              setCurrentSessionId(sid);
            }
          },
          onStage: (stage) => {
            setStageState(stage);
            setStageHistory((prev) => [...prev, stage].slice(-MAX_STAGE_LOGS));
            pushRuntimeLog('阶段', stage.label || stage.stage || '阶段更新');
          },
          onPlanPreview: (preview) => {
            setPlanPreview(preview);
            applyArtifactPatch(preview.artifact ?? preview.artifactPatch);
            pushRuntimeLog('计划预览', preview.intent || '已生成');
          },
          onSubagentStart: (event) => {
            recordSubagentEvent(event);
            pushRuntimeLog('子 Agent 启动', `${subagentLabel(event.subagent)} | ${event.skills?.join(', ') || 'no skills'}`);
          },
          onSubagentEnd: (event) => {
            recordSubagentEvent(event);
            pushRuntimeLog('子 Agent 完成', `${subagentLabel(event.subagent)} | ${event.status || 'completed'}`);
          },
          onArtifactPatch: (subagent, patch) => {
            applyArtifactPatch(patch);
            pushRuntimeLog('Artifact 更新', `${subagentLabel(subagent)} 提交结构化补丁`);
          },
          onChunk: (content) => {
            fullResponseRef.current += content;
            enqueueAnswer(content);
          },
          onReasoning: (content) => {
            fullReasoningRef.current += content;
            enqueueReasoning(content);
          },
          onReasoningStart: () => setIsThinking(true),
          onReasoningTimestamp: (timestamp) => {
            reasoningTimestampRef.current = timestamp;
          },
          onReasoningEnd: () => setIsThinking(false),
          onAnswerStart: () => setIsThinking(false),
          onToolStart: (toolName) => {
            setCurrentTool(toolName);
            pushRuntimeLog('工具启动', toolName);
          },
          onToolEnd: (toolName) => {
            setCurrentTool(null);
            pushRuntimeLog('工具完成', toolName);
          },
          onMetadata: (data) => {
            metadataRef.current = data;
            applyArtifactPatch(data.artifact);
            pushRuntimeLog('执行完成', `工具 ${data.toolsUsed.length} 个`);
          },
          onError: (errorMsg) => {
            message.destroy();
            message.error(`错误: ${errorMsg}`);
            clearStreamRuntimeRefs();
            setWaitingForResponse(false);
            setIsThinking(false);
            setCurrentTool(null);
            setError(errorMsg);
            setStageState(null);
            clearArtifactRuntimeState();
            pushRuntimeLog('执行失败', errorMsg);
            fullResponseRef.current = `抱歉，发生错误：${errorMsg}`;
            setStreamingMessage(fullResponseRef.current);
          },
          onComplete: (completion) => {
            message.destroy();
            drainStreamingQueueToRefs();

            const finalReasoning = reasoningTimestampRef.current
              ? `[Timestamp: ${reasoningTimestampRef.current}]\n\n${fullReasoningRef.current}`
              : fullReasoningRef.current;
            const finalContent = fullResponseRef.current;
            const finalMetadata = metadataRef.current;
            const finalArtifact = mergeTripPlanArtifact(artifactRef.current, completion?.artifact);
            const finalSubagentEvents = subagentEventsRef.current;
            const finalDiagnostics =
              finalMetadata || finalArtifact || finalSubagentEvents.length > 0
                ? {
                    toolsUsed: finalMetadata?.toolsUsed || finalArtifact?.toolsUsed || [],
                    verificationPassed: finalMetadata?.verificationPassed ?? finalArtifact?.verification.passed ?? null,
                    staleResultCount: finalMetadata?.staleResultCount ?? finalArtifact?.budget.staleResultCount ?? 0,
                    fallbackSteps: finalMetadata?.fallbackSteps ?? finalArtifact?.budget.fallbackSteps ?? 0,
                    planId: finalMetadata?.planId ?? finalArtifact?.itinerary.planId ?? null,
                    executionStats: finalMetadata?.executionStats ?? finalArtifact?.budget.summary,
                    artifact: finalArtifact,
                    subagentEvents: finalSubagentEvents,
                    runId: completion?.runId || finalMetadata?.runId,
                    requestId: completion?.requestId || finalMetadata?.requestId,
                    traceId: completion?.traceId || finalMetadata?.traceId,
                  }
                : undefined;

            clearStreamRuntimeRefs();
            addMessage({
              role: 'assistant',
              content: finalContent,
              reasoning: finalReasoning,
              diagnostics: finalDiagnostics,
              timestamp: messageTimestamp(),
            });

            setStreamingMessage('');
            setStreamingReasoning('');
            setWaitingForResponse(false);
            setIsStreaming(false);
            setIsThinking(false);
            setCurrentTool(null);
            setStageState(null);
            stopRef.current = false;
            clearArtifactRuntimeState();
            pushRuntimeLog('结束', '已生成最终回答');
          },
          onStop: () => stopRef.current,
        }
      );

      refreshSessions();
    } catch (err: unknown) {
      message.destroy();
      const errorMsg = err instanceof Error ? err.message : '未知错误';
      message.error(`发送失败: ${errorMsg}`);
      setWaitingForResponse(false);
      setIsThinking(false);
      setCurrentTool(null);
      setError(errorMsg);
      clearArtifactRuntimeState();
      clearStreamRuntimeRefs();
    }
  };

  const handleStop = () => {
    stopRef.current = true;
    setStopStreaming(true);
    drainStreamingQueueToRefs();

    const stoppedContent = fullResponseRef.current;
    const stoppedReasoning = fullReasoningRef.current;
    const stoppedArtifact = artifactRef.current;
    const stoppedSubagentEvents = subagentEventsRef.current;
    clearStreamRuntimeRefs();

    setWaitingForResponse(false);
    setIsThinking(false);
    setIsStreaming(false);
    setCurrentTool(null);
    setStageState(null);
    metadataRef.current = null;
    pushRuntimeLog('已停止', '用户中断本次生成');

    if (stoppedContent || stoppedReasoning) {
      addMessage({
        role: 'assistant',
        content: `${stoppedContent || '已停止生成'}\n\n⚠️ 已停止生成`,
        reasoning: stoppedReasoning,
        diagnostics:
          stoppedArtifact || stoppedSubagentEvents.length > 0
            ? { artifact: stoppedArtifact, subagentEvents: stoppedSubagentEvents }
            : undefined,
        timestamp: messageTimestamp(),
      });
    }

    setStreamingMessage('');
    setStreamingReasoning('');
    clearArtifactRuntimeState();
  };

  const handleUsePromptFromExplorer = (prompt: string) => {
    setInputValue(prompt);
    setChatMode('plan');
    setActiveView('chat');
  };

  const handleContinueRefine = (prompt: string) => {
    setInputValue(prompt);
    setChatMode('plan');
    setActiveView('chat');
    message.info('已填入细化指令，按回车可继续生成。');
  };

  const handlePickQuickStartPrompt = (prompt: string) => {
    setInputValue(prompt);
  };

  return {
    activeSubagent,
    activeView,
    artifactState,
    budgetUpperLimit,
    chatMode,
    compareModeEnabled,
    comparePlanCount,
    currentTool,
    error,
    inputValue,
    isStreaming,
    isThinking,
    messages,
    messagesEndRef,
    metadata: metadataRef.current,
    planPreview,
    reasoningExpanded,
    runtimeLogs,
    selectedConstraintCount,
    selectedConstraints,
    stageHistory,
    stageState,
    streamingMessage,
    streamingReasoning,
    subagentEvents,
    waitingForResponse,
    handleContinueRefine,
    handlePickQuickStartPrompt,
    handleSend,
    handleStop,
    handleUsePromptFromExplorer,
    setActiveView,
    setBudgetUpperLimit,
    setChatMode,
    setCompareModeEnabled,
    setComparePlanCount,
    setInputValue,
    setSelectedConstraints,
    toggleReasoning,
  };
}
