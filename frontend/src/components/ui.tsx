import { useState, type ReactNode, type ButtonHTMLAttributes, type InputHTMLAttributes, type CSSProperties } from "react";

// ─── Card ───────────────────────────────────────────────────────────────────
const cardStyle: CSSProperties = {
  backgroundColor: "var(--bg-secondary)",
  borderRadius: "12px",
  border: "1px solid var(--border)",
};

export function Card({ children, className = "", style }: { children: ReactNode; className?: string; style?: CSSProperties }) {
  return (
    <div style={{ ...cardStyle, ...style }} className={className}>
      {children}
    </div>
  );
}

// ─── Button ──────────────────────────────────────────────────────────────────
type ButtonVariant = "primary" | "success" | "danger" | "ghost" | "outline";

const variantStyles: Record<ButtonVariant, CSSProperties> = {
  primary: { backgroundColor: "var(--accent)", color: "#fff", border: "none" },
  success: { backgroundColor: "var(--success)", color: "#000", border: "none" },
  danger:  { backgroundColor: "var(--danger)", color: "#fff", border: "none" },
  ghost:   { backgroundColor: "transparent", color: "var(--text-primary)", border: "none" },
  outline: { backgroundColor: "var(--bg-tertiary)", color: "var(--text-primary)", border: "1px solid var(--border)" },
};

const btnBase: CSSProperties = {
  borderRadius: "8px",
  padding: "10px 20px",
  cursor: "pointer",
  fontSize: "14px",
  fontWeight: 500,
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  gap: "6px",
  transition: "opacity 0.15s",
};

export function Button({
  variant = "primary",
  children,
  className = "",
  style,
  disabled,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      {...rest}
      disabled={disabled}
      style={{
        ...btnBase,
        ...variantStyles[variant],
        opacity: disabled ? 0.5 : 1,
        cursor: disabled ? "not-allowed" : "pointer",
        ...style,
      }}
      className={className}
    >
      {children}
    </button>
  );
}

// ─── Input ───────────────────────────────────────────────────────────────────
const inputBase: CSSProperties = {
  backgroundColor: "var(--bg-tertiary)",
  border: "1px solid var(--border)",
  borderRadius: "8px",
  color: "var(--text-primary)",
  padding: "12px 16px",
  fontSize: "14px",
  outline: "none",
  width: "100%",
  transition: "border-color 0.15s",
};

export function Input({
  className = "",
  style,
  ...rest
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...rest}
      style={{ ...inputBase, ...style }}
      className={`${className} focus:ring-1 focus:ring-[var(--accent)] focus:border-[var(--accent)]`}
    />
  );
}

// ─── LoadingSpinner ──────────────────────────────────────────────────────────
export function LoadingSpinner({ text = "加载中...", className = "" }: { text?: string; className?: string }) {
  return (
    <div className={`flex flex-col items-center justify-center py-8 gap-3 ${className}`}>
      <div
        className="animate-spin w-6 h-6 border-2 rounded-full"
        style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
      />
      <span className="text-sm" style={{ color: "var(--text-secondary)" }}>{text}</span>
    </div>
  );
}

// ─── InlineSpinner ──────────────────────────────────────────────────────────
export function InlineSpinner() {
  return (
    <span
      className="inline-block w-4 h-4 border-2 border-t-transparent rounded-full animate-spin align-middle"
      style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
    />
  );
}

// ─── ErrorBox ───────────────────────────────────────────────────────────────
export function ErrorBox({ message, className = "" }: { message: string; className?: string }) {
  return (
    <div
      className={`text-center py-8 ${className}`}
      style={{ color: "var(--danger)" }}
    >
      {message}
    </div>
  );
}

// ─── Collapsible ───────────────────────────────────────────────────────────
export function Collapsible({ title, children, defaultOpen = false }: { title: string; children: ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        style={{
          backgroundColor: "transparent", border: "none", cursor: "pointer",
          color: "var(--text-secondary)", fontSize: "13px", fontWeight: 500,
          padding: 0, marginBottom: open ? 12 : 0,
          transition: "margin-bottom 0.2s",
        }}
      >
        {open ? "▾ " : "▸ "}{title}
      </button>
      <div
        style={{
          display: open ? "block" : "none",
          overflow: "hidden",
          maxHeight: open ? 2000 : 0,
          transition: open ? "max-height 0.3s ease-in" : undefined,
        }}
      >
        {children}
      </div>
    </div>
  );
}

// ─── EmptyState ─────────────────────────────────────────────────────────────
export function EmptyState({ icon = "📭", message, action }: { icon?: string; message: string; action?: ReactNode }) {
  return (
    <div className="text-center py-12">
      <div className="text-3xl mb-3">{icon}</div>
      <p className="mb-4" style={{ color: "var(--text-secondary)" }}>{message}</p>
      {action}
    </div>
  );
}
