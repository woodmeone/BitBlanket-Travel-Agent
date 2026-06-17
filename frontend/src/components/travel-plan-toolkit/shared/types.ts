// 【核心】旅行行程工具包的公共类型定义文件
// TypeScript 中 type 和 interface 都用来定义"数据长什么样"（即类型/形状）
// type 更适合定义联合类型（如 'saving' | 'balanced'），interface 更适合定义对象结构

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

// BudgetMode 预算模式：三种选择——省钱(saving)、平衡(balanced)、舒适(comfort)
// 联合类型：变量只能是这三个字符串之一，不能是其他值
export type BudgetMode = 'saving' | 'balanced' | 'comfort';

// CompareRow 方案对比表格中的一行数据
// interface 定义了对象必须包含哪些字段（类似表格的列名）
export interface CompareRow {
  key: string;                       // 行的唯一标识，用于 React 渲染时的 key 属性
  metric: string;                    // 对比指标名称，如"总预算"、"天数"等
  values: Record<string, string>;    // 每个方案的对应值，键是方案名，值是指标值
                                     // Record<string, string> 表示"键是字符串、值也是字符串"的对象
                                     // 例如：{ "方案A": "¥3000", "方案B": "¥5000" }
}

// QuickRefineAction 快速微调操作按钮的配置
export interface QuickRefineAction {
  key: string;      // 操作的唯一标识
  label: string;    // 按钮上显示的文字，如"增加预算"
  prompt: string;   // 点击后发送给 AI 的提示词，告诉 AI 要怎么调整方案
}
