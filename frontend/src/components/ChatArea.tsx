'use client';

import React from 'react';
import { Tabs } from 'antd';
import CityExplorer from '@/components/CityExplorer';
import SystemStatusPanel from '@/components/SystemStatusPanel';
import ChatComposer from '@/components/chat-area/ChatComposer';
import ChatConversationView from '@/components/chat-area/ChatConversationView';
import { useChatRuntime } from '@/components/chat-area/useChatRuntime';

const ChatArea: React.FC = () => {
  const runtime = useChatRuntime();

  return (
    <div
      className="chat-input-area"
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        padding: '24px',
        background: 'linear-gradient(180deg, #fafbfc 0%, #f3f4f6 100%)',
      }}
    >
      <div style={{ marginBottom: 10 }}>
        <Tabs
          activeKey={runtime.activeView}
          onChange={(value) => runtime.setActiveView(value as 'chat' | 'city' | 'status')}
          items={[
            { key: 'chat', label: '对话体验' },
            { key: 'city', label: '城市探索' },
            { key: 'status', label: '系统状态' },
          ]}
        />
      </div>

      <div style={{ flex: 1, overflow: 'auto', marginBottom: '16px' }}>
        {runtime.activeView === 'chat' && (
          <ChatConversationView
            messages={runtime.messages}
            messagesEndRef={runtime.messagesEndRef}
            streamingMessage={runtime.streamingMessage}
            streamingReasoning={runtime.streamingReasoning}
            waitingForResponse={runtime.waitingForResponse}
            isThinking={runtime.isThinking}
            isStreaming={runtime.isStreaming}
            currentTool={runtime.currentTool}
            reasoningExpanded={runtime.reasoningExpanded}
            error={runtime.error}
            metadata={runtime.metadata}
            stageState={runtime.stageState}
            stageHistory={runtime.stageHistory}
            runtimeLogs={runtime.runtimeLogs}
            planPreview={runtime.planPreview}
            artifactState={runtime.artifactState}
            activeSubagent={runtime.activeSubagent}
            subagentEvents={runtime.subagentEvents}
            onContinuePrompt={runtime.handleContinueRefine}
            onPickPrompt={runtime.handlePickQuickStartPrompt}
            onToggleReasoning={runtime.toggleReasoning}
          />
        )}

        {runtime.activeView === 'city' && <CityExplorer onUsePrompt={runtime.handleUsePromptFromExplorer} />}
        {runtime.activeView === 'status' && <SystemStatusPanel />}
      </div>

      {runtime.activeView === 'chat' && (
        <ChatComposer
          chatMode={runtime.chatMode}
          compareModeEnabled={runtime.compareModeEnabled}
          comparePlanCount={runtime.comparePlanCount}
          budgetUpperLimit={runtime.budgetUpperLimit}
          inputValue={runtime.inputValue}
          isStreaming={runtime.isStreaming}
          selectedConstraintCount={runtime.selectedConstraintCount}
          selectedConstraints={runtime.selectedConstraints}
          onBudgetUpperLimitChange={runtime.setBudgetUpperLimit}
          onChatModeChange={runtime.setChatMode}
          onCompareModeChange={runtime.setCompareModeEnabled}
          onComparePlanCountChange={runtime.setComparePlanCount}
          onInputChange={runtime.setInputValue}
          onSend={runtime.handleSend}
          onSelectedConstraintsChange={runtime.setSelectedConstraints}
          onStop={runtime.handleStop}
        />
      )}
    </div>
  );
};

export default ChatArea;
