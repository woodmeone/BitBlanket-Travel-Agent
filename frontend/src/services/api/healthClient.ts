// healthClient.ts —— 健康检查 API 客户端
// 本文件负责与后端的健康检查接口通信，用于检测各个服务是否正常运行
// 包括：
// 1. 整体健康检查
// 2. LLM（大语言模型）服务健康检查
// 3. 工具服务健康检查
// 4. 工具意图服务健康检查
//
// 应用场景举例：
// 系统启动时或用户遇到问题时，前端调用这些接口检测后端服务状态，
// 在界面上显示"系统正常"或"部分服务不可用"的提示

import type { HealthResponse, LLMHealthResponse, ToolIntentsHealthResponse, ToolsHealthResponse } from '@/types';
import { API_PREFIX, apiClient } from './core';

// HealthClient 类 —— 健康检查的 API 客户端
class HealthClient {
  // checkHealth —— 检查后端整体健康状态
  // 应用场景：页面加载时检测系统是否可用
  async checkHealth(): Promise<HealthResponse> {
    const response = await apiClient.get(`${API_PREFIX}/health`);
    return response.data;
  }

  // checkLLMHealth —— 检查大语言模型服务是否正常
  // 应用场景：用户发送消息前，确认 AI 模型服务可用
  async checkLLMHealth(): Promise<LLMHealthResponse> {
    const response = await apiClient.get(`${API_PREFIX}/health/llm`);
    return response.data;
  }

  // checkToolsHealth —— 检查工具服务是否正常
  // 应用场景：确认酒店搜索、景点推荐等工具服务可用
  async checkToolsHealth(): Promise<ToolsHealthResponse> {
    const response = await apiClient.get(`${API_PREFIX}/health/tools`);
    return response.data;
  }

  // checkToolsIntentsHealth —— 检查工具意图识别服务是否正常
  // 应用场景：确认 AI 能正确识别用户意图并调用对应工具
  async checkToolsIntentsHealth(): Promise<ToolIntentsHealthResponse> {
    const response = await apiClient.get(`${API_PREFIX}/health/tools/intents`);
    return response.data;
  }
}

// 导出 HealthClient 的单例实例
export const healthClient = new HealthClient();
