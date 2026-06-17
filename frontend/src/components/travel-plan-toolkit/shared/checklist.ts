// 执行清单（Checklist）的状态样式配置
// 应用场景：出行清单中每项任务有"已完成"和"待处理"两种状态，不同状态显示不同颜色

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

// 根据清单项是否已完成，返回对应的标签文字和颜色样式
// completed=true → 绿色"已完成"；completed=false → 蓝色"待处理"
export function checklistStatusMeta(completed: boolean): {
  label: string;       // 状态文字，如"已完成"或"待处理"
  background: string;  // 背景色（十六进制颜色值）
  border: string;      // 边框色
  color: string;       // 文字色
} {
  if (completed) {
    return {
      label: '已完成',
      background: '#ecfdf5',  // 浅绿色背景
      border: '#86efac',      // 绿色边框
      color: '#166534',       // 深绿色文字
    };
  }
  return {
    label: '待处理',
    background: '#eff6ff',  // 浅蓝色背景
    border: '#93c5fd',      // 蓝色边框
    color: '#1d4ed8',       // 深蓝色文字
  };
}
