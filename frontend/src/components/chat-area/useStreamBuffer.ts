'use client';

import type { Dispatch, RefObject, SetStateAction } from 'react';
import { useEffect, useRef } from 'react';
import {
  ANSWER_CHARS_PER_TICK,
  REASONING_CHARS_PER_TICK,
  STREAM_FLUSH_INTERVAL_MS,
  takeChars,
} from './shared';

interface UseStreamBufferArgs {
  messagesEndRef: RefObject<HTMLDivElement | null>;
  setStreamingMessage: Dispatch<SetStateAction<string>>;
  setStreamingReasoning: Dispatch<SetStateAction<string>>;
}

interface StreamBufferState {
  fullReasoningRef: React.MutableRefObject<string>;
  fullResponseRef: React.MutableRefObject<string>;
  reasoningTimestampRef: React.MutableRefObject<string>;
  streamScrollMarker: string;
  clearStreamRuntimeRefs: () => void;
  drainStreamingQueueToRefs: () => void;
  enqueueAnswer: (content: string) => void;
  enqueueReasoning: (content: string) => void;
  scheduleScrollToBottom: () => void;
  setReasoningTimestamp: (timestamp: string) => void;
}

export function useStreamBuffer({
  messagesEndRef,
  setStreamingMessage,
  setStreamingReasoning,
}: UseStreamBufferArgs): StreamBufferState {
  const fullResponseRef = useRef('');
  const fullReasoningRef = useRef('');
  const reasoningTimestampRef = useRef('');
  const streamQueueRef = useRef({ answer: '', reasoning: '' });
  const flushTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const scrollRafRef = useRef<number | null>(null);

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

  const setReasoningTimestamp = (timestamp: string) => {
    reasoningTimestampRef.current = timestamp;
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

  const streamScrollMarker = `${Math.floor(fullResponseRef.current.length / 8)}-${Math.floor(
    fullReasoningRef.current.length / 12
  )}`;

  return {
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
  };
}
