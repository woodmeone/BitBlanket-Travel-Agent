import type { CityDetail, CityListResponse, RegionListResponse, TagListResponse } from '@/types';
import { API_PREFIX, apiClient } from './core';

class CityClient {
  async getRegions(): Promise<RegionListResponse> {
    const response = await apiClient.get(`${API_PREFIX}/regions`);
    return response.data;
  }

  async getTags(): Promise<TagListResponse> {
    const response = await apiClient.get(`${API_PREFIX}/tags`);
    return response.data;
  }

  async getCities(params?: { region?: string; tags?: string[] }): Promise<CityListResponse> {
    const response = await apiClient.get(`${API_PREFIX}/cities`, {
      params: {
        region: params?.region || undefined,
        tags: params?.tags && params.tags.length > 0 ? params.tags.join(',') : undefined,
      },
    });
    return response.data;
  }

  async getCityDetail(cityId: string): Promise<CityDetail> {
    const response = await apiClient.get(`${API_PREFIX}/cities/${cityId}`);
    return response.data;
  }
}

export const cityClient = new CityClient();
