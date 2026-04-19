import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

/**
 * Prevents a single render failure from blanking the entire SPA; logs without echoing internals to UI.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('UI error boundary:', error.message, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-neutral-950 text-white p-8">
          <div className="max-w-md text-center space-y-4">
            <h1 className="text-xl font-semibold">Something went wrong</h1>
            <p className="text-white/60 text-sm">
              The interface hit an unexpected error. Reload the page to continue. If the problem
              persists, sign out and sign in again.
            </p>
            <button
              type="button"
              className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400"
              onClick={() => window.location.reload()}
            >
              Reload
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
