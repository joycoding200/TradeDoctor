import { useParams, Link } from "react-router-dom";
import { useReport } from "../hooks/useAnalysis";
import ReactMarkdown from "react-markdown";

export default function Report() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, error } = useReport(id);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center" style={{ color: "var(--text-secondary)" }}>
          加载中...
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8 text-center">
        <h1 className="text-xl font-semibold mb-4">报告未找到</h1>
        <p className="mb-6" style={{ color: "var(--text-secondary)" }}>
          该报告不存在或已被删除
        </p>
        <Link
          to="/history"
          style={{
            backgroundColor: "var(--accent)",
            color: "#fff",
            borderRadius: "8px",
            padding: "10px 24px",
            textDecoration: "none",
          }}
          className="text-sm"
        >
          查看历史报告
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">交易行为诊断书</h1>
        <Link
          to={`/analysis/${data.analysis_id}`}
          style={{ color: "var(--accent)" }}
          className="text-sm no-underline"
        >
          返回分析面板
        </Link>
      </div>

      {data.validation_passed === false && (
        <div
          className="mb-6 p-4 rounded-lg text-sm"
          style={{
            backgroundColor: "rgba(251,191,36,0.1)",
            border: "1px solid var(--warning)",
            color: "var(--warning)",
          }}
        >
          ⚠️ 警告：数据量较少或质量较低，报告仅供参考
        </div>
      )}

      <div
        style={{
          backgroundColor: "var(--bg-secondary)",
          borderRadius: "12px",
          border: "1px solid var(--border)",
        }}
        className="p-6 md:p-8"
      >
        <div className="prose prose-invert max-w-none">
          <ReactMarkdown
            components={{
              h1: ({ children, ...props }) => (
                <h1 className="text-xl font-semibold mt-6 mb-3" style={{ color: "var(--text-primary)" }} {...props}>
                  {children}
                </h1>
              ),
              h2: ({ children, ...props }) => (
                <h2 className="text-lg font-semibold mt-5 mb-2" style={{ color: "var(--text-primary)" }} {...props}>
                  {children}
                </h2>
              ),
              h3: ({ children, ...props }) => (
                <h3 className="text-base font-semibold mt-4 mb-2" style={{ color: "var(--text-primary)" }} {...props}>
                  {children}
                </h3>
              ),
              p: ({ children, ...props }) => (
                <p className="text-sm mb-3 leading-relaxed" style={{ color: "var(--text-primary)" }} {...props}>
                  {children}
                </p>
              ),
              ul: ({ children, ...props }) => (
                <ul className="text-sm mb-3 pl-5 space-y-1" style={{ color: "var(--text-primary)" }} {...props}>
                  {children}
                </ul>
              ),
              li: ({ children, ...props }) => (
                <li className="leading-relaxed" style={{ color: "var(--text-primary)" }} {...props}>
                  {children}
                </li>
              ),
              strong: ({ children, ...props }) => (
                <strong style={{ color: "var(--accent)" }} {...props}>
                  {children}
                </strong>
              ),
              code: ({ children, ...props }) => (
                <code
                  className="text-xs px-1.5 py-0.5 rounded"
                  style={{
                    backgroundColor: "var(--bg-tertiary)",
                    color: "var(--accent)",
                  }}
                  {...props}
                >
                  {children}
                </code>
              ),
            }}
          >
            {data.content || data.report || ""}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
