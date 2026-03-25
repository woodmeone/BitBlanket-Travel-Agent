import type { AvailableModelsResponse, GetSessionModelResponse, SetModelRequest, SetModelResponse } from '@/types';
import { API_PREFIX, apiClient, toAxiosRequestConfig, type APIRequestOptions } from './core';

class ModelClient {
  async getAvailableModels(options?: APIRequestOptions): Promise<AvailableModelsResponse> {
    const response = await apiClient.get(`${API_PREFIX}/models`, toAxiosRequestConfig(options));
    return response.data;
  }

  async setSessionModel(sessionId: string, modelId: string): Promise<SetModelResponse> {
    const response = await apiClient.put(`${API_PREFIX}/session/${sessionId}/model`, {
      model_id: modelId,
    } as SetModelRequest);
    return response.data;
  }

  async getSessionModel(sessionId: string): Promise<GetSessionModelResponse> {
    const response = await apiClient.get(`${API_PREFIX}/session/${sessionId}/model`);
    return response.data;
  }
}

export const modelClient = new ModelClient();
