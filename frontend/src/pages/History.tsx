import { Link } from "react-router-dom";
import { listAnalyses } from "../api/analysis";
import { useQuery } from "@tanstack/react-query";
import { Card, Button, LoadingSpinner, EmptyState } from "../components/ui";

/* ─── Inline SVG icons ───────────────────────────────────────────────────── */
const DocIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-accent">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="8" y1="13" x2="16" y2="13" />
    <line x1="8" y1="17" x2="13" y2="17" />
  </svg>
);

const FilesIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
  </svg>
);

const CalendarIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
    <line x1="16" y1="2" x2="16" y2="6" />
    <line x1="8" y1="2" x2="8" y2="6" />
    <line x1="3" y1="10" x2="21" y2="10" />
  </svg>
);

const ArrowRightIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="5" y1="12" x2="19" y2="12" />
    <polyline points="12 5 19 12 12 19" />
  </svg>
);

const ReportIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2l2.4 7.2h7.6l-6 4.8 2.4 7.2-6.4-4.8-6.4 4.8 2.4-7.2-6-4.8h7.6z" />
  </svg>
);

const EmptyIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" className="text-text-secondary">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="12" y1="18" x2="12" y2="12" />
    <line x1="9" y1="15" x2="15" y2="15" />
  </svg>
);

/* ─── Types ───────────────────────────────────────────────────────────────── */
interface AnalysisItem {
  id: string;
  filename?: string;
  filenames?: string[];
  date_start?: string;
  date_end?: string;
  created_at?: string;
  has_snapshot?: boolean;
  has_report?: boolean;
  report_id?: string;
}

/* ═══════════════════════════════════════════════════════════════════════════ */
export default function History() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["analyses"],
    queryFn: listAnalyses,
  });

  const analyses: AnalysisItem[] = data?.analyses || [];

  if (isLoading) {
    return <LoadingSpinner text="加载历史记录..." />;
  }

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-danger/10">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-danger">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        <p className="text-danger">{error instanceof Error ? error.message : "加载失败"}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:py-12">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-extrabold tracking-tight text-text-primary">
          历史分析
        </h1>
        <p className="mt-1.5 text-sm text-text-secondary">
          查看和管理你所有的交易分析记录
        </p>
      </div>

      {analyses.length === 0 ? (
        <EmptyState
          icon={<EmptyIcon />}
          message="暂无分析记录"
          action={
            <Link to="/upload">
              <Button className="shadow-lg shadow-accent/25">上传交割单</Button>
            </Link>
          }
        />
      ) : (
        <div className="flex flex-col gap-3">
          {analyses.map((a) => (
            <Card
              key={a.id}
              className="group p-5 transition-all duration-300 hover:-translate-y-0.5 hover:border-accent/30 hover:shadow-lg hover:shadow-accent/5"
            >
              <div className="flex items-center justify-between gap-4">
                {/* Left: file info */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="flex-shrink-0">
                      <DocIcon />
                    </span>
                    <Link
                      to={`/analysis/${a.id}`}
                      className="truncate text-[15px] font-semibold text-text-primary no-underline transition-colors hover:text-accent"
                    >
                      {a.filename || `分析 ${a.id.slice(0, 8)}`}
                    </Link>
                  </div>

                  {/* Sub info row */}
                  <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 pl-7">
                    {/* Date range */}
                    {a.date_start && (
                      <span className="inline-flex items-center gap-1 text-xs text-text-secondary">
                        <CalendarIcon />
                        {a.date_start}{a.date_end ? ` ~ ${a.date_end}` : ""}
                      </span>
                    )}

                    {/* Created date */}
                    {a.created_at && (
                      <span className="text-xs text-text-secondary">
                        {new Date(a.created_at).toLocaleDateString("zh-CN", {
                          year: "numeric",
                          month: "long",
                          day: "numeric",
                        })}
                      </span>
                    )}

                    {/* File count */}
                    {a.filenames && a.filenames.length > 1 && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-bg-tertiary px-2 py-0.5 text-xs text-text-secondary">
                        <FilesIcon />
                        {a.filenames.length} 个文件
                      </span>
                    )}
                  </div>
                </div>

                {/* Right: action links */}
                <div className="flex flex-shrink-0 items-center gap-1">
                  {a.has_report && a.report_id && (
                    <Link
                      to={`/report/${a.report_id}`}
                      className="inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium text-accent no-underline transition-colors hover:bg-accent/10"
                    >
                      <ReportIcon />
                      AI 报告
                      <ArrowRightIcon />
                    </Link>
                  )}
                  <Link
                    to={`/analysis/${a.id}`}
                    className="inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium text-text-secondary no-underline transition-colors hover:bg-bg-tertiary hover:text-text-primary"
                  >
                    分析面板
                    <ArrowRightIcon />
                  </Link>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
