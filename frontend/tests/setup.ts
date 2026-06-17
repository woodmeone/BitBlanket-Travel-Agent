import '@testing-library/jest-dom';
import { beforeAll, afterAll, afterEach, vi } from 'vitest';

const originalGetComputedStyle = window.getComputedStyle.bind(window);
const computedStyleFallbacks: Record<string, string> = {
  lineHeight: '22px',
  fontSize: '14px',
  borderWidth: '1px',
  borderTopWidth: '1px',
  borderBottomWidth: '1px',
  paddingTop: '0px',
  paddingBottom: '0px',
  paddingLeft: '0px',
  paddingRight: '0px',
  boxSizing: 'border-box',
  width: '100px',
  fontFamily: 'sans-serif',
  fontWeight: '400',
  fontVariant: 'normal',
  textTransform: 'none',
  textIndent: '0px',
  letterSpacing: 'normal',
  wordBreak: 'normal',
  whiteSpace: 'pre-wrap',
};

// Mock window.ENV
beforeAll(() => {
  Object.defineProperty(window, 'ENV', {
    value: {
      NEXT_PUBLIC_API_BASE: 'http://localhost:8000',
    },
    writable: true,
  });
});

// Mock ResizeObserver
beforeAll(() => {
  global.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }));
});

// Mock browser APIs used by antd responsive/table internals in jsdom.
beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });

  Object.defineProperty(window, 'getComputedStyle', {
    writable: true,
    value: ((element: Element, pseudoElt?: string | null) => {
      let style: CSSStyleDeclaration;
      try {
        style = pseudoElt ? originalGetComputedStyle(element) : originalGetComputedStyle(element, pseudoElt);
      } catch {
        style = originalGetComputedStyle(element);
      }
      return new Proxy(style, {
        get(target, prop, receiver) {
          const value = Reflect.get(target, prop, receiver);
          if (typeof prop === 'string') {
            if ((value === '' || value === 'normal' || (typeof value === 'string' && value.startsWith('var('))) && computedStyleFallbacks[prop]) {
              return computedStyleFallbacks[prop];
            }
          }
          return value;
        },
      });
    }) as typeof window.getComputedStyle,
  });
});

// Clean up after each test
afterEach(() => {
  vi.clearAllMocks();
});

// Clean up after all tests
afterAll(() => {
  vi.resetAllMocks();
  Object.defineProperty(window, 'getComputedStyle', {
    writable: true,
    value: originalGetComputedStyle,
  });
});
