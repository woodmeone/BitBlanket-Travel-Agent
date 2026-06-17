// 'use client' 表示这是一个客户端组件，在浏览器端运行（Next.js 的约定）
// 场景举例：用户在浏览器中操作聊天界面时，此组件负责接收输入和发送消息
'use client';

// 导入 React 核心库
import React from 'react';
// 从 antd（蚂蚁金服 UI 组件库）导入常用组件：
//   Badge - 徽标数字，用于显示未读数量等
//   Button - 按钮
//   Checkbox - 复选框
//   Input - 输入框
//   InputNumber - 数字输入框，只能输入数字
//   Popover - 气泡弹出框，点击或悬停时弹出内容
//   Select - 下拉选择框
//   Space - 间距组件，用于控制子元素之间的间距
//   Tag - 标签，用于分类或标记
import { Badge, Button, Checkbox, Input, InputNumber, Popover, Select, Space, Tag } from 'antd';
// 从 antd 图标库导入图标组件：
//   FilterOutlined - 筛选漏斗图标
//   SendOutlined - 发送箭头图标
//   StopOutlined - 停止方块图标
import { FilterOutlined, SendOutlined, StopOutlined } from '@ant-design/icons';
// 导入聊天模式类型（direct/react/plan 三种模式）
import type { ChatMode } from '@/types';
// 导入聊天模式选择器子组件
import ChatModeSelector from '@/components/ChatModeSelector';
// 导入预设约束条件列表和比较方案数量类型
import { PRESET_CONSTRAINTS, type ComparePlanCount } from './shared';

// Input.TextArea 是 antd 提供的多行文本输入框
const { TextArea } = Input;
// 自动调整高度配置：测试环境下禁用自动调整（避免测试不稳定），其他环境最小1行最大4行
const TEXTAREA_AUTOSIZE = process.env.NODE_ENV === 'test' ? false : { minRows: 1, maxRows: 4 };

// 【核心】ChatComposerProps 定义了聊天输入区域组件需要的所有属性（props）
// props 是父组件传递给子组件的数据，类似于函数的参数
// 场景举例：父组件把用户当前选择的聊天模式、输入框内容等数据通过 props 传给 ChatComposer
interface ChatComposerProps {
  chatMode: ChatMode;                          // 当前聊天模式（direct=快速回答 / react=推理执行 / plan=先计划再执行）
  compareModeEnabled: boolean;                 // 是否开启了"比较模式"（同时生成多套方案对比）
  comparePlanCount: ComparePlanCount;          // 比较模式下生成的方案数量（2 或 3）
  budgetUpperLimit: number | null;             // 预算上限（单位：元），null 表示未设置
  inputValue: string;                          // 输入框中的文字内容（受控组件：值由外部状态控制）
  isStreaming: boolean;                        // 是否正在流式输出 AI 回答（true 时禁用输入、显示停止按钮）
  selectedConstraintCount: number;             // 已选中的约束条件数量（用于 Badge 徽标显示）
  selectedConstraints: string[];               // 已选中的约束条件列表，如 ["避开高峰期", "仅限高铁"]
  onBudgetUpperLimitChange: (value: number | null) => void;  // 预算上限变更回调，用户修改预算时触发
  onChatModeChange: (mode: ChatMode) => void;                // 聊天模式变更回调，用户切换模式时触发
  onCompareModeChange: (enabled: boolean) => void;           // 比较模式开关回调，用户勾选/取消时触发
  onComparePlanCountChange: (count: ComparePlanCount) => void; // 比较方案数量变更回调
  onInputChange: (value: string) => void;                    // 输入框内容变更回调，每次按键都会触发
  onSend: () => void;                                        // 【核心】发送消息回调，用户点击发送或按回车时触发
  onSelectedConstraintsChange: (values: string[]) => void;   // 约束条件选择变更回调
  onStop: () => void;                                        // 停止生成回调，用户点击停止按钮时触发
}

// 【核心】ChatComposer 聊天输入区域组件
// React.FC 是 React 的函数组件类型，<> 中是 props 的类型
// 场景举例：用户在输入框输入"上海三日游如何安排"，选择"推理与工具执行"模式，点击发送
// 这里的 { ... } 是 props 解构——把传入的对象属性逐一拆开为独立变量，方便直接使用
const ChatComposer: React.FC<ChatComposerProps> = ({
  chatMode,
  compareModeEnabled,
  comparePlanCount,
  budgetUpperLimit,
  inputValue,
  isStreaming,
  selectedConstraintCount,
  selectedConstraints,
  onBudgetUpperLimitChange,
  onChatModeChange,
  onCompareModeChange,
  onComparePlanCountChange,
  onInputChange,
  onSend,
  onSelectedConstraintsChange,
  onStop,
}) => {
  return (
    <div>
      {/* ====== 顶部区域：聊天模式选择器 + 当前模式描述 ====== */}
      <div
        style={{
          marginBottom: '14px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '12px 16px',
          background: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)',
          borderRadius: '14px',
          border: '1px solid rgba(0, 0, 0, 0.06)',
          boxShadow: '0 2px 10px rgba(0, 0, 0, 0.04)',
        }}
      >
        {/* ChatModeSelector 是聊天模式选择器子组件，disabled={isStreaming} 表示 AI 回答中不可切换 */}
        <ChatModeSelector value={chatMode} onChange={onChatModeChange} disabled={isStreaming} />
        {/* 条件渲染：根据 chatMode 的值显示不同的模式描述文字
            场景举例：用户选择了"推理与工具执行"模式，这里就显示"推理与工具执行" */}
        <div
          style={{
            fontSize: '12px',
            color: '#722ed1',
            background: 'rgba(114, 46, 209, 0.08)',
            padding: '4px 12px',
            borderRadius: '12px',
          }}
        >
          {/* chatMode === 'direct' 时显示"快速回答"，即直接给出答案不经过推理 */}
          {chatMode === 'direct' && '快速回答'}
          {/* chatMode === 'react' 时显示"推理与工具执行"，AI 会边推理边调用工具（如搜索天气） */}
          {chatMode === 'react' && '推理与工具执行'}
          {/* chatMode === 'plan' 时显示"先计划再执行"，AI 先制定计划再逐步执行 */}
          {chatMode === 'plan' && '先计划再执行'}
        </div>
      </div>

      {/* ====== 主体区域：约束条件 + 输入框 + 发送/停止按钮 ====== */}
      <div
        style={{
          background: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)',
          borderRadius: '20px',
          padding: '12px',
          boxShadow: '0 8px 30px rgba(0, 0, 0, 0.12)',
          border: '1px solid rgba(0, 0, 0, 0.08)',
        }}
      >
        {/* 约束条件行：左侧是"行程约束"按钮，右侧是已选约束的标签展示 */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '10px',
          }}
        >
          {/* Popover 气泡弹出框：点击"行程约束"按钮后弹出约束条件设置面板
              trigger="click" 表示点击触发（不是悬停）
              placement="topLeft" 表示弹出位置在左上方 */}
          <Popover
            trigger="click"
            placement="topLeft"
            title={<span style={{ fontSize: '13px' }}>约束条件设置</span>}
            content={
              <div style={{ width: 340, maxWidth: 'calc(100vw - 64px)' }}>
                {/* "出行限制"区域：用 Checkbox.Group 复选框组让用户多选约束条件
                    场景举例：用户勾选"避开高峰期"和"仅限高铁"，AI 规划时会遵守这些限制 */}
                <div style={{ fontSize: '12px', color: '#334155', marginBottom: '8px' }}>出行限制</div>
                <Checkbox.Group
                  options={PRESET_CONSTRAINTS.map((item) => ({ label: item, value: item }))}
                  value={selectedConstraints}
                  onChange={(values) => onSelectedConstraintsChange(values as string[])}
                />

                {/* "预算上限"区域：用 InputNumber 数字输入框让用户设置最大预算
                    场景举例：用户输入 5000，表示旅行预算不超过 5000 元 */}
                <div style={{ fontSize: '12px', color: '#334155', margin: '12px 0 6px' }}>预算上限</div>
                <InputNumber
                  min={100}
                  max={99999}
                  value={budgetUpperLimit ?? undefined}
                  onChange={(value) => onBudgetUpperLimitChange(typeof value === 'number' ? value : null)}
                  placeholder="预算上限(元)"
                  style={{ width: '100%' }}
                />

                {/* "比较模式"区域：勾选后可同时生成多套旅行方案进行对比
                    场景举例：用户勾选"比较模式"并选择"3 套方案"，AI 会同时生成 3 个不同行程供选择 */}
                <div style={{ marginTop: '10px', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                  <Checkbox checked={compareModeEnabled} onChange={(event) => onCompareModeChange(event.target.checked)}>
                    比较模式
                  </Checkbox>
                  {/* Select 下拉选择框：选择比较方案的数量（2套或3套）
                      disabled={!compareModeEnabled} 表示未开启比较模式时此下拉框不可用 */}
                  <Select
                    size="small"
                    style={{ width: 120 }}
                    value={comparePlanCount}
                    disabled={!compareModeEnabled}
                    options={[
                      { label: '2 套方案', value: 2 },
                      { label: '3 套方案', value: 3 },
                    ]}
                    onChange={(value) => onComparePlanCountChange(value as ComparePlanCount)}
                  />
                </div>
              </div>
            }
          >
            {/* Badge 徽标：在"行程约束"按钮右上角显示已选约束的数量
                场景举例：用户选了 3 个约束条件，按钮右上角会显示数字 3 */}
            <Badge count={selectedConstraintCount} size="small">
              <Button icon={<FilterOutlined />} size="small">
                行程约束
              </Button>
            </Badge>
          </Popover>

          {/* 条件渲染：只有选中了约束条件时才显示标签区域（&& 短路写法，前面为 true 才渲染后面） */}
          {selectedConstraintCount > 0 && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                flexWrap: 'wrap',
                justifyContent: 'flex-end',
              }}
            >
              {/* 只展示前 3 个约束条件标签，避免标签过多撑爆布局
                  .map() 是数组的遍历方法，对每个元素生成一个 Tag 标签 */}
              {selectedConstraints.slice(0, 3).map((item) => (
                <Tag key={item} color="blue">
                  {item}
                </Tag>
              ))}
              {/* 条件渲染：有预算上限时显示预算标签，如"≤ 5000元" */}
              {budgetUpperLimit && budgetUpperLimit > 0 && <Tag color="gold">≤ {budgetUpperLimit}元</Tag>}
              {/* 条件渲染：开启比较模式时显示比较标签，如"比较 3 套" */}
              {compareModeEnabled && <Tag color="purple">比较 {comparePlanCount} 套</Tag>}
            </div>
          )}
        </div>

        {/* Space.Compact 让子元素紧密排列（输入框和按钮之间无间隙） */}
        <Space.Compact style={{ width: '100%' }}>
          {/* 【核心】TextArea 多行文本输入框——这是一个"受控组件"
              受控组件的意思：输入框的值（value）由外部状态 inputValue 控制，
              每次输入都会触发 onChange 更新外部状态，外部状态再回传给 value
              这样 React 就完全掌控了输入框的内容 */}
          <TextArea
            value={inputValue}
            onChange={(event) => onInputChange(event.target.value)}
            // onPressEnter 回车键事件处理：
            // 如果按的是 Shift+Enter（换行），不拦截，正常换行
            // 如果只按了 Enter（发送），则阻止默认换行行为并触发发送
            // event.preventDefault() 阻止浏览器默认行为（此处是阻止回车换行）
            onPressEnter={(event) => {
              if (!event.shiftKey) {
                event.preventDefault();
                onSend();
              }
            }}
            // 三元运算符（? :）：isStreaming 为 true 时显示"正在生成回答..."，否则显示正常提示
            // 三元运算符相当于 if-else 的简写：条件 ? 真时的值 : 假时的值
            placeholder={isStreaming ? '正在生成回答...' : '输入你的旅行需求，例如：上海三日游如何安排'}
            disabled={isStreaming}
            autoSize={TEXTAREA_AUTOSIZE}
            style={{ resize: 'none', border: 'none', boxShadow: 'none', outline: 'none' }}
          />
          {/* 【核心】三元运算符条件渲染：根据 isStreaming 状态显示"停止"或"发送"按钮
              isStreaming 为 true → 显示红色"停止"按钮（用户可以中断 AI 生成，danger 属性使其显示为红色警示风格）
              isStreaming 为 false → 显示紫色"发送"按钮（用户可以发送消息，输入为空时 disabled 禁用） */}
          {isStreaming ? (
            <Button
              type="primary"
              danger
              icon={<StopOutlined />}
              onClick={onStop}
              style={{
                borderRadius: '14px',
                height: '42px',
                padding: '0 20px',
                background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                border: 'none',
                boxShadow: '0 4px 15px rgba(239, 68, 68, 0.4)',
              }}
            >
              停止
            </Button>
          ) : (
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={onSend}
              disabled={!inputValue.trim()}
              style={{
                borderRadius: '14px',
                height: '42px',
                padding: '0 24px',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                border: 'none',
                boxShadow: '0 4px 15px rgba(102, 126, 234, 0.4)',
              }}
            >
              发送
            </Button>
          )}
        </Space.Compact>
      </div>
    </div>
  );
};

// 导出组件，使其他文件可以通过 import 使用
export default ChatComposer;
