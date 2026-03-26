'use client';

import React, { useEffect, useRef, useState } from 'react';
import { App } from 'antd';
import { useAppContext } from '@/context/AppContext';
import { chatClient, sessionClient, shareClient, type StreamMetadata } from '@/services/api';
import type { PlanPreview, StreamStageEvent, SubagentEvent, TripPlanArtifact } from '@/types';
import { logger } from '@/utils/logger';
import { mergeTripPlanArtifact } from '@/utils/agentArtifacts';
import {
  messageTimestamp,
  subagentLabel,
  type ActiveView,
  type ComparePlanCount,
  type RuntimeLog,
} from './shared';
import { buildStoppedMessageContent, prepareChatInput } from './chatInputPolicy';
import { useArtifactRuntimeState } from './useArtifactRuntimeState';
import { useChatRunState } from './useChatRunState';
import { useStreamBuffer } from './useStreamBuffer';
import { buildCompletionDiagnostics, buildFinalReasoning, buildStoppedDiagnostics } from './runtimeMessageBuilders';

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
  const [reasoningExpanded, setReasoningExpanded] = useState<Record<string, boolean>>({});
  const [selectedConstraints, setSelectedConstraints] = useState<string[]>([]);
  const [budgetUpperLimit, setBudgetUpperLimit] = useState<number | null>(null);
  const [compareModeEnabled, setCompareModeEnabled] = useState(false);
  const [comparePlanCount, setComparePlanCount] = useState<ComparePlanCount>(2);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const stopRef = useRef(false);
  const skipNextSessionResetRef = useRef(false);
  const metadataRef = useRef<StreamMetadata | null>(null);
  const hasHandledShareRef = useRef(false);
  const {
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
    setThinking,
    stopRun,
  } = useChatRunState();
  const {
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
  } = useArtifactRuntimeState();
  const {
    fullReasoningRef,
    fullResponseRef,
    reasoningTimestampRef,
    streamScrollMarker,
    clearStreamRuntimeRefs,
    drainStreamingQueueToRefs,
    enqueueAnswer,
    enqueueReasoning,
    scheduleScrollToBottom,
    setReasoningTimestamp,
  } = useStreamBuffer({
    messagesEndRef,
    setStreamingMessage,
    setStreamingReasoning,
  });

  const clearArtifactRuntimeState = () => {
    metadataRef.current = null;
    resetArtifactRuntimeState();
  };

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
    resetRunState();
    setIsStreaming(false);
    setStopStreaming(false);
    clearArtifactRuntimeState();
    stopRef.current = false;
  }, [currentSessionId, resetRunState, setIsStreaming, setStopStreaming]);

  const toggleReasoning = (messageId: string) => {
    setReasoningExpanded((prev) => ({ ...prev, [messageId]: !prev[messageId] }));
  };

  const selectedConstraintCount =
    selectedConstraints.length + (budgetUpperLimit && budgetUpperLimit > 0 ? 1 : 0) + (compareModeEnabled ? 1 : 0);

  const handleSend = async () => {
    const preparedInput = prepareChatInput(inputValue, {
      selectedConstraints,
      budgetUpperLimit,
      compareModeEnabled,
      comparePlanCount,
    });
    if (!preparedInput) {
      message.warning('请输入内容');
      return;
    }

    try {
      const { displayMessage, enrichedPrompt, sessionName } = preparedInput;
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
        content: displayMessage,
        timestamp: messageTimestamp(),
      });

      clearStreamRuntimeRefs();
      setInputValue('');
      setIsStreaming(true);
      setStopStreaming(false);
      setStreamingMessage('');
      setStreamingReasoning('');
      clearArtifactRuntimeState();
      stopRef.current = false;
      beginRun(chatMode.toUpperCase());

      if (isFirstMessage && sessionId) {
        try {
          await sessionClient.updateSessionName(sessionId, sessionName);
        } catch (err) {
          logger.error('设置会话名称失败:', err);
        }
      }

      await chatClient.fetchStreamChat(
        { message: enrichedPrompt, display_message: displayMessage, session_id: sessionId, mode: chatMode },
        {
          onSessionId: (sid) => {
            if (!currentSessionId) {
              skipNextSessionResetRef.current = true;
              setCurrentSessionId(sid);
            }
          },
          onStage: (stage) => recordStage(stage),
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
          onReasoningStart: () => setThinking(true),
          onReasoningTimestamp: (timestamp) => {
            setReasoningTimestamp(timestamp);
          },
          onReasoningEnd: () => setThinking(false),
          onAnswerStart: () => setThinking(false),
          onToolStart: (toolName) => recordToolStart(toolName),
          onToolEnd: (toolName) => recordToolEnd(toolName),
          onMetadata: (data) => {
            metadataRef.current = data;
            applyArtifactPatch(data.artifact);
            pushRuntimeLog('执行完成', `工具 ${data.toolsUsed.length} 个`);
          },
          onError: (errorMsg) => {
            message.destroy();
            message.error(`错误: ${errorMsg}`);
            clearStreamRuntimeRefs();
            setIsStreaming(false);
            failRun(errorMsg);
            clearArtifactRuntimeState();
            stopRef.current = false;
            fullResponseRef.current = `抱歉，发生错误：${errorMsg}`;
            setStreamingMessage(fullResponseRef.current);
          },
          onComplete: (completion) => {
            message.destroy();
            drainStreamingQueueToRefs();

            const finalReasoning = buildFinalReasoning(fullReasoningRef.current, reasoningTimestampRef.current);
            const finalContent = fullResponseRef.current;
            const finalMetadata = metadataRef.current;
            const finalArtifact = mergeTripPlanArtifact(artifactRef.current, completion?.artifact);
            const finalSubagentEvents = subagentEventsRef.current;
            const finalDiagnostics = buildCompletionDiagnostics({
              artifact: finalArtifact,
              completion,
              metadata: finalMetadata,
              subagentEvents: finalSubagentEvents,
            });

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
            setIsStreaming(false);
            stopRef.current = false;
            clearArtifactRuntimeState();
            completeRun();
          },
          onStop: () => stopRef.current,
        }
      );

      refreshSessions();
    } catch (err: unknown) {
      message.destroy();
      const errorMsg = err instanceof Error ? err.message : '未知错误';
      message.error(`发送失败: ${errorMsg}`);
      setIsStreaming(false);
      setStreamingMessage('');
      setStreamingReasoning('');
      failRun(errorMsg);
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

    setIsStreaming(false);
    stopRun();

    if (stoppedContent || stoppedReasoning) {
      addMessage({
        role: 'assistant',
        content: buildStoppedMessageContent(stoppedContent),
        reasoning: stoppedReasoning,
        diagnostics: buildStoppedDiagnostics({ artifact: stoppedArtifact, subagentEvents: stoppedSubagentEvents }),
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
