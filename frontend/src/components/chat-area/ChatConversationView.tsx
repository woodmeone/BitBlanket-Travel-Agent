'use client';

import React from 'react';
import MessageList from '@/components/MessageList';
import type { Message, PlanPreview, StreamStageEvent, SubagentEvent, TripPlanArtifact } from '@/types';
import type { StreamMetadata } from '@/services/api';
import ExecutionInsights from './ExecutionInsights';
import QuickStartPrompts from './QuickStartPrompts';
import type { RuntimeLog } from './shared';

interface ChatConversationViewProps {
  messages: Message[];
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  streamingMessage: string;
  streamingReasoning: string;
  waitingForResponse: boolean;
  isThinking: boolean;
  isStreaming: boolean;
  currentTool: string | null;
  reasoningExpanded: Record<string, boolean>;
  error: string | null;
  metadata: StreamMetadata | null;
  stageState: StreamStageEvent | null;
  stageHistory: StreamStageEvent[];
  runtimeLogs: RuntimeLog[];
  planPreview: PlanPreview | null;
  artifactState: TripPlanArtifact | null;
  activeSubagent: string | null;
  subagentEvents: SubagentEvent[];
  onContinuePrompt: (prompt: string) => void;
  onPickPrompt: (prompt: string) => void;
  onToggleReasoning: (messageId: string) => void;
}

const ChatConversationView: React.FC<ChatConversationViewProps> = ({
  messages,
  messagesEndRef,
  streamingMessage,
  streamingReasoning,
  waitingForResponse,
  isThinking,
  isStreaming,
  currentTool,
  reasoningExpanded,
  error,
  metadata,
  stageState,
  stageHistory,
  runtimeLogs,
  planPreview,
  artifactState,
  activeSubagent,
  subagentEvents,
  onContinuePrompt,
  onPickPrompt,
  onToggleReasoning,
}) => {
  return (
    <>
      <ExecutionInsights
        isStreaming={isStreaming}
        isThinking={isThinking}
        currentTool={currentTool}
        stageState={stageState}
        stageHistory={stageHistory}
        runtimeLogs={runtimeLogs}
        planPreview={planPreview}
        metadata={metadata}
        artifact={artifactState}
        activeSubagent={activeSubagent}
        subagentEvents={subagentEvents}
      />

      <MessageList
        messages={messages}
        streamingMessage={streamingMessage}
        streamingReasoning={streamingReasoning}
        isWaiting={waitingForResponse}
        isThinking={isThinking}
        currentTool={currentTool}
        reasoningExpanded={reasoningExpanded}
        onToggleReasoning={onToggleReasoning}
        onContinuePrompt={onContinuePrompt}
        streamingArtifact={artifactState}
        streamingSubagentEvents={subagentEvents}
      />

      {messages.length === 0 && !waitingForResponse && !isStreaming && <QuickStartPrompts onPickPrompt={onPickPrompt} />}

      {error && (
        <div
          style={{
            color: '#dc2626',
            padding: '14px 18px',
            background: 'linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%)',
            borderRadius: '12px',
            margin: '0 16px 16px',
            border: '1px solid rgba(220, 38, 38, 0.2)',
            boxShadow: '0 2px 8px rgba(220, 38, 38, 0.1)',
          }}
        >
          {error}
        </div>
      )}
      <div ref={messagesEndRef} />
    </>
  );
};

export default ChatConversationView;
