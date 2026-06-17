// 'use client' 是 Next.js 的指令，表示此文件仅在浏览器端运行
'use client';

// 从 shared.ts 导入 buildEnhancedPrompt 函数和 ComparePlanCount 类型
// import { ... } from '...' 是 ES6 的模块导入语法，从指定文件中引入需要的功能
// type 关键字表示只导入类型（不导入运行时代码），用于类型注解
import { buildEnhancedPrompt, type ComparePlanCount } from './shared';

// 输入预处理所需的配置选项
// export interface 表示导出这个接口，其他文件也可以使用
export interface PrepareChatInputOptions {
  budgetUpperLimit: number | null;     // 预算上限（元），null 表示未设置
  compareModeEnabled: boolean;         // 是否开启对比模式
  comparePlanCount: ComparePlanCount;  // 对比方案的套数（2 或 3）
  selectedConstraints: string[];       // 用户选中的预设约束条件，如 ['亲子', '少走路']
}

// 【核心】预处理后的聊天输入数据
// 这里的每个字段都是 prepareChatInput 函数的输出，分别用于不同用途
export interface PreparedChatInput {
  displayMessage: string;   // 展示给用户看的消息（就是用户输入的原文）
  enrichedPrompt: string;   // 增强后的提示词（拼接了约束条件、对比要求、格式要求），会发送给 AI
  sessionName: string;      // 会话名称（取用户输入的前15个字），显示在会话列表中
  trimmed: string;          // 去除首尾空白后的用户输入
}

// 根据用户输入生成会话名称
// 取前 15 个字符，超长则加 "..." 后缀
// 应用场景：在左侧会话列表中显示，让用户快速识别每个会话
// 例如："帮我规划上海3天亲子游预算2000" → "帮我规划上海3天亲子游预算2..."
export function buildSessionName(displayMessage: string): string {
  return displayMessage.slice(0, 15) + (displayMessage.length > 15 ? '...' : '');
}

// 构建用户手动停止生成时的消息内容
// 在原始内容后追加 "⚠️ 已停止生成" 的提示
// \u26a0\ufe0f 是 ⚠️ 的 Unicode 编码，\u5df2\u505c\u6b62\u751f\u6210 是 "已停止生成"
export function buildStoppedMessageContent(content: string): string {
  return `${content || '\u5df2\u505c\u6b62\u751f\u6210'}\n\n\u26a0\ufe0f \u5df2\u505c\u6b62\u751f\u6210`;
}

// 【核心】预处理用户输入——将原始输入转化为可用的聊天数据
// 这是用户发送消息前的最后一道处理工序：
//   1. 去除首尾空白（trim）
//   2. 如果输入为空则返回 null，阻止发送空消息
//   3. 调用 buildEnhancedPrompt 将约束条件、对比模式等拼接到提示词中
//   4. 生成会话名称
// 应用场景举例：用户输入 "  帮我规划上海3天游  "（前后有空格），选中了"亲子"约束
//   → trimmed = "帮我规划上海3天游"
//   → displayMessage = "帮我规划上海3天游"（展示给用户看）
//   → enrichedPrompt = "帮我规划上海3天游\n\n约束条件：亲子\n\n请按每日行程卡输出..."（发给 AI）
//   → sessionName = "帮我规划上海3天游"
export function prepareChatInput(
  rawInput: string,
  options: PrepareChatInputOptions
): PreparedChatInput | null {
  // 去除首尾空白字符（空格、换行等）
  const trimmed = rawInput.trim();
  // 如果输入为空，返回 null，表示不发送
  if (!trimmed) return null;

  return {
    trimmed,
    displayMessage: trimmed,
    // 【核心】调用 shared.ts 中的 buildEnhancedPrompt，将用户输入与约束条件拼接成增强提示词
    enrichedPrompt: buildEnhancedPrompt(trimmed, options),
    sessionName: buildSessionName(trimmed),
  };
}
