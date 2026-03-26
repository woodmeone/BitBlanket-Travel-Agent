import type { LatestArtifactResponse } from '@/types';
import { API_PREFIX, apiClient } from './core';

class ArtifactClient {
  async getLatestArtifact(sessionId: string): Promise<LatestArtifactResponse> {
    const response = await apiClient.get(`${API_PREFIX}/artifacts/${sessionId}/latest`);
    return response.data;
  }
}

export const artifactClient = new ArtifactClient();
