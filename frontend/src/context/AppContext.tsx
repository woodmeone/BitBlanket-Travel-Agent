'use client';

import React, { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { modelClient, sessionClient } from '@/services/api';
import type { AppConfig, ChatMode, Message, ModelInfo, SessionInfo } from '@/types';
import { logger } from '@/utils/logger';
import { normalizePersistedMessages } from '@/utils/sessionMessages';

const DEFAULT_MODELS: ModelInfo[] = [
  {
    model_id: 'minimax-m2-5',
    name: 'MiniMax M2.5',
    provider: 'anthropic',
    model: 'MiniMax-M2.5',
  },
];

const DEFAULT_API_BASE =
  (typeof window !== 'undefined' && window.ENV?.NEXT_PUBLIC_API_BASE) ||
  process.env.NEXT_PUBLIC_API_BASE ||
  'http://localhost:38000';
const SESSION_STORAGE_KEY = 'moyuan-current-session-id';

function hasOwnSessionMessages(cache: Record<string, Message[]>, sessionId: string): boolean {
  return Object.prototype.hasOwnProperty.call(cache, sessionId);
}

interface AppState {
  config: AppConfig;
  setConfig: (config: AppConfig) => void;

  availableModels: ModelInfo[];
  currentModelId: string | null;
  setCurrentModelId: (modelId: string) => void;
  loadingModels: boolean;

  chatMode: ChatMode;
  setChatMode: (mode: ChatMode) => void;

  currentSessionId: string | null;
  setCurrentSessionId: (id: string | null) => void;
  switchSession: (id: string | null) => Promise<void>;
  refreshSessions: (includeEmpty?: boolean) => Promise<void>;
  sessions: SessionInfo[];

  messages: Message[];
  addMessage: (message: Message) => void;
  clearMessages: () => void;
  setMessages: (messages: Message[]) => void;

  isStreaming: boolean;
  setIsStreaming: (streaming: boolean) => void;
  stopStreaming: boolean;
  setStopStreaming: (stop: boolean) => void;
}

const AppContext = createContext<AppState | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [config, setConfig] = useState<AppConfig>({ apiBase: DEFAULT_API_BASE });
  const [availableModels, setAvailableModels] = useState<ModelInfo[]>(DEFAULT_MODELS);
  const [currentModelId, setCurrentModelIdState] = useState<string | null>('minimax-m2-5');
  const [loadingModels] = useState(false);

  const [currentSessionId, setCurrentSessionIdState] = useState<string | null>(null);
  const [messages, setMessagesState] = useState<Message[]>([]);
  // Local per-session cache avoids extra round-trips when users switch tabs rapidly.
  const [sessionMessages, setSessionMessages] = useState<Record<string, Message[]>>({});
  const sessionMessagesRef = useRef<Record<string, Message[]>>({});
  const [isStreaming, setIsStreaming] = useState(false);
  const [stopStreaming, setStopStreaming] = useState(false);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [chatMode, setChatModeState] = useState<ChatMode>('react');

  const cacheSessionMessages = (sessionId: string, nextMessages: Message[]) => {
    setSessionMessages((cache) => {
      const nextCache = { ...cache, [sessionId]: nextMessages };
      sessionMessagesRef.current = nextCache;
      return nextCache;
    });
  };

  const loadSessionMessages = async (sessionId: string): Promise<Message[]> => {
    if (hasOwnSessionMessages(sessionMessagesRef.current, sessionId)) {
      return sessionMessagesRef.current[sessionId];
    }

    const data = await sessionClient.getSessionMessages(sessionId);
    const normalizedMessages = normalizePersistedMessages(data.messages);
    cacheSessionMessages(sessionId, normalizedMessages);
    return normalizedMessages;
  };

  const loadSessions = async () => {
    try {
      const data = await sessionClient.getSessions();
      const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
      // Keep recent empty sessions visible for short-term navigation continuity.
      const activeSessions = data.sessions.filter(
        (session) => session.message_count > 0 || new Date(session.last_active) > oneHourAgo
      );
      setSessions(activeSessions);
    } catch (error) {
      logger.error('加载会话失败:', error);
    }
  };

  useEffect(() => {
    const loadModels = async () => {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000);
      try {
        // Keep model bootstrap isolated so shell rendering never depends on it.
        const data = await modelClient.getAvailableModels({ signal: controller.signal, timeoutMs: 3000 });
        if (!data.success || !Array.isArray(data.models) || data.models.length === 0) return;

        const modelExists = data.models.some((model: ModelInfo) => model.model_id === currentModelId);
        setAvailableModels(data.models);
        setCurrentModelIdState(modelExists ? currentModelId : data.models[0].model_id);
      } catch {
        // Keep default models silently.
      } finally {
        clearTimeout(timeoutId);
      }
    };

    const timer = setTimeout(loadModels, 1000);
    return () => clearTimeout(timer);
  }, [currentModelId]);

  useEffect(() => {
    loadSessions();
  }, []);

  const handleSetCurrentModelId = async (modelId: string) => {
    setCurrentModelIdState(modelId);
    if (!currentSessionId) return;
    try {
      await modelClient.setSessionModel(currentSessionId, modelId);
    } catch (error) {
      logger.error('设置会话模型失败:', error);
    }
  };

  const addMessage = (message: Message) => {
    setMessagesState((prev) => {
      const next = [...prev, message];
      if (currentSessionId) cacheSessionMessages(currentSessionId, next);
      return next;
    });
  };

  const clearMessages = () => {
    setMessagesState([]);
    if (currentSessionId) cacheSessionMessages(currentSessionId, []);
  };

  const setMessages = (newMessages: Message[]) => {
    setMessagesState(newMessages);
    if (currentSessionId) cacheSessionMessages(currentSessionId, newMessages);
  };

  const setCurrentSessionId = (id: string | null) => {
    setCurrentSessionIdState(id);
  };

  const refreshSessions = async (includeEmpty: boolean = false) => {
    try {
      const data = await sessionClient.getSessions();
      const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
      const uniqueSessionsMap = new Map(data.sessions.map((session) => [session.session_id, session]));
      const uniqueSessions = Array.from(uniqueSessionsMap.values());

      if (includeEmpty) {
        setSessions(uniqueSessions);
        return;
      }

      const activeSessions = uniqueSessions.filter(
        (session) => session.message_count > 0 || new Date(session.last_active) > oneHourAgo
      );
      setSessions(activeSessions);
    } catch {
      // Ignore refresh failures.
    }
  };

  const switchSession = async (id: string | null) => {
    // Persist current draft history into local cache before switching session scope.
    if (currentSessionId) cacheSessionMessages(currentSessionId, messages);

    setCurrentSessionIdState(id);
    if (!id) {
      setMessagesState([]);
      return;
    }

    try {
      const nextMessages = await loadSessionMessages(id);
      setMessagesState(nextMessages);
    } catch (error) {
      logger.error('加载会话消息失败:', error);
      setCurrentSessionIdState(null);
      setMessagesState([]);
      if (typeof window !== 'undefined') window.localStorage.removeItem(SESSION_STORAGE_KEY);
      return;
    }

    try {
      const data = await modelClient.getSessionModel(id);
      if (data.success && data.model_id && data.model_id !== 'default') {
        setCurrentModelIdState(data.model_id);
      }
    } catch (error) {
      logger.error('获取会话模型失败:', error);
    }
  };

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (window.location.search.includes('share=')) return;
    const storedSessionId = window.localStorage.getItem(SESSION_STORAGE_KEY);
    if (!storedSessionId) return;
    void switchSession(storedSessionId);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (currentSessionId) {
      window.localStorage.setItem(SESSION_STORAGE_KEY, currentSessionId);
      return;
    }
    window.localStorage.removeItem(SESSION_STORAGE_KEY);
  }, [currentSessionId]);

  const value: AppState = {
    config,
    setConfig,
    availableModels,
    currentModelId,
    setCurrentModelId: handleSetCurrentModelId,
    loadingModels,
    chatMode,
    setChatMode: setChatModeState,
    currentSessionId,
    setCurrentSessionId,
    switchSession,
    refreshSessions,
    sessions,
    messages,
    addMessage,
    clearMessages,
    setMessages,
    isStreaming,
    setIsStreaming,
    stopStreaming,
    setStopStreaming,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

export const useAppContext = (): AppState => {
  const context = useContext(AppContext);
  if (!context) throw new Error('useAppContext must be used within AppProvider');
  return context;
};
