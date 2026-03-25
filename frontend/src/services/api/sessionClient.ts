import type { SessionInfo, SessionMessagesResponse } from '@/types';
import { API_PREFIX, apiClient } from './core';

class SessionClient {
  async createSession(): Promise<{ session_id: string }> {
    const response = await apiClient.post(`${API_PREFIX}/session/new`);
    return response.data;
  }

  async getSessions(): Promise<{ sessions: SessionInfo[] }> {
    const response = await apiClient.get(`${API_PREFIX}/sessions`);
    return response.data;
  }

  async getSessionMessages(sessionId: string): Promise<SessionMessagesResponse> {
    const response = await apiClient.get(`${API_PREFIX}/session/${sessionId}/messages`);
    return response.data;
  }

  async deleteSession(sessionId: string): Promise<{ success: boolean }> {
    const response = await apiClient.delete(`${API_PREFIX}/session/${sessionId}`);
    return response.data;
  }

  async updateSessionName(sessionId: string, name: string): Promise<{ success: boolean; message?: string }> {
    const response = await apiClient.put(`${API_PREFIX}/session/${sessionId}/name`, { name });
    return response.data;
  }
}

export const sessionClient = new SessionClient();
