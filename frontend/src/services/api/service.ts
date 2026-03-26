import { artifactClient } from './artifactClient';
import { chatClient } from './chatClient';
import { cityClient } from './cityClient';
import { healthClient } from './healthClient';
import { mapClient } from './mapClient';
import { modelClient } from './modelClient';
import { sessionClient } from './sessionClient';
import { shareClient } from './shareClient';

export class APIService {
  getLatestArtifact = (sessionId: string) => artifactClient.getLatestArtifact(sessionId);
  getArtifactHistory = (sessionId: string, limit?: number) => artifactClient.getArtifactHistory(sessionId, limit);
  checkHealth = () => healthClient.checkHealth();
  checkLLMHealth = () => healthClient.checkLLMHealth();
  checkToolsHealth = () => healthClient.checkToolsHealth();
  checkToolsIntentsHealth = () => healthClient.checkToolsIntentsHealth();

  createSession = () => sessionClient.createSession();
  getSessions = () => sessionClient.getSessions();
  getSessionMessages = (sessionId: string) => sessionClient.getSessionMessages(sessionId);
  deleteSession = (sessionId: string) => sessionClient.deleteSession(sessionId);
  updateSessionName = (sessionId: string, name: string) => sessionClient.updateSessionName(sessionId, name);

  getAvailableModels = (options?: Parameters<typeof modelClient.getAvailableModels>[0]) =>
    modelClient.getAvailableModels(options);
  setSessionModel = (sessionId: string, modelId: string) => modelClient.setSessionModel(sessionId, modelId);
  getSessionModel = (sessionId: string) => modelClient.getSessionModel(sessionId);

  getRegions = () => cityClient.getRegions();
  getTags = () => cityClient.getTags();
  getCities = (params?: Parameters<typeof cityClient.getCities>[0]) => cityClient.getCities(params);
  getCityDetail = (cityId: string) => cityClient.getCityDetail(cityId);

  getRoutePreview = (payload: Parameters<typeof mapClient.getRoutePreview>[0]) => mapClient.getRoutePreview(payload);
  createShareLink = (payload: Parameters<typeof shareClient.createShareLink>[0]) => shareClient.createShareLink(payload);
  getShareDetail = (shareId: string) => shareClient.getShareDetail(shareId);

  clearChat = (sessionId: string) => chatClient.clearChat(sessionId);
  fetchStreamChat = (
    request: Parameters<typeof chatClient.fetchStreamChat>[0],
    callbacks: Parameters<typeof chatClient.fetchStreamChat>[1]
  ) => chatClient.fetchStreamChat(request, callbacks);
  cancelAllRequests = () => chatClient.cancelAllRequests();
  getConnectionStatus = () => chatClient.getConnectionStatus();
}

export const apiService = new APIService();
