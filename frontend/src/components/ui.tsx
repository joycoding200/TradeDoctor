import { useState, type ReactNode, type ButtonHTMLAttributes, type InputHTMLAttributes } from "react";

/* ═══════════════════════════════════════════════════════════════════════════
 * ui.tsx — Shared UI primitives
 *
 * All styling uses Tailwind utility classes backed by the design tokens
 * declared in index.css (`@theme`). No inline `style={{}}` here, which means:
 *  - hover/active/focus pseudo-states work properly
 *  - `prefers-reduced-motion` is respected
 *  - the markup is purge-friendly (classes survive Tailwind's JIT)
 * ═══════════════════════════════════════════════════════════════════════════ */

// ─── Card ───────────────────────────────────────────────────────────────────
export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-xl border border-border bg-bg-secondary ${className}`}
    >
      {children}
    </div>
  );
}

// ─── Button ──────────────────────────────────────────────────────────────────
type ButtonVariant = "primary" | "success" | "danger" | "ghost" | "outline";

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary:
    "bg-accent text-white hover:bg-accent-hover active:scale-[0.97] disabled:hover:bg-accent",
  success:
    "bg-success text-black hover:brightness-110 active:scale-[0.97]",
  danger:
    "bg-danger text-white hover:brightness-110 active:scale-[0.97]",
  ghost:
    "bg-transparent text-text-primary hover:bg-bg-tertiary",
  outline:
    "bg-bg-tertiary text-text-primary border border-border hover:border-accent hover:text-accent",
};

export function Button({
  variant = "primary",
  children,
  className = "",
  disabled,
  type = "button",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      {...rest}
      type={type}
      disabled={disabled}
      className={[
        "inline-flex items-center justify-center gap-1.5",
        "rounded-lg px-5 py-2.5 text-sm font-medium",
        "transition-[transform,background-color,color,border-color,filter] duration-150 ease-out",
        "cursor-pointer select-none focus-ring",
        disabled ? "opacity-50 cursor-not-allowed" : "",
        VARIANT_CLASS[variant],
        className,
      ].join(" ")}
    >
      {children}
    </button>
  );
}

// ─── Input ───────────────────────────────────────────────────────────────────
export function Input({
  className = "",
  ...rest
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...rest}
      className={[
        "w-full rounded-lg border border-border bg-bg-tertiary",
        "px-4 py-3 text-sm text-text-primary",
        "placeholder:text-text-secondary",
        "outline-none transition-[border-color,box-shadow] duration-150",
        "focus:border-accent focus:ring-1 focus:ring-accent",
        className,
      ].join(" ")}
    />
  );
}

// ─── LoadingSpinner ──────────────────────────────────────────────────────────
export function LoadingSpinner({
  text = "加载中...",
  className = "",
}: {
  text?: string;
  className?: string;
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 py-8 ${className}`}
    >
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      <span className="text-sm text-text-secondary">{text}</span>
    </div>
  );
}

// ─── InlineSpinner ──────────────────────────────────────────────────────────
export function InlineSpinner() {
  return (
    <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent align-middle" />
  );
}

// ─── ErrorBox ───────────────────────────────────────────────────────────────
export function ErrorBox({
  message,
  className = "",
}: {
  message: string;
  className?: string;
}) {
  return (
    <div className={`py-8 text-center text-danger ${className}`}>
      <p>{message}</p>
    </div>
  );
}

// ─── Collapsible ────────────────────────────────────────────────────────────
/* Uses the `.collapsible-content` CSS grid trick (see index.css) so the open
 * AND close transitions animate the real content height — no fixed
 * `maxHeight` guesswork. */
export function Collapsible({
  title,
  children,
  defaultOpen = false,
}: {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className={`mb-0 border-0 bg-transparent p-0 text-[13px] font-medium text-text-secondary transition-[margin] duration-200 hover:text-text-primary focus-ring ${open ? "mb-3" : ""}`}
      >
        {open ? "▾ " : "▸ "}
        {title}
      </button>
      <div className="collapsible-content" data-open={open}>
        <div>{children}</div>
      </div>
    </div>
  );
}

// ─── EmptyState ─────────────────────────────────────────────────────────────
export function EmptyState({
  icon,
  message,
  action,
}: {
  icon?: ReactNode;
  message: string;
  action?: ReactNode;
}) {
  return (
    <div className="py-12 text-center">
      <div className="mb-3 text-3xl">{icon}</div>
      <p className="mb-4 text-text-secondary">{message}</p>
      {action}
    </div>
  );
}
