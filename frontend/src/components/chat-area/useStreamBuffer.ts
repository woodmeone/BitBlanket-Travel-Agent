// 【核心】useStreamBuffer 是流式输出缓冲管理 Hook
//
// 核心问题：AI 的响应是逐字逐句流式返回的，如果每收到一个字符就更新一次 React 状态，
// 会导致频繁重渲染，性能很差。
//
// 解决方案：使用"队列 + 定时刷新"机制：
// 1. 收到的流式数据先放入队列（enqueueAnswer / enqueueReasoning）
// 2. 定时器每隔一段时间从队列中取出一批字符，更新到状态中
// 3. 这样把高频的流式更新"降频"为低频的状态更新，兼顾流畅感和性能
//
// 场景举例：AI 正在输出"三亚5日游行程如下..."，每收到几个字就放入队列，
// 定时器每 50ms 取出一批字符显示，用户看到的是流畅的打字效果
'use client';

import type { Dispatch, RefObject, SetStateAction } from 'react';
import { useEffect, useRef } from 'react';
import {
  // 每次刷新从队列中取出的"回答"字符数
  ANSWER_CHARS_PER_TICK,
  // 每次刷新从队列中取出的"思考过程"字符数
  REASONING_CHARS_PER_TICK,
  // 定时刷新的时间间隔（毫秒），例如 50ms 刷新一次
  STREAM_FLUSH_INTERVAL_MS,
  // 从字符串头部取出指定数量字符的工具函数，返回 [取出的部分, 剩余部分]
  takeChars,
} from './shared';

// 入参接口：调用方需要提供的信息
interface UseStreamBufferArgs {
  // 聊天区域底部的 DOM 引用，用于自动滚动到底部
  messagesEndRef: RefObject<HTMLDivElement | null>;
  // 设置当前流式"回答"文本的 React 状态更新函数
  setStreamingMessage: Dispatch<SetStateAction<string>>;
  // 设置当前流式"思考过程"文本的 React 状态更新函数
  setStreamingReasoning: Dispatch<SetStateAction<string>>;
}

// 返回值接口：useStreamBuffer 暴露给外部使用的方法和数据
interface StreamBufferState {
  // 完整思考过程的 ref（包含已刷新和队列中尚未刷新的全部内容）
  fullReasoningRef: React.MutableRefObject<string>;
  // 完整回答的 ref（包含已刷新和队列中尚未刷新的全部内容）
  fullResponseRef: React.MutableRefObject<string>;
  // 思考过程的时间戳 ref，用于标记当前思考对应的触发时间
  reasoningTimestampRef: React.MutableRefObject<string>;
  // 滚动标记字符串，值变化时触发聊天区域重新滚动到底部
  // 基于 fullResponseRef 和 fullReasoningRef 的长度计算，长度变化时标记就变化
  streamScrollMarker: string;
  // 清除所有运行时 ref 数据（队列、完整文本、时间戳），通常在对话结束时调用
  clearStreamRuntimeRefs: () => void;
  // 将队列中剩余的字符一次性全部取出，追加到 fullResponseRef / fullReasoningRef
  // 用于流式输出结束时，确保没有字符遗留在队列中
  drainStreamingQueueToRefs: () => void;
  // 将流式"回答"内容放入队列，等待定时器取出显示
  enqueueAnswer: (content: string) => void;
  // 将流式"思考过程"内容放入队列，等待定时器取出显示
  enqueueReasoning: (content: string) => void;
  // 调度一次滚动到底部的操作（使用 requestAnimationFrame，避免重复调度）
  scheduleScrollToBottom: () => void;
  // 设置思考过程的时间戳
  setReasoningTimestamp: (timestamp: string) => void;
}

export function useStreamBuffer({
  messagesEndRef,
  setStreamingMessage,
  setStreamingReasoning,
}: UseStreamBufferArgs): StreamBufferState {
  // 【核心】完整回答文本的 ref
  // 为什么用 ref 而不是 state？因为 fullResponseRef 只在内部使用，
  // 不需要触发界面重渲染。如果用 state，每次更新都会导致组件重渲染，影响性能。
  // ref 的值变化不会触发重渲染，适合存储"不需要驱动界面显示"的数据。
  const fullResponseRef = useRef('');
  // 完整思考过程文本的 ref，同上
  const fullReasoningRef = useRef('');
  // 思考过程的时间戳 ref
  const reasoningTimestampRef = useRef('');
  // 【核心】流式缓冲队列 ref，存放尚未刷新到界面的字符
  // answer: 待显示的"回答"字符；reasoning: 待显示的"思考过程"字符
  // 场景：AI 流式返回"三亚"两个字，先存入 queue.answer = "三亚"，
  // 等定时器下次刷新时再取出来更新到界面上
  const streamQueueRef = useRef({ answer: '', reasoning: '' });
  // 定时器 ID 的 ref，用于在需要时清除定时器
  // ReturnType<typeof setInterval> 是 TypeScript 写法，表示 setInterval 返回值的类型
  const flushTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // requestAnimationFrame 返回的 ID 的 ref，用于取消已调度的滚动操作
  // requestAnimationFrame 是浏览器提供的 API，会在下一次屏幕刷新前执行回调，
  // 比 setTimeout 更适合做动画和滚动，因为它和浏览器的刷新节奏同步（通常 60fps）
  const scrollRafRef = useRef<number | null>(null);

  // 【核心】调度滚动到底部
  // 使用 requestAnimationFrame 确保每帧最多滚动一次，避免短时间内多次滚动造成卡顿
  // 如果 scrollRafRef.current !== null，说明已经调度了一次滚动，不需要重复调度
  const scheduleScrollToBottom = () => {
    if (scrollRafRef.current !== null) return;
    scrollRafRef.current = window.requestAnimationFrame(() => {
      // 执行完后清空 ID，表示这次滚动已完成，下次可以重新调度
      scrollRafRef.current = null;
      // scrollIntoView 是浏览器原生 API，让元素滚动到可视区域
      // behavior: 'auto' 表示立即跳转（不带平滑动画），block: 'end' 表示对齐到底部
      messagesEndRef.current?.scrollIntoView({ behavior: 'auto', block: 'end' });
    });
  };

  // 停止定时刷新定时器
  // clearInterval 是 JavaScript 清除 setInterval 定时器的方法
  // 如果不清除，定时器会一直运行，即使组件已经不需要它了
  const stopFlushTimer = () => {
    if (flushTimerRef.current !== null) {
      clearInterval(flushTimerRef.current);
      flushTimerRef.current = null;
    }
  };

  // 【核心】定时刷新回调：从队列中取出一批字符，更新到 React 状态
  // 这是"降频"机制的核心：不是来一个字符就更新一次，而是攒一批再更新
  const flushStreamingQueue = () => {
    let didUpdate = false;

    // 处理"思考过程"队列
    if (streamQueueRef.current.reasoning) {
      // takeChars 从字符串头部取出指定数量的字符
      // 例如 takeChars("正在分析您的需求...", 5) 返回 ["正在分析您", "的需求..."]
      const [chunk, rest] = takeChars(streamQueueRef.current.reasoning, REASONING_CHARS_PER_TICK);
      streamQueueRef.current.reasoning = rest;
      if (chunk) {
        didUpdate = true;
        // setStreamingReasoning 是 React 的 setState，prev 是之前的值
        // (prev) => prev + chunk 表示在已有文本后面追加新取出的字符
        setStreamingReasoning((prev) => prev + chunk);
      }
    }

    // 处理"回答"队列，逻辑同上
    if (streamQueueRef.current.answer) {
      const [chunk, rest] = takeChars(streamQueueRef.current.answer, ANSWER_CHARS_PER_TICK);
      streamQueueRef.current.answer = rest;
      if (chunk) {
        didUpdate = true;
        setStreamingMessage((prev) => prev + chunk);
      }
    }

    // 如果有内容更新，滚动到底部让用户看到最新内容
    if (didUpdate) scheduleScrollToBottom();
    // 如果队列已经清空，停止定时器（没有新内容就不需要继续刷新了）
    if (!streamQueueRef.current.answer && !streamQueueRef.current.reasoning) stopFlushTimer();
  };

  // 启动定时刷新定时器
  // setInterval 是 JavaScript 的定时器 API，每隔指定时间重复执行回调
  // 如果定时器已经在运行（flushTimerRef.current !== null），则不重复启动
  const startFlushTimer = () => {
    if (flushTimerRef.current !== null) return;
    flushTimerRef.current = setInterval(flushStreamingQueue, STREAM_FLUSH_INTERVAL_MS);
  };

  // 【核心】将流式"回答"内容放入队列
  // 场景：AI 返回了一小段文字"三亚"，调用 enqueueAnswer("三亚")，
  // 文字被追加到队列中，同时启动定时器等待刷新
  const enqueueAnswer = (content: string) => {
    if (!content) return;
    streamQueueRef.current.answer += content;
    startFlushTimer();
  };

  // 【核心】将流式"思考过程"内容放入队列，逻辑同 enqueueAnswer
  const enqueueReasoning = (content: string) => {
    if (!content) return;
    streamQueueRef.current.reasoning += content;
    startFlushTimer();
  };

  // 将队列中剩余的字符一次性全部取出，追加到 fullResponseRef / fullReasoningRef
  // 场景：流式输出结束时，队列里可能还有没被定时器取完的字符，
  // 调用此方法确保所有字符都被保存到完整文本 ref 中，不丢失任何内容
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

  // 清除所有运行时 ref 数据
  // 场景：开始新一轮对话时，需要清空上一轮的所有数据
  const clearStreamRuntimeRefs = () => {
    stopFlushTimer();
    streamQueueRef.current.answer = '';
    streamQueueRef.current.reasoning = '';
    fullResponseRef.current = '';
    fullReasoningRef.current = '';
    reasoningTimestampRef.current = '';
  };

  // 设置思考过程的时间戳
  const setReasoningTimestamp = (timestamp: string) => {
    reasoningTimestampRef.current = timestamp;
  };

  // 【核心】useEffect 的清理函数
  // useEffect 是 React 的副作用 Hook，组件挂载时执行回调，卸载时执行 return 的清理函数
  // 为什么需要清理？如果组件卸载（比如用户离开了聊天页面）但定时器还在运行，
  // 定时器会尝试更新已经不存在的组件，导致内存泄漏和报错。
  // cancelAnimationFrame 用于取消已调度但尚未执行的 requestAnimationFrame 回调
  useEffect(() => {
    return () => {
      stopFlushTimer();
      if (scrollRafRef.current !== null) {
        window.cancelAnimationFrame(scrollRafRef.current);
        scrollRafRef.current = null;
      }
    };
  }, []); // 空数组表示只在组件挂载/卸载时执行，不会因其他状态变化而重复执行

  // 滚动标记：基于 fullResponseRef 和 fullReasoningRef 的长度计算
  // 当完整文本长度变化时，标记值也变化，外部组件可以据此判断是否需要滚动
  // 除以 8 和 12 是为了降低标记变化的频率，避免每次字符变化都触发滚动
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
