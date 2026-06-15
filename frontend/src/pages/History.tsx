import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listAnalyses } from "../api/analysis";

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
  const [analyses, setAnalyses] = useState<AnalysisItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    listAnalyses()
      .then((data) => setAnalyses(data.analyses || []))
      .catch((err) => setError(err instanceof Error ? err.message : "加载失败"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div style={{ color: "var(--text-secondary)" }}>加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8 text-center">
        <p style={{ color: "var(--danger)" }}>{error}</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-xl font-semibold mb-6">历史分析</h1>

      {analyses.length === 0 ? (
        <div className="text-center py-12">
          <p className="mb-4" style={{ color: "var(--text-secondary)" }}>暂无分析记录</p>
          <Link to="/upload" style={{ backgroundColor: "var(--accent)", color: "#fff", borderRadius: "8px", padding: "10px 24px", textDecoration: "none" }} className="text-sm">
            上传交割单
          </Link>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {analyses.map((a) => (
            <div key={a.id}
              style={{ backgroundColor: "var(--bg-secondary)", border: "1px solid var(--border)", borderRadius: "12px" }}
              className="p-4"
            >
              <div className="flex justify-between items-center">
                <div className="flex-1">
                  <Link to={`/analysis/${a.id}`}
                    style={{ textDecoration: "none", color: "var(--text-primary)" }}
                    className="font-medium hover:text-[var(--accent)] transition-colors"
                  >
                    {a.filename ? `📄 ${a.filename}` : `分析 ${a.id.slice(0, 8)}`}
                  </Link>
                  <div className="text-xs mt-1" style={{ color: "var(--text-secondary)" }}>
                    {a.date_start} ~ {a.date_end}
                    {a.created_at && ` · ${new Date(a.created_at).toLocaleDateString("zh-CN")}`}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {a.has_report && a.report_id && (
                    <Link to={`/report/${a.report_id}`}
                      style={{ color: "var(--accent)", textDecoration: "none", fontSize: 13 }}
                    >
                      AI 报告 →
                    </Link>
                  )}
                  <Link to={`/analysis/${a.id}`}
                    style={{ color: "var(--accent)", textDecoration: "none", fontSize: 13 }}
                  >
                    分析面板 →
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
