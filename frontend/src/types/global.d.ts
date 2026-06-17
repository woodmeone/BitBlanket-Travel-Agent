// 【核心】项目级全局环境类型声明文件
// .d.ts 文件是 TypeScript 的"声明文件"（declaration file），
// 专门用来告诉 TypeScript 编译器某些变量/对象的类型信息，而不包含实际的运行代码。
// global.d.ts 中声明的类型在整个项目中全局可用，无需 import 导入

/**
 * Project-level global ambient type declarations.
 * Keep browser or runtime-wide type augmentations in this file.
 */

/**
 * 全局类型声明
 */

// 扩展浏览器内置的 Window 接口，增加项目自定义的环境变量
// interface Window 是浏览器全局对象，通过"声明合并"（declaration merging），
// 可以在不修改原始定义的情况下给 Window 添加新字段
// 应用场景：在 HTML 页面中通过 <script> 注入的环境变量，TypeScript 需要知道它们的类型
// 例如：window.ENV?.NEXT_PUBLIC_API_BASE 可以获取后端 API 地址
interface Window {
  ENV?: {                                // 可选的环境变量对象
    NEXT_PUBLIC_API_BASE?: string;       // Next.js 公开 API 基础地址（NEXT_PUBLIC_ 前缀的变量会暴露到浏览器端）
  };
}
