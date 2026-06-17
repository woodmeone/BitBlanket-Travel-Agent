// 'use client'：客户端组件声明，因为本组件有用户交互（刷新按钮）和状态管理（useState/useEffect）
'use client';

// React 核心库及常用钩子（Hook）：
// useEffect：副作用钩子，组件加载后自动执行某操作（如请求数据）
// useMemo：缓存钩子，避免重复计算，只有依赖项变化时才重新计算
// useState：状态钩子，用来存储组件内部可变数据
import React, { useEffect, useMemo, useState } from 'react';
// 从 Ant Design 引入 UI 组件：
// Alert：警告提示框，用于显示错误信息
// Button：按钮
// Card：卡片容器，用于分组展示内容
// Progress：进度条
// Space：间距容器，自动在子元素之间添加间距
// Spin：加载旋转图标
// Statistic：统计数值展示（如"工具总数: 5"）
// Table：表格，用于展示 Intent 聚合数据
// Tag：标签，用于显示状态标记
import { Alert, Button, Card, Progress, Space, Spin, Statistic, Table, Tag } from 'antd';
// ColumnsType：Ant Design 表格列定义的类型，规定了每列应该有哪些配置
import type { ColumnsType } from 'antd/es/table';
// ReloadOutlined：刷新图标
import { ReloadOutlined } from '@ant-design/icons';
// healthClient：封装好的 API 请求客户端，专门用于调用健康检查相关的后端接口
import { healthClient } from '@/services/api';
// 从类型定义文件引入各种健康检查响应的数据类型
import type {
  HealthResponse,           // 系统整体健康状态
  LLMHealthResponse,       // 大语言模型（LLM）健康状态
  ToolIntentsHealthResponse, // 工具意图聚合健康状态
  ToolsHealthResponse,     // 工具健康状态
} from '@/types';

// IntentRow：Intent 聚合表格中每一行的数据结构
// interface 定义了对象必须包含的属性和类型
interface IntentRow {
  key: string;           // React 列表渲染需要的唯一标识
  intent: string;        // 意图名称，如 "search_hotel"、"plan_itinerary"
  requests: number;      // 该意图的请求总数
  requestShare: number;  // 该意图请求量占总请求量的比例（0~1）
  successRate: number;   // 成功率（0~1）
  timeoutRate: number;   // 超时率（0~1）
  fallbackRate: number;  // 回退率（0~1），即工具调用失败后降级处理的比例
}

// toNumber：安全地将任意值转换为数字
// 应用场景：后端返回的数据格式可能不一致（有时是数字，有时是字符串），
// 这个函数确保无论输入什么，都能得到一个有效的数字
// fallback：转换失败时的默认返回值，默认为 0
function toNumber(value: unknown, fallback = 0): number {
  const parsed = Number(value);  // 尝试将值转为数字
  // Number.isFinite()：检查是否为有限数字（排除 NaN 和 Infinity）
  return Number.isFinite(parsed) ? parsed : fallback;
}

// extractRequests：从指标数据中提取请求量
// 应用场景：后端不同接口返回的请求量字段名不统一，
// 有的叫 requests，有的叫 total_requests，有的叫 count 等
// 这个函数依次尝试多个可能的字段名，找到第一个有值的就返回
function extractRequests(metrics: Record<string, unknown>): number {
  return toNumber(
    // ?? 是空值合并运算符：当前面的值为 null 或 undefined 时，使用后面的值
    metrics.requests ??
      metrics.total_requests ??
      metrics.count ??
      metrics.total ??
      metrics.request_count,
    0
  );
}

// extractRate：从指标数据中提取比率值（如成功率、超时率）
// keys：可能的字段名列表，按优先级排序
// 应用场景：后端可能用 "failure_rate" 或 "error_rate" 表示失败率，
// 这个函数按顺序查找，找到第一个存在的字段就返回
function extractRate(metrics: Record<string, unknown>, keys: string[], fallback = 0): number {
  for (const key of keys) {
    if (key in metrics) {  // 检查对象中是否存在该属性
      const value = toNumber(metrics[key], fallback);
      // Math.max(0, Math.min(1, value))：将值限制在 0~1 范围内（夹紧/clamp）
      return Math.max(0, Math.min(1, value));
    }
  }
  return fallback;
}

// 【核心】SystemStatusPanel：系统状态面板组件
// 作用：展示后端各服务的健康状态、工具统计和 Intent 聚合数据
// 应用场景：运维人员或开发者查看系统是否正常运行，哪些意图调用最频繁、成功率如何
const SystemStatusPanel: React.FC = () => {
  // useState：声明组件内部状态，[当前值, 设置值的函数]
  // null 表示初始值为空，泛型 <HealthResponse | null> 表示值可以是 HealthResponse 类型或 null
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [llmHealth, setLlmHealth] = useState<LLMHealthResponse | null>(null);
  const [toolsHealth, setToolsHealth] = useState<ToolsHealthResponse | null>(null);
  const [intentHealth, setIntentHealth] = useState<ToolIntentsHealthResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);  // 是否正在加载
  const [error, setError] = useState<string | null>(null);  // 错误信息

  // 【核心】loadStatus：加载所有系统状态数据
  // async/await：异步编程语法，让异步代码看起来像同步代码
  // 应用场景：用户打开系统状态面板或点击刷新按钮时，同时请求4个后端接口获取数据
  const loadStatus = async () => {
    try {
      setIsLoading(true);   // 开始加载，显示加载动画
      setError(null);       // 清除之前的错误信息
      // Promise.all：同时发起多个异步请求，等所有请求都完成后一起返回结果
      // 比逐个请求更快，因为4个请求是并行执行的
      const [h, llm, tools, intents] = await Promise.all([
        healthClient.checkHealth(),            // 检查系统整体健康
        healthClient.checkLLMHealth(),         // 检查大模型服务健康
        healthClient.checkToolsHealth(),       // 检查工具服务健康
        healthClient.checkToolsIntentsHealth(), // 检查工具意图聚合数据
      ]);
      // 将请求结果存入对应的状态
      setHealth(h);
      setLlmHealth(llm);
      setToolsHealth(tools);
      setIntentHealth(intents);
    } catch (loadError) {
      // catch：捕获请求过程中的错误
      // instanceof Error：判断是否为 Error 类型的错误对象
      setError(loadError instanceof Error ? loadError.message : '加载系统状态失败');
    } finally {
      // finally：无论成功还是失败，都会执行的代码
      setIsLoading(false);  // 结束加载状态
    }
  };

  // useEffect：组件挂载（首次渲染到页面）后自动执行
  // 空数组 [] 表示只在组件首次加载时执行一次，不会重复执行
  useEffect(() => {
    loadStatus();
  }, []);

  // useMemo：缓存计算结果，只有 intentHealth 变化时才重新计算
  // 应用场景：将后端返回的 intent 聚合数据转换为表格可用的行数据
  // 例如：后端返回 { "search_hotel": { requests: 50, failure_rate: 0.1 }, ... }
  // 转换为 [{ key: "search_hotel", intent: "search_hotel", requests: 50, successRate: 0.9, ... }]
  const intentRows = useMemo<IntentRow[]>(() => {
    const aggregate = intentHealth?.intent_aggregate || {};  // ?. 可选链，如果 intentHealth 为 null 则返回 undefined
    // Object.entries()：将对象转为 [key, value] 数组，方便遍历
    const rows = Object.entries(aggregate).map(([intent, raw]) => {
      const metrics = (raw || {}) as Record<string, unknown>;  // as 类型断言，告诉 TypeScript 这是某种类型
      return {
        key: intent,
        intent,
        requests: extractRequests(metrics),
        // 成功率 = 1 - 失败率（后端存的是失败率，前端显示成功率）
        successRate:
          1 -
          extractRate(metrics, ['failure_rate', 'error_rate'], 0),
        timeoutRate: extractRate(metrics, ['timeout_rate']),
        fallbackRate: extractRate(metrics, ['fallback_rate']),
        requestShare: 0,  // 先设为0，下面统一计算
      };
    });

    // 计算总请求数，用于算各意图的请求占比
    const total = rows.reduce((sum, item) => sum + item.requests, 0);
    return rows
      .map((item) => ({
        ...item,  // 展开运算符，复制对象的所有属性
        // 三元表达式：total > 0 时计算占比，否则为 0（避免除以0的错误）
        requestShare: total > 0 ? item.requests / total : 0,
      }))
      .sort((a, b) => b.requests - a.requests);  // 按请求量从高到低排序
  }, [intentHealth]);

  // intentColumns：表格列配置，定义了每列的标题、数据字段和渲染方式
  const intentColumns = useMemo<ColumnsType<IntentRow>>(
    () => [
      {
        title: 'Intent',           // 列标题
        dataIndex: 'intent',       // 对应数据中的字段名
        key: 'intent',             // 列的唯一标识
        width: 180,                // 列宽（像素）
        render: (value: string) => <Tag color="geekblue">{value}</Tag>,  // 自定义渲染：用蓝色标签显示
      },
      {
        title: '请求量',
        dataIndex: 'requests',
        key: 'requests',
        width: 90,
        sorter: (a, b) => a.requests - b.requests,  // 支持点击表头排序
      },
      {
        title: '请求占比趋势',
        dataIndex: 'requestShare',
        key: 'requestShare',
        width: 260,
        // 用进度条可视化占比，如 45% 显示为接近一半的进度条
        render: (value: number) => (
          <Progress
            percent={Math.round(value * 100)}  // 转为百分比整数
            size="small"
            strokeColor={{ '0%': '#0ea5e9', '100%': '#2563eb' }}  // 渐变色：从浅蓝到深蓝
            format={(percent) => `${percent || 0}%`}  // 显示的文字格式
          />
        ),
      },
      {
        title: '成功率趋势',
        dataIndex: 'successRate',
        key: 'successRate',
        width: 230,
        render: (value: number) => (
          <Progress
            percent={Math.round(value * 100)}
            size="small"
            strokeColor={{ '0%': '#22c55e', '100%': '#15803d' }}  // 渐变色：从浅绿到深绿
            format={(percent) => `${percent || 0}%`}
          />
        ),
      },
      {
        title: '超时率',
        dataIndex: 'timeoutRate',
        key: 'timeoutRate',
        width: 90,
        render: (value: number) => `${Math.round(value * 100)}%`,  // 如 0.05 显示为 "5%"
      },
      {
        title: '回退率',
        dataIndex: 'fallbackRate',
        key: 'fallbackRate',
        width: 90,
        render: (value: number) => `${Math.round(value * 100)}%`,
      },
    ],
    []  // 空依赖数组，列配置不会变化，只计算一次
  );

  return (
    <div style={{ margin: '0 16px 16px' }}>
      {/* 外层卡片：带圆角和绿色渐变背景 */}
      <Card
        style={{
          borderRadius: 16,
          border: '1px solid rgba(16, 185, 129, 0.2)',  // 半透明绿色边框
          background: 'linear-gradient(145deg, #ffffff 0%, #f0fdf4 100%)',  // 从白色到浅绿色的渐变
        }}
        styles={{ body: { padding: 16 } }}
      >
        {/* 顶部标题栏和刷新按钮 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
          <div style={{ fontSize: 16, fontWeight: 600, color: '#166534' }}>系统状态中心</div>
          {/* 刷新按钮：点击后重新调用 loadStatus 获取最新数据 */}
          <Button icon={<ReloadOutlined />} onClick={loadStatus} loading={isLoading}>
            刷新
          </Button>
        </div>

        {/* 错误提示：有错误时才显示 */}
        {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 12 }} />}
        {/* 加载中显示旋转动画，加载完成显示内容 */}
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '30px 0' }}>
            <Spin />
          </div>
        ) : (
          // Space：垂直排列的间距容器
          <Space orientation="vertical" size={12} style={{ width: '100%' }}>
            {/* 状态标签卡片：显示各服务的健康状态 */}
            <Card size="small">
              <Space wrap>
                {/* 根据状态值显示不同颜色的标签：健康=绿色，异常=红色/金色 */}
                <Tag color={health?.status === 'healthy' ? 'green' : 'red'}>API: {health?.status || 'unknown'}</Tag>
                <Tag color={llmHealth?.status === 'ok' ? 'green' : 'gold'}>LLM: {llmHealth?.status || 'unknown'}</Tag>
                <Tag color={toolsHealth?.status === 'ok' ? 'green' : 'gold'}>
                  Tools: {toolsHealth?.status || 'unknown'}
                </Tag>
                <Tag color="blue">Version: {health?.version || '-'}</Tag>
              </Space>
            </Card>

            {/* 统计数值卡片网格 */}
            {/* grid 布局：auto-fill 自动填充列，每列最小180px */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 10 }}>
              <Card size="small">
                {/* Statistic：数值统计展示，?? 是空值合并运算符，左侧为 null/undefined 时用右侧值 */}
                <Statistic title="工具总数" value={llmHealth?.tools_count ?? 0} />
              </Card>
              <Card size="small">
                {/* Circuit Open：熔断器开启数量，熔断器是保护系统的机制，当错误过多时自动"断路"停止调用 */}
                <Statistic title="Circuit Open" value={toolsHealth?.circuit_open_count ?? 0} />
              </Card>
              <Card size="small">
                {/* 监控窗口：熔断器统计错误率的时间范围（分钟） */}
                <Statistic title="监控窗口(分钟)" value={toolsHealth?.window_minutes ?? 0} />
              </Card>
              <Card size="small">
                <Statistic title="请求总量" value={intentHealth?.total_requests ?? 0} />
              </Card>
            </div>

            {/* Intent 聚合数据表格 */}
            <Card size="small" title="Intent 聚合（结构化）">
              {intentRows.length === 0 ? (
                <div style={{ color: '#64748b' }}>暂无 intent 聚合数据</div>
              ) : (
                <Table
                  rowKey="key"               // 每行的唯一标识字段
                  columns={intentColumns}     // 列配置
                  dataSource={intentRows}     // 数据源
                  pagination={false}           // 不分页（数据量不大）
                  size="small"                // 紧凑尺寸
                  scroll={{ x: 980 }}         // 横向滚动，防止窄屏下列被挤压
                />
              )}
            </Card>
          </Space>
        )}
      </Card>
    </div>
  );
};

export default SystemStatusPanel;
