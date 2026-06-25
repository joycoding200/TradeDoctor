import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useRef,
  type ReactNode,
} from "react";

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
  const [options, setOptions] = useState<
    (ConfirmOptions & { resolve: (v: boolean) => void }) | null
  >(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const confirmBtnRef = useRef<HTMLButtonElement>(null);
  // Element that had focus before the dialog opened — restored on close.
  const previouslyFocused = useRef<HTMLElement | null>(null);

  const confirm = useCallback((opts: ConfirmOptions): Promise<boolean> => {
    return new Promise((resolve) => {
      setOptions({ ...opts, resolve });
    });
  }, []);

  const close = useCallback(
    (result: boolean) => {
      options?.resolve(result);
      setOptions(null);
    },
    [options]
  );

  // While open: trap focus + handle ESC + autofocus the confirm button
  useEffect(() => {
    if (!options) return;

    previouslyFocused.current = document.activeElement as HTMLElement;
    confirmBtnRef.current?.focus();

    const dialog = dialogRef.current;
    if (!dialog) return;

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        close(false);
        return;
      }
      if (e.key === "Tab") {
        const focusables = dialog.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusables.length === 0) return;
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    document.addEventListener("keydown", onKeyDown);
    // Prevent body scroll while modal is open
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = prevOverflow;
      previouslyFocused.current?.focus();
    };
  }, [options, close]);

  return (
    <ConfirmContext.Provider value={{ confirm }}>
      {children}
      {options && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-[200] animate-fade-in bg-black/50"
            onClick={() => close(false)}
          />
          {/* Dialog */}
          <div
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirm-title"
            aria-describedby="confirm-desc"
            className="fixed left-1/2 top-1/2 z-[201] w-[90%] max-w-[380px] animate-scale-in rounded-2xl border border-border bg-bg-secondary p-6 shadow-[0_12px_40px_rgba(0,0,0,0.5)]"
            style={{ transform: "translate(-50%, -50%)" }}
          >
            <h2
              id="confirm-title"
              className="mb-2 text-base font-semibold text-text-primary"
            >
              {options.title}
            </h2>
            <p
              id="confirm-desc"
              className="mb-5 text-sm text-text-secondary"
            >
              {options.message}
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => close(false)}
                className="cursor-pointer rounded-lg border border-border bg-bg-tertiary px-4 py-2 text-sm text-text-primary transition-colors hover:brightness-125 focus-ring"
              >
                {options.cancelText || "取消"}
              </button>
              <button
                ref={confirmBtnRef}
                type="button"
                onClick={() => close(true)}
                className={[
                  "cursor-pointer rounded-lg border-0 px-4 py-2 text-sm font-medium text-white transition-colors focus-ring",
                  options.variant === "danger"
                    ? "bg-danger hover:brightness-110"
                    : "bg-accent hover:bg-accent-hover",
                ].join(" ")}
              >
                {options.confirmText || "确认"}
              </button>
            </div>
          </div>
        </>
      )}
    </ConfirmContext.Provider>
  );
}

export function useConfirm() {
  return useContext(ConfirmContext);
}
