// 前端日志工具模块
// 提供统一的日志输出接口，支持根据环境自动调整日志级别
// 开发环境输出所有级别日志（debug 及以上），生产环境只输出 info 及以上
//
// 使用方式：
//   import { logger } from '@/utils/logger';
//   logger.debug('调试信息', extraData);   // 开发环境可见
//   logger.info('一般信息');               // 所有环境可见
//   logger.warn('警告信息');               // 所有环境可见
//   logger.error('错误信息');              // 所有环境可见
//
// 核心概念：
// - 日志级别（LogLevel）：debug < info < warn < error，级别越低越详细
// - 环境感知：生产环境自动提升日志级别，避免敏感信息泄露和性能损耗

/**
 * Frontend logging helper with environment-aware verbosity controls.
 * Use this utility instead of direct console calls in application code.
 */

/**
 * 日志工具
 * 提供统一的日志输出，支持不同环境配置不同的日志级别
 */

// 日志级别类型 —— 联合类型，限定为四个级别字符串
// type 和 interface 的区别：type 用于定义类型别名（给类型起个名字），
// interface 用于定义对象结构。type 更灵活，可以定义联合类型、交叉类型等
export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

// 获取当前应该使用的日志级别
// 根据运行环境自动决定：生产环境用 info（只显示 info/warn/error），
// 开发环境用 debug（显示所有级别），也可通过环境变量 NEXT_PUBLIC_LOG_LEVEL 覆盖
const getLogLevel = (): LogLevel => {
  // 开发环境使用 debug，生产环境使用 info
  if (process.env.NODE_ENV === 'production') {
    return 'info';
  }
  return process.env.NEXT_PUBLIC_LOG_LEVEL as LogLevel || 'debug';
};

// 日志级别映射 —— 将日志级别字符串映射为数字，用于比较大小
// 数字越大表示级别越高（越严重），只有当前日志级别 ≥ 设定级别时才输出
// 例如：当前级别为 info(1)，则 debug(0) 不输出，info(1)/warn(2)/error(3) 都输出
const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,    // 调试级别：最详细的日志，只在开发环境输出
  info: 1,     // 信息级别：一般运行信息
  warn: 2,     // 警告级别：潜在问题，不影响运行但需关注
  error: 3,    // 错误级别：严重问题，需要立即处理
};

const currentLevel = getLogLevel();  // 启动时确定日志级别，运行期间不变

// 格式化日志消息 —— 添加时间戳和级别前缀
// 输出格式：[2026-01-01T10:00:00.000Z] [INFO] 消息内容 附加数据
const formatMessage = (level: LogLevel, message: string, ...args: unknown[]): string => {
  const timestamp = new Date().toISOString();  // ISO 格式时间戳
  const prefix = `[${timestamp}] [${level.toUpperCase()}]`;  // 如 [INFO]、[ERROR]
  return args.length > 0
    ? `${prefix} ${message} ${args.map(arg => String(arg)).join(' ')}`  // 有附加数据时拼接
    : `${prefix} ${message}`;  // 无附加数据
};

// 输出日志 —— 核心日志输出函数
// 只有当日志级别 >= 当前设定级别时才输出，避免生产环境输出过多日志
const log = (level: LogLevel, message: string, ...args: unknown[]): void => {
  if (LOG_LEVELS[level] >= LOG_LEVELS[currentLevel]) {  // 级别比较：只有足够高的级别才输出
    const formattedMessage = formatMessage(level, message, ...args);
    switch (level) {
      case 'debug':
        // eslint-disable-next-line no-console
        console.debug(formattedMessage);   // 浏览器控制台显示为灰色
        break;
      case 'info':
        // eslint-disable-next-line no-console
        console.log(formattedMessage);     // 浏览器控制台默认样式
        break;
      case 'warn':
        // eslint-disable-next-line no-console
        console.warn(formattedMessage);    // 浏览器控制台显示为黄色警告
        break;
      case 'error':
        // eslint-disable-next-line no-console
        console.error(formattedMessage);   // 浏览器控制台显示为红色错误
        break;
    }
  }
};

// 日志工具导出 —— 提供四个级别的日志方法
// 应用场景：在应用代码中统一使用 logger 而非直接调用 console
export const logger = {
  debug: (message: string, ...args: unknown[]): void => log('debug', message, ...args),
  info: (message: string, ...args: unknown[]): void => log('info', message, ...args),
  warn: (message: string, ...args: unknown[]): void => log('warn', message, ...args),
  error: (message: string, ...args: unknown[]): void => log('error', message, ...args),
};

// 便捷方法 —— 直接导出各级别的日志函数，使用时更简洁
// 例如：import { logError } from '@/utils/logger'; logError('出错了');
export const logDebug = (message: string, ...args: unknown[]): void => logger.debug(message, ...args);
export const logInfo = (message: string, ...args: unknown[]): void => logger.info(message, ...args);
export const logWarn = (message: string, ...args: unknown[]): void => logger.warn(message, ...args);
export const logError = (message: string, ...args: unknown[]): void => logger.error(message, ...args);
