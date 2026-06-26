/* ─── Step derivation from statusText ──────────────────────────────────────── */
export function deriveStep(statusText: string): number {
  if (!statusText) return 0;
  if (statusText.includes("上传")) return 1;
  if (statusText.includes("解析")) return 2;
  if (statusText.includes("导入")) return 3;
  if (statusText.includes("分析") || statusText.includes("添加")) return 4;
  return 0;
}

const STEPS = [
  { step: 1, label: "上传" },
  { step: 2, label: "解析" },
  { step: 3, label: "导入" },
  { step: 4, label: "分析" },
];

/* ─── SVG icons ───────────────────────────────────────────────────────────── */
const CheckCircleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-success">
    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
    <polyline points="22 4 12 14.01 9 11.01" />
  </svg>
);

/* ─── Component ───────────────────────────────────────────────────────────── */
interface UploadProgressProps {
  currentStep: number;
  statusText: string;
}

export default function UploadProgress({ currentStep, statusText }: UploadProgressProps) {
  return (
    <div className="mt-8">
      {/* Status text */}
      <p className="mb-5 text-center text-sm font-medium text-text-primary">
        {statusText}
      </p>

      {/* Timeline — horizontal on sm+, vertical on mobile */}
      <div className="flex flex-col items-center gap-0 sm:flex-row sm:justify-center sm:gap-0">
        {STEPS.map(({ step, label }, i) => {
          const isCompleted = step < currentStep;
          const isActive = step === currentStep;

          return (
            <div key={step} className="flex flex-col items-center sm:flex-row">
              {/* Step node */}
              <div className="flex flex-col items-center">
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition-colors duration-300 ${
                    isCompleted
                      ? "bg-success/15 text-success"
                      : isActive
                        ? "bg-accent/15 text-accent animate-pulse-dot"
                        : "bg-bg-tertiary text-text-secondary"
                  }`}
                  aria-current={isActive ? "step" : undefined}
                >
                  {isCompleted ? (
                    <CheckCircleIcon />
                  ) : (
                    step
                  )}
                </div>
                <span
                  className={`mt-1.5 text-[11px] font-medium ${
                    isCompleted
                      ? "text-success"
                      : isActive
                        ? "text-accent"
                        : "text-text-secondary"
                  }`}
                >
                  {label}
                </span>
              </div>

              {/* Connector line */}
              {i < STEPS.length - 1 && (
                <>
                  {/* Vertical connector (mobile) */}
                  <div className="my-1 h-6 w-px sm:hidden">
                    <div
                      className={`h-full w-full transition-colors duration-300 ${
                        isCompleted ? "bg-success/30" : "bg-border"
                      }`}
                    />
                  </div>
                  {/* Horizontal connector (desktop) */}
                  <div className="mx-2 hidden h-px w-8 sm:block md:w-12">
                    <div
                      className={`h-full w-full transition-colors duration-300 ${
                        isCompleted ? "bg-success/30" : "bg-border"
                      }`}
                    />
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
