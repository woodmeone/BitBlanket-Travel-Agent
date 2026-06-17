/**
 * Session navigation panel for create, select, rename, and delete operations.
 * Encapsulates list interactions to keep the main page focused on chat rendering.
 *
 * 会话导航面板，用于创建、选择、重命名和删除会话。
 * 将列表交互封装在此组件中，使主页面专注于聊天渲染。
 */

// 导入 React 核心库和 useState Hook
// useState 是 React 的状态管理 Hook，用于在函数组件中添加可变状态
// 调用方式：const [状态值, 设置函数] = useState(初始值)
import React, { useState } from 'react';
// 从 antd（蚂蚁金服 UI 组件库）导入多个 UI 组件
// Button：按钮组件  Input：输入框组件  Space：间距组件  Card：卡片容器
// Modal：对话框组件  Select：下拉选择组件  Spin：加载动画组件
// App：应用级组件（提供 message 等全局方法） Flex：弹性布局组件
// Badge：徽标组件  Tag：标签组件
import { Button, Input, Space, Card, Modal, Select, Spin, App, Flex, Badge, Tag } from 'antd';
// 从 antd 图标库导入各种图标组件
// 图标组件用于在按钮、标题等位置显示小图标，提升界面可读性
import {
  PlusOutlined,       // 加号图标，用于"新建"按钮
  DeleteOutlined,     // 删除图标，用于"删除"按钮
  CheckCircleOutlined,// 勾选图标，用于标记当前选中项
  EditOutlined,       // 编辑图标，用于"重命名"按钮
  RobotOutlined,      // 机器人图标，用于 AI 模型区域
  MessageOutlined,    // 消息图标，用于历史会话区域
  ClearOutlined,      // 清除图标，用于"清空对话"按钮
} from '@ant-design/icons';
// 导入应用上下文 Hook
// useAppContext 是自定义 Hook，用于获取全局共享状态（如当前会话 ID、会话列表等）
// Context 是 React 的跨组件数据传递机制，避免通过 props 层层传递
import { useAppContext } from '../context/AppContext';
// 导入 API 客户端
// chatClient：聊天相关的 API 请求客户端（如发送消息、清空对话）
// sessionClient：会话相关的 API 请求客户端（如创建、删除、重命名会话）
import { chatClient, sessionClient } from '../services/api';
// 导入日志工具，用于记录错误和调试信息
import { logger } from '../utils/logger';
// 导入 SessionInfo 类型定义
// TypeScript 中 interface/type 用于定义数据结构的形状
// SessionInfo 描述了一个会话对象包含哪些字段（如 session_id、name、message_count 等）
import { SessionInfo } from '../types';

// 从 Select 组件中解构出 Option 子组件
// 解构赋值：const { a } = obj 相当于 const a = obj.a
// Select.Option 是下拉选项组件，放在 Select 内部表示每个可选项
const { Option } = Select;

// Sidebar 侧边栏组件，提供会话管理和模型切换功能
const Sidebar: React.FC = () => {
  // App.useApp() 获取 antd 提供的全局方法，这里用到 message 来显示操作提示
  // message.success('xxx') 会在页面顶部弹出绿色成功提示
  // message.error('xxx') 会弹出红色错误提示
  const { message } = App.useApp();

  // 从 AppContext 中解构出多个全局状态和方法
  // 解构赋值允许我们从对象中提取需要的属性，直接用变量名访问
  const {
    currentSessionId,    // 当前选中的会话 ID
    switchSession,       // 切换会话的方法，传入会话 ID 即可切换
    availableModels,     // 可用的 AI 模型列表
    currentModelId,      // 当前选中的模型 ID
    setCurrentModelId,   // 设置当前模型 ID 的方法
    loadingModels,       // 模型列表是否正在加载中
    sessions,            // 所有会话列表
    refreshSessions,     // 刷新会话列表的方法（从服务器重新获取）
    clearMessages,       // 清空当前会话消息的方法
  } = useAppContext();

  // useState 创建组件内部状态
  // loading：是否正在创建新会话（创建过程中按钮显示加载动画）
  const [loading, setLoading] = useState(false);
  // switchingModel：是否正在切换模型（切换过程中下拉框显示加载状态）
  const [switchingModel, setSwitchingModel] = useState(false);
  // editingSessionId：正在编辑名称的会话 ID，null 表示没有在编辑
  // useState<string | null>(null) 中的 <string | null> 是 TypeScript 泛型，
  // 表示这个状态的值可以是字符串或 null
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  // editingName：编辑中的会话名称，用于重命名对话框中的输入框
  const [editingName, setEditingName] = useState('');

  // 【核心】创建新会话
  // async/await 是处理异步操作的语法，async 声明异步函数，await 等待异步操作完成
  // 应用场景：用户点击"新建会话"按钮时触发
  const handleCreateSession = async () => {
    try {
      setLoading(true);  // 开始加载，按钮显示加载动画
      // 调用后端 API 创建新会话，返回包含 session_id 的数据
      const data = await sessionClient.createSession();
      // 切换到新创建的会话
      switchSession(data.session_id);
      // 刷新会话列表，让新会话出现在历史会话中
      await refreshSessions();
      message.success('新会话已创建');
    } catch (error) {
      // try/catch 捕获异步操作中的错误
      message.error('创建会话失败');
    } finally {
      // finally 块无论成功还是失败都会执行，用于清理状态
      setLoading(false);  // 结束加载状态
    }
  };

  // 【核心】删除会话
  // 应用场景：用户点击会话旁的删除图标时触发
  const handleDeleteSession = async (sessionId: string) => {
    try {
      // 调用后端 API 删除指定会话
      await sessionClient.deleteSession(sessionId);
      // 如果删除的是当前正在使用的会话，需要切换到空状态
      if (sessionId === currentSessionId) {
        switchSession(null);
      }
      // 刷新会话列表
      await refreshSessions();
      message.success('会话已删除');
    } catch (error) {
      message.error('删除失败');
    }
  };

  // 切换会话
  // 应用场景：用户点击历史会话列表中的某个会话时触发
  const handleSwitchSession = (sessionId: string) => {
    switchSession(sessionId);
  };

  // 开始编辑会话名称
  // 应用场景：用户点击会话旁的编辑图标时触发，打开重命名对话框
  const handleStartEdit = (session: SessionInfo) => {
    // 记录正在编辑的会话 ID
    setEditingSessionId(session.session_id);
    // 将编辑框的初始值设为当前会话名称，如果没有名称则用 ID 前 8 位作为默认名
    // session_id.slice(0, 8) 截取字符串前 8 个字符
    setEditingName(session.name || `会话 ${session.session_id.slice(0, 8)}`);
  };

  // 取消编辑
  // 应用场景：用户在重命名对话框中点击"取消"时触发
  const handleCancelEdit = () => {
    setEditingSessionId(null);  // 清除正在编辑的会话 ID
    setEditingName('');         // 清空编辑框内容
  };

  // 【核心】保存会话名称
  // 应用场景：用户在重命名对话框中点击"保存"或按回车时触发
  const handleSaveEdit = async () => {
    // 如果没有正在编辑的会话，或名称为空（trim() 去除首尾空格后为空），则直接返回
    if (!editingSessionId || !editingName.trim()) return;

    try {
      // 调用后端 API 更新会话名称
      await sessionClient.updateSessionName(editingSessionId, editingName.trim());
      // 刷新会话列表以显示新名称
      await refreshSessions();
      // 清除编辑状态
      setEditingSessionId(null);
      setEditingName('');
      message.success('会话名称已更新');
    } catch (error) {
      message.error('更新失败');
    }
  };

  // 清空对话
  // 应用场景：用户点击"清空对话"按钮时触发，清除当前会话的所有消息
  const handleClearChat = async () => {
    if (!currentSessionId) {
      message.warning('请先创建会话');
      return;
    }

    try {
      // 调用后端 API 清空当前会话的聊天记录
      await chatClient.clearChat(currentSessionId);
      // 清空前端的消息列表
      clearMessages();
      message.success('对话已清空');
    } catch (error) {
      message.error('清空失败');
    }
  };

  // 【核心】模型切换
  // 应用场景：用户在下拉框中选择不同的 AI 模型时触发
  // 例如从"GPT-4"切换到"Claude"，不同模型有不同的能力和响应风格
  const handleModelChange = async (modelId: string) => {
    try {
      setSwitchingModel(true);  // 开始切换，下拉框显示加载状态
      // 调用全局方法设置当前模型
      await setCurrentModelId(modelId);
      // 从可用模型列表中找到选中的模型，用于显示切换成功的提示
      // find() 是数组方法，返回第一个满足条件的元素
      const model = availableModels.find(m => m.model_id === modelId);
      message.success(`已切换到 ${model?.name || modelId}`);
      // model?.name 是可选链操作符，如果 model 为 null/undefined 则不会报错，而是返回 undefined
    } catch (error) {
      message.error('模型切换失败，请重试');
      logger.error('模型切换错误:', error);
    } finally {
      setSwitchingModel(false);  // 结束切换状态
    }
  };

  // return 语句返回 JSX，描述侧边栏的 UI 结构
  return (
    // 侧边栏最外层容器
    // style 中的 CSS 属性采用驼峰命名法（如 flexDirection 对应 CSS 的 flex-direction）
    <div style={{
      padding: '20px',          // 内边距
      height: '100%',           // 占满父容器高度
      display: 'flex',          // 弹性盒布局
      flexDirection: 'column',  // 子元素纵向排列
      gap: '16px'               // 子元素之间的间距
    }}>
      {/* Logo/标题区域 */}
      <div style={{
        textAlign: 'center',
        padding: '8px 0 16px',
        borderBottom: '1px solid rgba(102, 126, 234, 0.1)'  // 底部分隔线
      }}>
        {/* Logo 图片 */}
        <img
          src="/logo.png"
          alt="放心游"
          style={{
            width: '36px',
            height: '36px',
            borderRadius: '10px',
            marginBottom: '8px',
            objectFit: 'cover',
          }}
        />
        {/* 应用名称，使用渐变色文字效果
            WebkitBackgroundClip: 'text' 和 WebkitTextFillColor: 'transparent'
            配合 background 渐变实现文字渐变色效果 */}
        <div style={{
          fontSize: '16px',
          fontWeight: 600,
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}>
          放心游旅行助手
        </div>
        {/* 副标题 */}
        <div style={{
          fontSize: '12px',
          color: '#999',
          marginTop: '4px'
        }}>
          智能AI旅行规划
        </div>
      </div>

      {/* 模型选择卡片 */}
      <Card
        size="small"  // 小尺寸卡片
        style={{
          marginBottom: 0,
          background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%)',
        }}
        styles={{ body: { padding: '12px' } }}  // 卡片内容区域的内边距
      >
        {/* 模型区域标题 */}
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
        {/* 条件渲染：模型列表加载中时显示加载动画，加载完成后显示下拉选择框
            三元运算符 condition ? A : B，条件为真显示 A，否则显示 B */}
        {loadingModels ? (
          // 加载中状态
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 0' }}>
            <Spin size="small" />
            <span style={{ fontSize: '13px', color: '#999' }}>加载中...</span>
          </div>
        ) : (
          // 【核心】模型选择下拉框
          // value：当前选中的值  onChange：选中项变化时的回调
          // loading：是否显示加载状态  disabled：是否禁用（无可用模型或正在切换时禁用）
          <Select
            value={currentModelId}
            onChange={handleModelChange}
            style={{ width: '100%' }}
            placeholder="选择模型"
            suffixIcon={<RobotOutlined style={{ color: '#667eea' }} />}
            loading={switchingModel}
            disabled={availableModels.length === 0 || switchingModel}
          >
            {/* 遍历可用模型列表，为每个模型生成一个下拉选项
                map() 是数组方法，对每个元素执行函数并返回新数组
                key 属性帮助 React 识别列表中的每个元素，提高渲染效率 */}
            {availableModels.map((model) => (
              <Option key={model.model_id} value={model.model_id}>
                {model.name}
              </Option>
            ))}
          </Select>
        )}
      </Card>

      {/* 会话管理卡片 */}
      <Card
        size="small"
        styles={{ body: { padding: '12px' } }}
      >
        {/* Space 组件用于在子元素之间添加统一间距 */}
        <Space orientation="vertical" style={{ width: '100%' }} size="small">
          {/* 新建会话按钮 */}
          <Button
            icon={<PlusOutlined />}
            onClick={handleCreateSession}
            loading={loading}  // loading 为 true 时按钮显示加载动画并禁用点击
            style={{
              width: '100%',
              height: '40px',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              border: 'none',
              borderRadius: '10px',
              fontWeight: 500,
            }}
            type="primary"  // 主要按钮样式（实心背景色）
          >
            新建会话
          </Button>
          {/* 清空对话按钮 */}
          <Button
            onClick={handleClearChat}
            icon={<ClearOutlined />}
            style={{
              width: '100%',
              height: '36px',
              borderRadius: '10px',
              borderColor: 'rgba(255, 107, 107, 0.5)',
              color: '#ff6b6b'  // 红色文字，暗示这是危险操作
            }}
          >
            清空对话
          </Button>
        </Space>
      </Card>

      {/* 历史会话卡片 */}
      <Card
        size="small"
        style={{
          flex: 1,               // 占据剩余空间
          overflow: 'hidden',    // 超出部分隐藏
          display: 'flex',
          flexDirection: 'column',
          marginBottom: 0
        }}
        styles={{
          body: {
            flex: 1,
            overflow: 'auto',    // 内容超出时显示滚动条
            padding: '8px'
          }
        }}
      >
        {/* 历史会话标题栏 */}
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
          {/* Tag 组件显示会话总数，marginLeft: 'auto' 将其推到右侧 */}
          <Tag style={{ marginLeft: 'auto', fontSize: '11px' }}>{sessions.length}</Tag>
        </div>
        {/* Flex 组件纵向排列会话列表，gap: 4 设置每项间距 */}
        <Flex vertical gap={4}>
          {/* 遍历会话列表，渲染每个会话项 */}
          {sessions.map((session) => (
            <div
              key={session.session_id}  // key 帮助 React 高效更新列表
              // 动态 class 名：当前选中的会话添加 'active' 样式类
              // 模板字符串 `` 内的 ${} 可以嵌入 JavaScript 表达式
              className={`session-item ${session.session_id === currentSessionId ? 'active' : ''}`}
              style={{
                padding: '10px 12px',
                borderRadius: '10px',
                cursor: 'pointer',     // 鼠标悬停显示手型光标
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              {/* 会话信息区域，点击可切换到该会话 */}
              <div
                onClick={() => handleSwitchSession(session.session_id)}
                style={{ cursor: 'pointer', flex: 1, minWidth: 0 }}
              >
                {/* 会话名称行 */}
                <div style={{
                  fontWeight: session.session_id === currentSessionId ? '600' : 'normal',  // 选中项加粗
                  fontSize: '13px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  color: session.session_id === currentSessionId ? '#667eea' : '#333'  // 选中项高亮色
                }}>
                  {/* 当前选中的会话显示勾选图标 */}
                  {session.session_id === currentSessionId && (
                    <CheckCircleOutlined style={{ color: '#667eea', fontSize: '12px' }} />
                  )}
                  {/* 会话名称，超长时省略号显示
                      textOverflow: 'ellipsis' 配合 overflow: 'hidden' 和 whiteSpace: 'nowrap' 实现文字截断 */}
                  <span style={{
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                  }}>
                    {session.name || `会话 ${session.session_id.slice(0, 8)}`}
                  </span>
                </div>
                {/* 会话元信息：消息数量和最后活跃时间 */}
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
                  {/* toLocaleDateString('zh-CN') 将日期格式化为中文格式，如"2024/1/15" */}
                  <span>{new Date(session.last_active).toLocaleDateString('zh-CN')}</span>
                </div>
              </div>
              {/* 操作按钮区域：重命名和删除 */}
              <div style={{ display: 'flex', gap: '2px', opacity: 0.6 }}>
                {/* 重命名按钮 */}
                <Button
                  size="small"
                  type="text"   // 文本按钮（无边框无背景）
                  icon={<EditOutlined />}
                  onClick={() => handleStartEdit(session)}
                  style={{ color: '#667eea' }}
                  title="重命名"  // 鼠标悬停时的提示文字
                />
                {/* 删除按钮 */}
                <Button
                  size="small"
                  type="text"
                  danger  // danger 属性使按钮显示红色，暗示危险操作
                  icon={<DeleteOutlined />}
                  onClick={() => handleDeleteSession(session.session_id)}
                  title="删除"
                />
              </div>
            </div>
          ))}
        </Flex>
      </Card>

      {/* 编辑会话名称对话框（Modal）
          Modal 是浮层对话框组件，覆盖在页面上方
          - open：控制对话框是否显示，editingSessionId 不为 null 时显示
          - onOk：点击"确定"按钮的回调
          - onCancel：点击"取消"按钮或遮罩层的回调 */}
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
        okText="保存"      // 确定按钮文字
        cancelText="取消"  // 取消按钮文字
        okButtonProps={{
          style: {
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            border: 'none'
          }
        }}
      >
        {/* 输入框
            - value：输入框的值，受控组件模式（值由 state 控制）
            - onChange：输入内容变化时的回调，e.target.value 获取输入框的新值
            - maxLength：最大输入长度
            - onPressEnter：按下回车键时的回调，等同于点击"保存" */}
        <Input
          value={editingName}
          onChange={(e) => setEditingName(e.target.value)}
          placeholder="请输入会话名称"
          maxLength={50}
          onPressEnter={handleSaveEdit}
        />
      </Modal>

      {/* 底部版权信息
          marginTop: 'auto' 将其推到容器底部 */}
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

// export default 将该组件作为默认导出，其他文件可以通过 import Sidebar from '...' 引入
export default Sidebar;
