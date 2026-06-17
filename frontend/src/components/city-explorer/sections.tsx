// 'use client' —— 客户端组件声明，表示此模块在浏览器端运行
'use client';

// 【核心】sections.tsx —— 城市探索模块的统一导出入口
// 这个文件不包含任何组件实现，只负责把各个子模块"重新导出"（re-export）
// 好处：外部引用时只需要写一层路径，如 import { CityExplorerHero } from './sections'
//       而不需要写 import { CityExplorerHero } from './sections/HeroSection'
// export { X } from '...' —— 从指定文件导出组件，同时让外部可以通过本文件访问
export { CityExplorerHero } from './sections/HeroSection';           // 城市探索顶部区域（灵感起点 + 候选池）
export { CityExplorerFilterBar } from './sections/FilterBarSection'; // 筛选栏（地区/标签/快速筛选）
export { CityExplorerComparePanel } from './sections/ComparePanelSection'; // 城市对比面板
export { CityExplorerGrid } from './sections/GridSection';           // 城市卡片网格
export { CityExplorerDetailDrawer } from './sections/DetailDrawerSection'; // 城市详情抽屉
