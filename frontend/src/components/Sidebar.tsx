import React, { useState } from 'react';
import { Button, Input, Space, Card, Modal, Select, Spin, App, Flex, Badge, Tag } from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  EditOutlined,
  RobotOutlined,
  MessageOutlined,
  ClearOutlined,
} from '@ant-design/icons';
import { useAppContext } from '../context/AppContext';
import { apiService } from '../services/api';
import { logger } from '../utils/logger';
import { SessionInfo } from '../types';

const { Option } = Select;

const Sidebar: React.FC = () => {
  const { message } = App.useApp();
  const {
    currentSessionId,
    switchSession,
    availableModels,
    currentModelId,
    setCurrentModelId,
    loadingModels,
    sessions,
    refreshSessions,
    clearMessages,
  } = useAppContext();

  const [loading, setLoading] = useState(false);
  const [switchingModel, setSwitchingModel] = useState(false);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');

  // 创建新会话
  const handleCreateSession = async () => {
    try {
      setLoading(true);
      const data = await apiService.createSession();
      switchSession(data.session_id);
      await refreshSessions();
      message.success('新会话已创建');
    } catch (error) {
      message.error('创建会话失败');
    } finally {
      setLoading(false);
    }
  };

  // 删除会话
  const handleDeleteSession = async (sessionId: string) => {
    try {
      await apiService.deleteSession(sessionId);
      if (sessionId === currentSessionId) {
        switchSession(null);
      }
      await refreshSessions();
      message.success('会话已删除');
    } catch (error) {
      message.error('删除失败');
    }
  };

  // 切换会话
  const handleSwitchSession = (sessionId: string) => {
    switchSession(sessionId);
  };

  // 开始编辑会话名称
  const handleStartEdit = (session: SessionInfo) => {
    setEditingSessionId(session.session_id);
    setEditingName(session.name || `会话 ${session.session_id.slice(0, 8)}`);
  };

  // 取消编辑
  const handleCancelEdit = () => {
    setEditingSessionId(null);
    setEditingName('');
  };

  // 保存会话名称
  const handleSaveEdit = async () => {
    if (!editingSessionId || !editingName.trim()) return;

    try {
      await apiService.updateSessionName(editingSessionId, editingName.trim());
      await refreshSessions();
      setEditingSessionId(null);
      setEditingName('');
      message.success('会话名称已更新');
    } catch (error) {
      message.error('更新失败');
    }
  };

  // 清空对话
  const handleClearChat = async () => {
    if (!currentSessionId) {
      message.warning('请先创建会话');
      return;
    }

    try {
      await apiService.clearChat(currentSessionId);
      clearMessages();
      message.success('对话已清空');
    } catch (error) {
      message.error('清空失败');
    }
  };

  // 模型切换
  const handleModelChange = async (modelId: string) => {
    try {
      setSwitchingModel(true);
      await setCurrentModelId(modelId);
      const model = availableModels.find(m => m.model_id === modelId);
      message.success(`已切换到 ${model?.name || modelId}`);
    } catch (error) {
      message.error('模型切换失败，请重试');
      logger.error('模型切换错误:', error);
    } finally {
      setSwitchingModel(false);
    }
  };

  return (
    <div style={{
      padding: '20px',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      gap: '16px'
    }}>
      {/* Logo/标题区域 */}
      <div style={{
        textAlign: 'center',
        padding: '8px 0 16px',
        borderBottom: '1px solid rgba(102, 126, 234, 0.1)'
      }}>
        <div style={{
          fontSize: '16px',
          fontWeight: 600,
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}>
          小帅旅游助手
        </div>
        <div style={{
          fontSize: '12px',
          color: '#999',
          marginTop: '4px'
        }}>
          智能AI旅游推荐
        </div>
      </div>

      {/* 模型选择 */}
      <Card
        size="small"
        style={{
          marginBottom: 0,
          background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%)',
        }}
        styles={{ body: { padding: '12px' } }}
      >
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '8px',
          fontSize: '13px',
          fontWeight: 500,
          color: '#667eea'
        }}>
          <RobotOutlined />
          <span>AI模型</span>
        </div>
        {loadingModels ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 0' }}>
            <Spin size="small" />
            <span style={{ fontSize: '13px', color: '#999' }}>加载中...</span>
          </div>
        ) : (
          <Select
            value={currentModelId}
            onChange={handleModelChange}
            style={{ width: '100%' }}
            placeholder="选择模型"
            suffixIcon={<RobotOutlined style={{ color: '#667eea' }} />}
            loading={switchingModel}
            disabled={availableModels.length === 0 || switchingModel}
          >
            {availableModels.map((model) => (
              <Option key={model.model_id} value={model.model_id}>
                {model.name}
              </Option>
            ))}
          </Select>
        )}
      </Card>

      {/* 会话管理 */}
      <Card
        size="small"
        styles={{ body: { padding: '12px' } }}
      >
        <Space orientation="vertical" style={{ width: '100%' }} size="small">
          <Button
            icon={<PlusOutlined />}
            onClick={handleCreateSession}
            loading={loading}
            style={{
              width: '100%',
              height: '40px',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              border: 'none',
              borderRadius: '10px',
              fontWeight: 500,
            }}
            type="primary"
          >
            新建会话
          </Button>
          <Button
            onClick={handleClearChat}
            icon={<ClearOutlined />}
            style={{
              width: '100%',
              height: '36px',
              borderRadius: '10px',
              borderColor: 'rgba(255, 107, 107, 0.5)',
              color: '#ff6b6b'
            }}
          >
            清空对话
          </Button>
        </Space>
      </Card>

      {/* 历史会话 */}
      <Card
        size="small"
        style={{
          flex: 1,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          marginBottom: 0
        }}
        styles={{
          body: {
            flex: 1,
            overflow: 'auto',
            padding: '8px'
          }
        }}
      >
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '13px',
          fontWeight: 500,
          color: '#667eea',
          marginBottom: '12px',
          paddingBottom: '8px',
          borderBottom: '1px solid rgba(102, 126, 234, 0.1)'
        }}>
          <MessageOutlined />
          <span>历史会话</span>
          <Tag style={{ marginLeft: 'auto', fontSize: '11px' }}>{sessions.length}</Tag>
        </div>
        <Flex vertical gap={4}>
          {sessions.map((session) => (
            <div
              key={session.session_id}
              className={`session-item ${session.session_id === currentSessionId ? 'active' : ''}`}
              style={{
                padding: '10px 12px',
                borderRadius: '10px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <div
                onClick={() => handleSwitchSession(session.session_id)}
                style={{ cursor: 'pointer', flex: 1, minWidth: 0 }}
              >
                <div style={{
                  fontWeight: session.session_id === currentSessionId ? '600' : 'normal',
                  fontSize: '13px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  color: session.session_id === currentSessionId ? '#667eea' : '#333'
                }}>
                  {session.session_id === currentSessionId && (
                    <CheckCircleOutlined style={{ color: '#667eea', fontSize: '12px' }} />
                  )}
                  <span style={{
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                  }}>
                    {session.name || `会话 ${session.session_id.slice(0, 8)}`}
                  </span>
                </div>
                <div style={{
                  fontSize: '11px',
                  color: '#999',
                  marginTop: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  <MessageOutlined style={{ fontSize: '10px' }} />
                  <span>{session.message_count}条</span>
                  <span>·</span>
                  <span>{new Date(session.last_active).toLocaleDateString('zh-CN')}</span>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '2px', opacity: 0.6 }}>
                <Button
                  size="small"
                  type="text"
                  icon={<EditOutlined />}
                  onClick={() => handleStartEdit(session)}
                  style={{ color: '#667eea' }}
                  title="重命名"
                />
                <Button
                  size="small"
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => handleDeleteSession(session.session_id)}
                  title="删除"
                />
              </div>
            </div>
          ))}
        </Flex>
      </Card>

      {/* 编辑会话名称对话框 */}
      <Modal
        title={
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            color: '#667eea'
          }}>
            <EditOutlined />
            重命名会话
          </div>
        }
        open={editingSessionId !== null}
        onOk={handleSaveEdit}
        onCancel={handleCancelEdit}
        okText="保存"
        cancelText="取消"
        okButtonProps={{
          style: {
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            border: 'none'
          }
        }}
      >
        <Input
          value={editingName}
          onChange={(e) => setEditingName(e.target.value)}
          placeholder="请输入会话名称"
          maxLength={50}
          onPressEnter={handleSaveEdit}
        />
      </Modal>

      <div style={{
        marginTop: 'auto',
        textAlign: 'center',
        paddingTop: '12px',
        borderTop: '1px solid rgba(102, 126, 234, 0.1)'
      }}>
        <div style={{
          fontSize: '11px',
          color: '#999',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '4px'
        }}>
          <span>Powered by</span>
          <span style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            fontWeight: 600
          }}>tiammomo</span>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
