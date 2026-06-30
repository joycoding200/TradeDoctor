import "@testing-library/jest-dom/vitest";

// jsdom doesn't implement matchMedia (used by BackToTop's scroll listener
// isn't needed, but ResponsiveContainer / other libs may touch it).
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// jsdom lacks ResizeObserver (Recharts ResponsiveContainer uses it).
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = ResizeObserverMock as any;
