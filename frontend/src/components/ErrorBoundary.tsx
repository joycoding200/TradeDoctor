import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Global error boundary — catches render errors anywhere in the tree and
 * shows a themed fallback instead of a blank white screen.
 */
export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Surface to console for debugging; a real app would report to Sentry etc.
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-bg-primary p-6">
          <div className="max-w-md text-center">
            <div className="mb-4 text-5xl">😵</div>
            <h1 className="mb-3 text-2xl font-bold text-text-primary">
              页面加载异常
            </h1>
            <p className="mb-6 text-text-secondary">
              页面渲染时发生了意外错误，请刷新页面重试。
            </p>
            <button
              type="button"
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
              className="inline-flex cursor-pointer items-center justify-center rounded-lg bg-accent px-5 py-2.5 text-sm font-medium text-white transition-colors duration-150 hover:bg-accent-hover focus-ring"
            >
              刷新页面
            </button>
            <details className="mt-6 text-left">
              <summary className="cursor-pointer text-sm text-text-secondary">
                错误详情
              </summary>
              <pre className="mt-2 overflow-auto rounded-lg bg-bg-tertiary p-3 text-xs text-danger">
                {this.state.error?.message}
              </pre>
            </details>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
