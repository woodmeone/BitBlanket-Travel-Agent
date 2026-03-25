import type { ShareCreateRequest, ShareCreateResponse, ShareDetailResponse } from '@/types';
import { API_PREFIX, apiClient } from './core';

class ShareClient {
  async createShareLink(payload: ShareCreateRequest): Promise<ShareCreateResponse> {
    const response = await apiClient.post(`${API_PREFIX}/share-links`, payload);
    return response.data;
  }

  async getShareDetail(shareId: string): Promise<ShareDetailResponse> {
    const response = await apiClient.get(`${API_PREFIX}/share-links/${encodeURIComponent(shareId)}`);
    return response.data;
  }
}

export const shareClient = new ShareClient();
