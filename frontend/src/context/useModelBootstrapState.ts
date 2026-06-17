/* 【核心】模型引导状态管理钩子 —— 管理 AI 模型的加载、选择和切换 */
/* 应用场景：应用启动时需要从后端获取可用的 AI 模型列表，用户可以切换不同的模型 */
/* 例如：后端提供了 MiniMax M2.5、GPT-4 等模型，用户在界面上选择不同的模型来生成回答 */
/* "引导"（Bootstrap）一词来自"启动引导"的概念，指应用启动时自动加载模型列表 */
'use client';

/* useEffect：副作用钩子，用于在组件渲染后执行异步操作 */
/* useRef：持久化引用，修改不触发渲染 */
/* useState：创建可变状态 */
import { useEffect, useRef, useState } from 'react';
/* 导入模型 API 客户端，用于与后端通信 */
import { modelClient } from '@/services/api';
/* 导入模型信息类型 */
import type { ModelInfo } from '@/types';
/* 导入日志工具 */
import { logger } from '@/utils/logger';

/* 【核心】默认模型列表 —— 当后端不可用时的兜底配置 */
/* 应用场景：如果后端服务还没启动或请求超时，前端仍然可以正常显示模型选项 */
/* 这样设计是为了"优雅降级"：即使后端出问题，用户界面也不会崩溃 */
export const DEFAULT_MODELS: ModelInfo[] = [
  {
    model_id: 'minimax-m2-5',    // 模型唯一标识
    name: 'MiniMax M2.5',         // 模型显示名称
    provider: 'anthropic',        // 模型提供商
    model: 'MiniMax-M2.5',       // 模型实际名称
  },
];

/* 【核心】解析引导时的模型 ID —— 确定应用启动后默认使用哪个模型 */
/* 优先使用用户之前选择的模型（preferredModelId），如果该模型不在可用列表中则使用第一个可用模型 */
/* 应用场景：用户上次选择了 GPT-4，但这次后端只提供了 MiniMax M2.5，则自动切换到 MiniMax M2.5 */
export function resolveBootstrapModelId(models: ModelInfo[], preferredModelId: string | null): string | null {
  /* 没有可用模型，返回 null */
  if (models.length === 0) return null;
  /* 如果用户偏好的模型在可用列表中，使用它 */
  if (preferredModelId && models.some((model) => model.model_id === preferredModelId)) {
    return preferredModelId;
  }
  /* 否则使用列表中的第一个模型 */
  return models[0].model_id;
}

/* 钩子选项接口 */
interface UseModelBootstrapStateOptions {
  currentSessionId: string | null;  // 当前会话 ID（切换模型时需要通知后端）
}

/* 钩子返回值接口 */
interface UseModelBootstrapStateResult {
  availableModels: ModelInfo[];                          // 可用模型列表
  currentModelId: string | null;                         // 当前选中的模型 ID
  loadingModels: boolean;                                // 是否正在加载模型列表
  recoverModelId: (modelId: string) => void;             // 恢复模型 ID（从会话中恢复时使用）
  setCurrentModelId: (modelId: string) => Promise<void>; // 切换模型（同时通知后端）
}

/* 【核心】模型引导状态管理钩子 */
/* 这个钩子负责：1. 应用启动时从后端加载可用模型列表 */
/*             2. 管理当前选中的模型 */
/*             3. 切换模型时同步到后端 */
export function useModelBootstrapState({
  currentSessionId,
}: UseModelBootstrapStateOptions): UseModelBootstrapStateResult {
  /* 可用模型列表，默认使用 DEFAULT_MODELS */
  const [availableModels, setAvailableModels] = useState<ModelInfo[]>(DEFAULT_MODELS);
  /* 当前选中的模型 ID，默认使用默认模型的第一个 */
  const [currentModelId, setCurrentModelIdState] = useState<string | null>(DEFAULT_MODELS[0]?.model_id ?? null);
  /* 是否正在加载模型列表 */
  const [loadingModels, setLoadingModels] = useState(false);
  /* 用 useRef 保存当前模型 ID 的最新值，避免在异步回调中读到过期的值 */
  /* 应用场景：在 useEffect 中发起异步请求时，如果组件状态已更新，闭包中的值可能是旧的 */
  /* useRef 可以确保始终读取到最新值 */
  const currentModelIdRef = useRef<string | null>(DEFAULT_MODELS[0]?.model_id ?? null);

  /* 更新当前模型 ID 的辅助函数（同时更新 state 和 ref） */
  const updateCurrentModelId = (modelId: string | null) => {
    currentModelIdRef.current = modelId;  // 更新 ref（不触发渲染）
    setCurrentModelIdState(modelId);       // 更新 state（触发渲染）
  };

  /* 【核心】应用启动时从后端加载可用模型列表 */
  /* useEffect 的第二个参数是空数组 []，表示只在组件首次挂载时执行一次 */
  useEffect(() => {
    /* active 标志位，用于在组件卸载时取消异步操作 */
    let active = true;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    /* AbortController 是浏览器提供的 API，用于取消正在进行的网络请求 */
    const controller = new AbortController();

    const loadModels = async () => {
      /* 只有当当前模型列表为空时才显示加载状态 */
      const shouldShowLoader = availableModels.length === 0;
      if (shouldShowLoader && active) {
        setLoadingModels(true);
      }

      /* 设置3秒超时，超时后自动取消请求 */
      timeoutId = setTimeout(() => controller.abort(), 3000);
      try {
        /* 从后端获取可用模型列表 */
        const data = await modelClient.getAvailableModels({ signal: controller.signal, timeoutMs: 3000 });
        /* 检查返回数据是否有效 */
        if (!active || !data.success || !Array.isArray(data.models) || data.models.length === 0) return;

        /* 更新可用模型列表 */
        setAvailableModels(data.models);
        /* 根据用户偏好和可用列表确定默认模型 */
        updateCurrentModelId(resolveBootstrapModelId(data.models, currentModelIdRef.current));
      } catch {
        /* 请求失败时静默处理，保留默认模型列表 */
      } finally {
        if (timeoutId) {
          clearTimeout(timeoutId);
        }
        if (active) {
          setLoadingModels(false);
        }
      }
    };

    /* 【核心】延迟1秒后再加载模型列表 */
    /* 这样做是为了"让壳先渲染"：先让页面框架渲染出来，再去加载模型数据 */
    /* 避免模型加载阻塞页面首次渲染，提升用户体验 */
    const timer = setTimeout(loadModels, 1000);
    /* 清理函数：组件卸载时取消所有异步操作 */
    return () => {
      active = false;
      clearTimeout(timer);
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      controller.abort();
    };
  }, []);

  /* 恢复模型 ID —— 从会话中恢复模型选择时使用 */
  /* 应用场景：用户切换回之前的会话，该会话使用的是 GPT-4，需要恢复模型选择 */
  const recoverModelId = (modelId: string) => {
    updateCurrentModelId(modelId);
  };

  /* 【核心】切换当前模型 —— 同时更新前端状态和后端会话配置 */
  /* 应用场景：用户在界面上选择不同的 AI 模型，需要立即生效并同步到后端 */
  const setCurrentModelId = async (modelId: string) => {
    /* 先更新前端状态（立即生效） */
    updateCurrentModelId(modelId);
    /* 如果没有当前会话，不需要通知后端 */
    if (!currentSessionId) return;

    try {
      /* 通知后端更新该会话使用的模型 */
      await modelClient.setSessionModel(currentSessionId, modelId);
    } catch (error) {
      logger.error('设置会话模型失败:', error);
      /* 将错误向上抛出，让调用方决定如何处理 */
      throw error;
    }
  };

  return {
    availableModels,
    currentModelId,
    loadingModels,
    recoverModelId,
    setCurrentModelId,
  };
}
