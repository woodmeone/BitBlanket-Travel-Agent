'use client';

import React, { useMemo } from 'react';
import type { Message, SubagentEvent, TripPlanArtifact } from '@/types';
import { MessageItem, StreamingMessageItem } from './message-list/messageItems';

interface Props {
  messages: Message[];
  streamingMessage?: string;
  streamingReasoning?: string;
  isWaiting?: boolean;
  isThinking?: boolean;
  currentTool?: string | null;
  reasoningExpanded?: Record<string, boolean>;
  onToggleReasoning?: (messageId: string) => void;
  onContinuePrompt?: (prompt: string) => void;
  streamingArtifact?: TripPlanArtifact | null;
  streamingSubagentEvents?: SubagentEvent[];
}

const MessageList: React.FC<Props> = ({
  messages,
  streamingMessage,
  streamingReasoning,
  isWaiting = false,
  isThinking = false,
  currentTool = null,
  reasoningExpanded = {},
  onToggleReasoning,
  onContinuePrompt,
  streamingArtifact,
  streamingSubagentEvents = [],
}) => {
  const toggleHandler = onToggleReasoning || (() => {});

  const renderedMessages = useMemo(
    () =>
      messages.map((msg, index) => {
        const messageId = `msg_${msg.timestamp}_${index}`;

        return (
          <MessageItem
            key={messageId}
            msg={msg}
            messageId={messageId}
            reasoningExpanded={reasoningExpanded}
            onToggleReasoning={toggleHandler}
            onContinuePrompt={onContinuePrompt}
          />
        );
      }),
    [messages, reasoningExpanded, toggleHandler, onContinuePrompt]
  );

  const shouldShowStreamingDialog =
    isWaiting ||
    isThinking ||
    Boolean(streamingMessage && streamingMessage.length > 0) ||
    Boolean(streamingReasoning && streamingReasoning.length > 0);

  return (
    <div className="chat-message-container" style={{ maxWidth: '900px', margin: '0 auto', width: '100%' }}>
      {renderedMessages}

      {shouldShowStreamingDialog && (
        <StreamingMessageItem
          content={streamingMessage || ''}
          reasoning={streamingReasoning}
          isWaiting={isWaiting}
          isThinking={isThinking}
          currentTool={currentTool}
          artifact={streamingArtifact}
          subagentEvents={streamingSubagentEvents}
        />
      )}
    </div>
  );
};

export default MessageList;
