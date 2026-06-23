import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

interface ConfirmOptions {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "danger" | "primary";
}

interface ConfirmContextType {
  confirm: (options: ConfirmOptions) => Promise<boolean>;
}

const ConfirmContext = createContext<ConfirmContextType>({
  confirm: () => Promise.resolve(false),
});

export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [options, setOptions] = useState<(ConfirmOptions & { resolve: (v: boolean) => void }) | null>(null);

  const confirm = useCallback((opts: ConfirmOptions): Promise<boolean> => {
    return new Promise((resolve) => {
      setOptions({ ...opts, resolve });
    });
  }, []);

  const handleConfirm = () => {
    options?.resolve(true);
    setOptions(null);
  };

  const handleCancel = () => {
    options?.resolve(false);
    setOptions(null);
  };

  return (
    <ConfirmContext.Provider value={{ confirm }}>
      {children}
      {options && (
        <>
          {/* Backdrop */}
          <div
            style={{
              position: "fixed", inset: 0, zIndex: 200,
              backgroundColor: "rgba(0,0,0,0.5)",
              animation: "fadeIn 0.15s ease-out",
            }}
            onClick={handleCancel}
          />
          {/* Dialog */}
          <div
            role="dialog"
            aria-modal="true"
            style={{
              position: "fixed", top: "50%", left: "50%", transform: "translate(-50%, -50%)",
              zIndex: 201,
              backgroundColor: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              borderRadius: "16px",
              padding: "24px",
              maxWidth: 380,
              width: "90%",
              boxShadow: "0 12px 40px rgba(0,0,0,0.5)",
              animation: "scaleIn 0.15s ease-out",
            }}
          >
            <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: 8 }}>{options.title}</h2>
            <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginBottom: 20 }}>{options.message}</p>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button
                onClick={handleCancel}
                style={{
                  backgroundColor: "var(--bg-tertiary)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  padding: "8px 16px",
                  cursor: "pointer",
                  fontSize: "14px",
                }}
              >
                {options.cancelText || "取消"}
              </button>
              <button
                onClick={handleConfirm}
                style={{
                  backgroundColor: options.variant === "danger" ? "var(--danger)" : "var(--accent)",
                  color: options.variant === "danger" ? "#fff" : "#fff",
                  border: "none",
                  borderRadius: "8px",
                  padding: "8px 16px",
                  cursor: "pointer",
                  fontSize: "14px",
                  fontWeight: 500,
                }}
              >
                {options.confirmText || "确认"}
              </button>
            </div>
          </div>
          <style>{`
            @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
            @keyframes scaleIn { from { opacity: 0; transform: translate(-50%, -50%) scale(0.95); } to { opacity: 1; transform: translate(-50%, -50%) scale(1); } }
          `}</style>
        </>
      )}
    </ConfirmContext.Provider>
  );
}

export function useConfirm() {
  return useContext(ConfirmContext);
}
