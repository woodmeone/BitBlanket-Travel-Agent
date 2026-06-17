import { describe, expect, it, vi } from 'vitest';
import { logger } from '@/utils/logger';

describe('logger', () => {
  it('logs all levels without throwing', () => {
    const debugSpy = vi.spyOn(console, 'debug').mockImplementation(() => {});
    const logSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => logger.debug('debug message')).not.toThrow();
    expect(() => logger.info('info message')).not.toThrow();
    expect(() => logger.warn('warn message')).not.toThrow();
    expect(() => logger.error('error message')).not.toThrow();

    expect(debugSpy.mock.calls.length + logSpy.mock.calls.length + warnSpy.mock.calls.length + errorSpy.mock.calls.length).toBeGreaterThan(0);
  });
});
