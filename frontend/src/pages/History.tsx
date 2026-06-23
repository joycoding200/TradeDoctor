import { Link } from "react-router-dom";
import { listAnalyses } from "../api/analysis";
import { useQuery } from "@tanstack/react-query";
import { Card, Button, LoadingSpinner, EmptyState } from "../components/ui";

interface AnalysisItem {
  id: string;
  filename?: string;
  date_start?: string;
  date_end?: string;
  created_at?: string;
  has_snapshot?: boolean;
  has_report?: boolean;
  report_id?: string;
}

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
      <div className="max-w-3xl mx-auto px-4 py-8 text-center">
        <p style={{ color: "var(--danger)" }}>{error instanceof Error ? error.message : "加载失败"}</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-xl font-semibold mb-6">历史分析</h1>

      {analyses.length === 0 ? (
        <EmptyState
          icon="📭"
          message="暂无分析记录"
          action={
            <Link to="/upload">
              <Button>上传交割单</Button>
            </Link>
          }
        />
      ) : (
        <div className="flex flex-col gap-3">
          {analyses.map((a) => (
            <Card key={a.id} className="p-4">
              <div className="flex justify-between items-center">
                <div className="flex-1 min-w-0">
                  <Link
                    to={`/analysis/${a.id}`}
                    style={{ textDecoration: "none", color: "var(--text-primary)" }}
                    className="font-medium hover:text-[var(--accent)] transition-colors block truncate"
                  >
                    {a.filename ? `📄 ${a.filename}` : `分析 ${a.id.slice(0, 8)}`}
                  </Link>
                  <div className="text-xs mt-1" style={{ color: "var(--text-secondary)" }}>
                    {a.date_start} ~ {a.date_end}
                    {a.created_at && ` · ${new Date(a.created_at).toLocaleDateString("zh-CN")}`}
                  </div>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0 ml-3">
                  {a.has_report && a.report_id && (
                    <Link to={`/report/${a.report_id}`} className="text-xs no-underline" style={{ color: "var(--accent)" }}>
                      AI 报告 →
                    </Link>
                  )}
                  <Link to={`/analysis/${a.id}`} className="text-xs no-underline" style={{ color: "var(--accent)" }}>
                    分析面板 →
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
