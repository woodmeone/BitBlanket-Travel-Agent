import type { RoutePreviewRequest, RoutePreviewResponse } from '@/types';
import { API_PREFIX, apiClient } from './core';

class MapClient {
  async getRoutePreview(payload: RoutePreviewRequest): Promise<RoutePreviewResponse> {
    const response = await apiClient.post(`${API_PREFIX}/map/route-preview`, payload);
    return response.data;
  }
}

export const mapClient = new MapClient();
