/* 【核心】会话历史状态管理钩子 —— 管理聊天会话的创建、切换、消息加载和缓存 */
/* 自定义 Hook 是 React 中复用状态逻辑的方式，可以把复杂的状态管理逻辑从组件中抽离出来 */
/* 应用场景：用户在聊天界面中切换不同的会话（聊天记录），每个会话有独立的消息列表 */
/* 例如：用户从"东京旅行"会话切换到"巴黎旅行"会话，这个钩子负责加载对应的消息、缓存旧消息等 */
'use client';

/* useEffect：React 的"副作用"钩子，在组件渲染后执行异步操作（如请求数据） */
/* useRef：创建一个跨渲染周期持久化的引用，修改它不会触发重新渲染 */
/* useState：创建可变状态 */
import { useEffect, useRef, useState } from 'react';
/* 导入各种 API 客户端，用于与后端通信 */
import { artifactClient, modelClient, sessionClient } from '@/services/api';
/* 导入类型定义 */
import type { Message, SessionInfo } from '@/types';
/* 导入日志工具 */
import { logger } from '@/utils/logger';
/* 导入消息处理工具函数 */
import {
  findLatestAssistantMessageIndex,   // 查找最新的 AI 助手消息索引
  hydrateMessagesWithLatestArtifact, // 将最新的旅行方案产物注入到消息中
  normalizePersistedMessages,        // 规范化从后端加载的消息数据
} from '@/utils/sessionMessages';

/* localStorage 中存储当前会话 ID 的键名 */
/* 应用场景：用户关闭浏览器后再次打开，能自动恢复到上次的会话 */
export const SESSION_STORAGE_KEY = 'bitblanket-current-session-id';

/* 判断缓存中是否包含指定会话的消息 */
/* cache 是一个键值对（会话ID → 消息数组），sessionId 是要查询的会话 ID */
export function hasOwnSessionMessages(cache: Record<string, Message[]>, sessionId: string): boolean {
  /* Object.prototype.hasOwnProperty.call 是安全的方式检查对象是否有某个属性 */
  return Object.prototype.hasOwnProperty.call(cache, sessionId);
}

/* 【核心】构建可见的会话列表 */
/* 应用场景：侧边栏显示会话列表时，需要过滤掉空会话（没有消息且超过1小时未活跃的会话） */
/* 例如：用户创建了5个会话，但只有2个有聊天记录，侧边栏只显示这2个 */
export function buildVisibleSessions(
  sessions: SessionInfo[],       // 所有会话列表
  options: { includeEmpty?: boolean; now?: Date } = {}  // 选项：是否包含空会话、当前时间
): SessionInfo[] {
  /* 去重：用 Map 按会话 ID 去重（保留最后一个） */
  const uniqueSessions = Array.from(new Map(sessions.map((session) => [session.session_id, session])).values());
  /* 如果要求包含空会话，直接返回去重后的列表 */
  if (options.includeEmpty) return uniqueSessions;

  /* 计算一小时前的时间 */
  const now = options.now ?? new Date();
  const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
  /* 过滤：保留有消息的会话，或者最近1小时内活跃的空会话 */
  return uniqueSessions.filter((session) => session.message_count > 0 || new Date(session.last_active) > oneHourAgo);
}

/* 从 localStorage 中读取存储的会话 ID */
/* search 是 URL 查询字符串（如 ?share=xxx），storage 是 localStorage */
export function readStoredSessionId(search: string, storage: Pick<Storage, 'getItem'>): string | null {
  /* 如果 URL 中包含 share= 参数（分享链接），不恢复本地会话 */
  if (search.includes('share=')) return null;
  return storage.getItem(SESSION_STORAGE_KEY);
}

/* 将当前会话 ID 持久化到 localStorage */
export function persistStoredSessionId(storage: Pick<Storage, 'setItem' | 'removeItem'>, sessionId: string | null): void {
  if (sessionId) {
    /* 有会话 ID 时保存 */
    storage.setItem(SESSION_STORAGE_KEY, sessionId);
    return;
  }
  /* 没有会话 ID 时删除存储 */
  storage.removeItem(SESSION_STORAGE_KEY);
}

/* 钩子选项接口 */
interface UseSessionHistoryStateOptions {
  onRecoveredModelId: (modelId: string) => void;  // 恢复模型 ID 的回调函数
}

/* 钩子返回值接口 */
interface UseSessionHistoryStateResult {
  currentSessionId: string | null;                // 当前会话 ID
  setCurrentSessionId: (id: string | null) => void;  // 设置当前会话 ID
  switchSession: (id: string | null) => Promise<void>;  // 切换会话
  refreshSessions: (includeEmpty?: boolean) => Promise<void>;  // 刷新会话列表
  sessions: SessionInfo[];                        // 会话列表
  messages: Message[];                            // 当前会话的消息列表
  addMessage: (message: Message) => void;         // 添加消息
  clearMessages: () => void;                      // 清空消息
  setMessages: (messages: Message[]) => void;     // 替换消息列表
}

/* 【核心】会话历史状态管理钩子 */
/* 这个钩子封装了会话管理的所有逻辑，包括：会话切换、消息加载/缓存、会话列表刷新等 */
export function useSessionHistoryState({
  onRecoveredModelId,
}: UseSessionHistoryStateOptions): UseSessionHistoryStateResult {
  /* 当前会话 ID */
  const [currentSessionId, setCurrentSessionIdState] = useState<string | null>(null);
  /* 当前会话的消息列表 */
  const [messages, setMessagesState] = useState<Message[]>([]);
  /* 所有会话列表 */
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  /* 【核心】会话消息缓存：用 useRef 存储各会话的消息，避免切换会话时重复请求后端 */
  /* useRef 与 useState 的区别：修改 useRef 不会触发组件重新渲染，适合存储不需要立即反映到界面上的数据 */
  /* 结构：{ "session-1": [消息1, 消息2], "session-2": [消息3] } */
  const sessionMessagesRef = useRef<Record<string, Message[]>>({});

  /* 将消息缓存到指定会话 */
  const cacheSessionMessages = (sessionId: string, nextMessages: Message[]) => {
    sessionMessagesRef.current = {
      ...sessionMessagesRef.current,
      [sessionId]: nextMessages,
    };
  };

  /* 【核心】为持久化的消息恢复旅行方案产物（Artifact） */
  /* 应用场景：从后端加载历史消息时，最新的 AI 回复可能关联了一个旅行方案产物 */
  /* 但消息数据中可能没有包含产物信息，需要单独从后端获取并注入到消息中 */
  /* 例如：用户之前生成了"东京3日游方案"，切换回这个会话时，需要恢复方案数据以便操作 */
  const hydratePersistedArtifact = async (sessionId: string, messages: Message[]): Promise<Message[]> => {
    /* 找到最新的 AI 助手消息的索引 */
    const latestAssistantIndex = findLatestAssistantMessageIndex(messages);
    /* 如果没有 AI 消息，直接返回 */
    if (latestAssistantIndex < 0) return messages;
    /* 如果消息中已经有产物数据，不需要再获取 */
    if (messages[latestAssistantIndex]?.diagnostics?.artifact) return messages;

    try {
      /* 从后端获取最新的旅行方案产物 */
      const latestArtifact = await artifactClient.getLatestArtifact(sessionId);
      /* 将产物数据注入到消息中 */
      return hydrateMessagesWithLatestArtifact(messages, latestArtifact);
    } catch (error) {
      logger.warn('恢复持久化 artifact 失败:', error);
      return messages;
    }
  };

  /* 为消息附加会话 ID */
  /* 应用场景：从后端加载的消息可能没有 sessionId 字段，需要手动补充 */
  const attachSessionId = (sessionId: string, nextMessages: Message[]): Message[] =>
    nextMessages.map((message) => ({
      ...message,
      diagnostics: message.diagnostics
        ? {
            ...message.diagnostics,
            sessionId: message.diagnostics.sessionId || sessionId,
          }
        : undefined,
    }));

  /* 【核心】加载指定会话的消息 */
  /* 优先从缓存读取，缓存没有则从后端请求 */
  const loadSessionMessages = async (sessionId: string): Promise<Message[]> => {
    /* 如果缓存中有该会话的消息，直接返回 */
    if (hasOwnSessionMessages(sessionMessagesRef.current, sessionId)) {
      return sessionMessagesRef.current[sessionId];
    }

    /* 从后端获取消息 */
    const data = await sessionClient.getSessionMessages(sessionId);
    /* 规范化消息数据并附加会话 ID */
    const normalizedMessages = attachSessionId(sessionId, normalizePersistedMessages(data.messages));
    /* 恢复旅行方案产物数据 */
    const hydratedMessages = await hydratePersistedArtifact(sessionId, normalizedMessages);
    /* 缓存消息 */
    cacheSessionMessages(sessionId, hydratedMessages);
    return hydratedMessages;
  };

  /* 刷新会话列表 */
  const refreshSessions = async (includeEmpty: boolean = false) => {
    try {
      const data = await sessionClient.getSessions();
      /* 构建可见会话列表（过滤空会话等） */
      setSessions(buildVisibleSessions(data.sessions, { includeEmpty }));
    } catch (error) {
      logger.error('加载会话失败:', error);
    }
  };

  /* 添加一条消息到当前会话 */
  const addMessage = (message: Message) => {
    setMessagesState((previous) => {
      /* 创建新数组（不可变更新：不直接修改原数组，而是创建副本） */
      const nextMessages = [...previous, message];
      /* 如果有当前会话，同步更新缓存 */
      if (currentSessionId) cacheSessionMessages(currentSessionId, nextMessages);
      return nextMessages;
    });
  };

  /* 清空当前会话的消息 */
  const clearMessages = () => {
    setMessagesState([]);
    if (currentSessionId) cacheSessionMessages(currentSessionId, []);
  };

  /* 替换当前会话的整个消息列表 */
  const setMessages = (nextMessages: Message[]) => {
    setMessagesState(nextMessages);
    if (currentSessionId) cacheSessionMessages(currentSessionId, nextMessages);
  };

  /* 【核心】切换会话 —— 保存当前会话消息，加载目标会话消息 */
  /* 应用场景：用户在侧边栏点击另一个会话，需要切换到那个会话的消息 */
  /* 例如：从"东京旅行"切换到"巴黎旅行"，先缓存东京的消息，再加载巴黎的消息 */
  const switchSession = async (id: string | null) => {
    /* 先缓存当前会话的消息（避免丢失） */
    if (currentSessionId) {
      cacheSessionMessages(currentSessionId, messages);
    }

    /* 更新当前会话 ID */
    setCurrentSessionIdState(id);
    /* 如果切换到空会话（新建会话），清空消息 */
    if (!id) {
      setMessagesState([]);
      return;
    }

    try {
      /* 加载目标会话的消息 */
      const nextMessages = await loadSessionMessages(id);
      setMessagesState(nextMessages);
    } catch (error) {
      logger.error('加载会话消息失败:', error);
      /* 加载失败时重置状态 */
      setCurrentSessionIdState(null);
      setMessagesState([]);
      if (typeof window !== 'undefined') {
        window.localStorage.removeItem(SESSION_STORAGE_KEY);
      }
      return;
    }

    /* 尝试恢复该会话使用的模型 ID */
    try {
      const data = await modelClient.getSessionModel(id);
      /* 如果后端返回了有效的模型 ID（且不是默认值），通知上层更新模型选择 */
      if (data.success && data.model_id && data.model_id !== 'default') {
        onRecoveredModelId(data.model_id);
      }
    } catch (error) {
      logger.error('获取会话模型失败:', error);
    }
  };

  /* 【核心】组件挂载时（首次渲染后）刷新会话列表 */
  /* useEffect 的第二个参数是空数组 []，表示只在组件首次挂载时执行一次 */
  /* void 表示不等待 Promise 完成（即"触发后不管"） */
  useEffect(() => {
    void refreshSessions();
  }, []);

  /* 组件挂载时，从 localStorage 恢复上次的会话 */
  useEffect(() => {
    /* typeof window === 'undefined' 检查是否在浏览器环境（SSR 时 window 不存在） */
    if (typeof window === 'undefined') return;
    /* 读取存储的会话 ID */
    const storedSessionId = readStoredSessionId(window.location.search, window.localStorage);
    if (!storedSessionId) return;
    /* 恢复到上次的会话 */
    void switchSession(storedSessionId);
  }, []);

  /* 当 currentSessionId 变化时，将其持久化到 localStorage */
  useEffect(() => {
    if (typeof window === 'undefined') return;
    persistStoredSessionId(window.localStorage, currentSessionId);
  }, [currentSessionId]);  /* 依赖项：只有 currentSessionId 变化时才执行 */

  return {
    currentSessionId,
    setCurrentSessionId: setCurrentSessionIdState,
    switchSession,
    refreshSessions,
    sessions,
    messages,
    addMessage,
    clearMessages,
    setMessages,
  };
}
