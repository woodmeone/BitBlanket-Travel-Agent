// 'use client'：声明为客户端组件，支持用户交互（如点击选择模式）
'use client';

// React：前端框架核心
import React from 'react';
// Badge：小圆点/数字标记，这里用来显示当前模式的颜色指示点
// Select：下拉选择器，用户点击后弹出选项列表
// Tooltip：文字提示，鼠标悬停时显示说明文字
import { Badge, Select, Tooltip } from 'antd';
// 从 @ant-design/icons 引入图标组件，每个图标就是一个 React 组件
// BulbOutlined：灯泡图标，代表"推理/思考"
// FileTextOutlined：文件图标，代表"计划"
// ThunderboltOutlined：闪电图标，代表"快速"
import { BulbOutlined, FileTextOutlined, ThunderboltOutlined } from '@ant-design/icons';
// ChatMode：自定义类型，定义了聊天模式的可选值（'direct' | 'react' | 'plan'）
import { ChatMode } from '@/types';

// interface：TypeScript 中定义对象形状的方式，类似于"蓝图"，规定了对象必须有哪些属性
// ChatModeSelectorProps：这个组件接收的属性（Props）定义
interface ChatModeSelectorProps {
  value: ChatMode;              // 当前选中的模式
  onChange: (value: ChatMode) => void;  // 模式变化时的回调函数，void 表示没有返回值
  disabled?: boolean;           // 是否禁用选择器，? 表示这个属性是可选的
}

// modeOptions：三种聊天模式的配置列表
// as const：TypeScript 语法，让数组变成"只读常量"，防止意外修改
const modeOptions = [
  {
    value: 'direct',            // 模式标识，对应 ChatMode 类型
    label: '直答模式',          // 显示给用户的名称
    icon: <ThunderboltOutlined />,  // 闪电图标
    description: '速度最快，直接返回答案',  // 模式说明
    color: '#52c41a',           // 绿色，代表"快速/通行"
  },
  {
    value: 'react',
    label: 'ReAct 模式',
    icon: <BulbOutlined />,     // 灯泡图标
    // 应用场景举例：用户问"帮我规划一个3天的成都旅行"，ReAct 模式会先推理需要查什么信息，
    // 然后调用天气、酒店、景点等工具获取数据，再综合给出答案
    description: '推理 + 工具调用，适合复杂旅行问题',
    color: '#1890ff',           // 蓝色，代表"智能/推理"
  },
  {
    value: 'plan',
    label: 'Plan 模式',
    icon: <FileTextOutlined />, // 文件图标
    // 应用场景举例：用户说"帮我安排5天的日本旅行"，Plan 模式会先列出完整计划（第1天去哪、第2天去哪），
    // 用户确认后再逐步执行每个步骤
    description: '先展示计划，再分步执行',
    color: '#722ed1',           // 紫色，代表"计划/策略"
  },
] as const;

// 【核心】ChatModeSelector 组件：聊天模式选择器
// value = 'react'：默认值是 ReAct 模式（解构赋值时设置默认值）
// disabled = false：默认不禁用
const ChatModeSelector: React.FC<ChatModeSelectorProps> = ({ value = 'react', onChange, disabled = false }) => {
  // find()：在数组中查找第一个符合条件的元素
  // 这里根据当前选中的 value 找到对应的模式配置，用于显示颜色指示点和提示文字
  const activeMode = modeOptions.find((item) => item.value === value);

  return (
    // div：HTML 容器标签，用来包裹一组元素
    // style：行内样式，直接写在标签上的 CSS 样式
    // display: 'flex'：弹性布局，让子元素水平排列
    // alignItems: 'center'：垂直居中对齐
    // gap: '8px'：子元素之间的间距为8像素
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      {/* "对话模式:" 标签文字 */}
      <span style={{ fontSize: '12px', color: '#999', whiteSpace: 'nowrap' }}>对话模式:</span>
      {/* 【核心】Select 下拉选择器，用户点击后弹出三个模式选项 */}
      <Select
        value={value}           // 当前选中的值
        onChange={onChange}      // 选中变化时触发 onChange 回调
        disabled={disabled}      // 是否禁用
        style={{ width: 170 }}   // 选择器宽度170像素
        size="small"             // 小尺寸
        // options：下拉选项列表，通过 map() 将 modeOptions 转换为 Select 需要的格式
        options={modeOptions.map((option) => ({
          value: option.value,
          // label：每个选项的显示内容，包含彩色图标和文字
          label: (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ color: option.color }}>{option.icon}</span>
              <span>{option.label}</span>
            </div>
          ),
          // title：鼠标悬停时显示的提示文字
          title: option.description,
        }))}
      />
      {/* Tooltip：鼠标悬停在 Badge 上时，显示当前模式的详细说明 */}
      <Tooltip title={activeMode?.description}>
        {/* Badge：小圆点指示器，颜色随当前模式变化，cursor: 'help' 表示鼠标变成问号样式 */}
        <Badge color={activeMode?.color} text="" style={{ cursor: 'help' }} />
      </Tooltip>
    </div>
  );
};

export default ChatModeSelector;
