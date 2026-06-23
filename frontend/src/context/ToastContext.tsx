import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

interface Toast {
  id: number;
  type: "success" | "error" | "warning" | "info";
  message: string;
}

interface ToastContextType {
  toasts: Toast[];
  addToast: (type: Toast["type"], message: string) => void;
  removeToast: (id: number) => void;
}

const ToastContext = createContext<ToastContextType>({
  toasts: [],
  addToast: () => {},
  removeToast: () => {},
});

let nextId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((type: Toast["type"], message: string) => {
    const id = nextId++;
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const colors: Record<Toast["type"], string> = {
    success: "var(--success)",
    error: "var(--danger)",
    warning: "var(--warning)",
    info: "var(--accent)",
  };

  const icons: Record<Toast["type"], string> = {
    success: "✓",
    error: "✗",
    warning: "⚠",
    info: "ℹ",
  };

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      {/* Toast container */}
      <div style={{ position: "fixed", top: 16, right: 16, zIndex: 100, display: "flex", flexDirection: "column", gap: 8, maxWidth: 360 }}>
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="alert"
            style={{
              backgroundColor: "var(--bg-secondary)",
              border: `1px solid ${colors[toast.type]}`,
              borderRadius: "10px",
              padding: "12px 16px",
              color: "var(--text-primary)",
              fontSize: "14px",
              display: "flex",
              alignItems: "flex-start",
              gap: 8,
              boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
              animation: "toastIn 0.2s ease-out",
              cursor: "pointer",
            }}
            onClick={() => removeToast(toast.id)}
          >
            <span style={{ color: colors[toast.type], fontWeight: 700, fontSize: 15 }}>{icons[toast.type]}</span>
            <span style={{ flex: 1 }}>{toast.message}</span>
          </div>
        ))}
      </div>
      <style>{`
        @keyframes toastIn {
          from { opacity: 0; transform: translateX(40px); }
          to   { opacity: 1; transform: translateX(0); }
        }
      `}</style>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
