// 子 Agent（子智能体）的中文标签映射
// 应用场景：行程规划由多个子 Agent 协作完成，在界面上展示协作轨迹时，
//   需要把英文的 Agent 名称翻译成中文，让用户更容易理解
//   例如：规划流程显示为"研究 → 规划 → 预算 → 校验"

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

// 将子 Agent 的英文名称转换为中文标签
// 如果名称不在已知列表中，则原样返回
export function subagentLabel(name: string): string {
  if (name === 'planning') return '规划';       // 规划 Agent：负责编排行程
  if (name === 'research') return '研究';       // 研究 Agent：负责搜索景点信息
  if (name === 'budget') return '预算';         // 预算 Agent：负责估算费用
  if (name === 'verification') return '校验';   // 校验 Agent：负责检查行程合理性
  return name;                                  // 未知 Agent：直接返回原名
}
