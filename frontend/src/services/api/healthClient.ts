import type { HealthResponse, LLMHealthResponse, ToolIntentsHealthResponse, ToolsHealthResponse } from '@/types';
import { API_PREFIX, apiClient } from './core';

class HealthClient {
  async checkHealth(): Promise<HealthResponse> {
    const response = await apiClient.get(`${API_PREFIX}/health`);
    return response.data;
  }

  async checkLLMHealth(): Promise<LLMHealthResponse> {
    const response = await apiClient.get(`${API_PREFIX}/health/llm`);
    return response.data;
  }

  async checkToolsHealth(): Promise<ToolsHealthResponse> {
    const response = await apiClient.get(`${API_PREFIX}/health/tools`);
    return response.data;
  }

  async checkToolsIntentsHealth(): Promise<ToolIntentsHealthResponse> {
    const response = await apiClient.get(`${API_PREFIX}/health/tools/intents`);
    return response.data;
  }
}

export const healthClient = new HealthClient();
