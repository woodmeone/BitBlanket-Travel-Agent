// modelClient.ts —— 模型管理 API 客户端
// 本文件负责与后端的 AI 模型管理接口通信，包括：
// 1. 获取可用的 AI 模型列表
// 2. 为指定会话设置使用的 AI 模型
// 3. 获取指定会话当前使用的 AI 模型
//
// 应用场景举例：
// 用户在设置面板中切换 AI 模型（如从 GPT-4 切换到 Claude），
// 或者在不同会话中使用不同的模型

import type { AvailableModelsResponse, GetSessionModelResponse, SetModelRequest, SetModelResponse } from '@/types';
import { API_PREFIX, apiClient, toAxiosRequestConfig, type APIRequestOptions } from './core';

// ModelClient 类 —— 模型管理的 API 客户端
class ModelClient {
  // getAvailableModels —— 获取所有可用的 AI 模型列表
  // 应用场景：用户打开模型选择器，展示所有可选的 AI 模型
  // options?: APIRequestOptions 可选的请求配置，如超时时间、取消信号
  // toAxiosRequestConfig(options)：将自定义选项转换为 axios 配置格式
  async getAvailableModels(options?: APIRequestOptions): Promise<AvailableModelsResponse> {
    const response = await apiClient.get(`${API_PREFIX}/models`, toAxiosRequestConfig(options));
    return response.data;
  }

  // setSessionModel —— 为指定会话设置使用的 AI 模型
  // 应用场景：用户在某个对话中切换模型，从"GPT-4"切换到"Claude"
  // sessionId：会话ID，modelId：模型ID
  // as SetModelRequest：TypeScript 类型断言，告诉编译器请求体的结构符合 SetModelRequest 类型
  async setSessionModel(sessionId: string, modelId: string): Promise<SetModelResponse> {
    const response = await apiClient.put(`${API_PREFIX}/session/${sessionId}/model`, {
      model_id: modelId,
    } as SetModelRequest);
    return response.data;
  }

  // getSessionModel —— 获取指定会话当前使用的 AI 模型
  // 应用场景：用户打开某个历史会话，界面上需要显示该会话正在使用的模型名称
  async getSessionModel(sessionId: string): Promise<GetSessionModelResponse> {
    const response = await apiClient.get(`${API_PREFIX}/session/${sessionId}/model`);
    return response.data;
  }
}

// 导出 ModelClient 的单例实例
export const modelClient = new ModelClient();
