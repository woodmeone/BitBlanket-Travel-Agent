// api.ts —— services 目录下的 API 入口文件
// 本文件是 services 层的最外层入口，将 api/ 目录下的所有导出项再次转发
// 外部代码只需要写 import { xxx } from '@/services/api' 即可使用所有 API 功能
//
// 关键概念解释：
// - export * from './api/index'：批量重新导出目标模块的所有导出项
//   * 表示"所有"，相当于把 api/index.ts 中所有 export 的内容都重新导出一次
//   这样外部代码不需要关心内部文件的目录结构

export * from './api/index';
