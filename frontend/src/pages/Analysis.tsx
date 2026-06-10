import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useStats, useInsight, useWhatIf, useRunAnalysis, useGenerateReport } from "../hooks/useAnalysis";
import StatsCards from "../components/StatsCards";
import PatternChart from "../components/PatternChart";
import WhatIfChart from "../components/WhatIfChart";

type Tab = "stats" | "insight" | "whatif";

export default function Analysis() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>("stats");

  const runAnalysis = useRunAnalysis();
  const stats = useStats(id);
  const insight = useInsight(id);
  const whatIf = useWhatIf(id);
  const genReport = useGenerateReport();

  const handleRunAnalysis = () => {
    runAnalysis.mutate(
      {},
      {
        onSuccess: (data) => {
          navigate(`/analysis/${data.id}`, { replace: true });
        },
      }
    );
  };

  const handleGenerateReport = () => {
    if (!id) return;
    genReport.mutate(id, {
      onSuccess: (data) => {
        navigate(`/report/${data.id}`);
      },
    });
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: "stats", label: "统计概览" },
    { key: "insight", label: "归因分析" },
    { key: "whatif", label: "What If 回测" },
  ];

  const isLoading = runAnalysis.isPending;

  if (!id) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 text-center">
        <h1 className="text-xl font-semibold mb-4">分析面板</h1>
        <p className="mb-6" style={{ color: "var(--text-secondary)" }}>
          请先上传并导入交易数据
        </p>
        <button
          onClick={() => navigate("/upload")}
          style={{
            backgroundColor: "var(--accent)",
            color: "#fff",
            border: "none",
            borderRadius: "8px",
            padding: "10px 24px",
            cursor: "pointer",
          }}
        >
          上传交割单
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">分析面板</h1>
        <div className="flex gap-3">
          <button
            onClick={handleRunAnalysis}
            disabled={isLoading}
            style={{
              backgroundColor: "var(--accent)",
              color: "#fff",
              border: "none",
              borderRadius: "8px",
              padding: "8px 20px",
              cursor: isLoading ? "not-allowed" : "pointer",
              opacity: isLoading ? 0.6 : 1,
            }}
            className="text-sm"
          >
            {isLoading ? "分析中..." : "运行分析"}
          </button>
          <button
            onClick={handleGenerateReport}
            disabled={genReport.isPending}
            style={{
              backgroundColor: "var(--success)",
              color: "#000",
              border: "none",
              borderRadius: "8px",
              padding: "8px 20px",
              cursor: genReport.isPending ? "not-allowed" : "pointer",
              opacity: genReport.isPending ? 0.6 : 1,
            }}
            className="text-sm font-medium"
          >
            {genReport.isPending ? "生成中..." : "生成 AI 报告"}
          </button>
        </div>
      </div>

      <div className="flex gap-1 mb-6" style={{ borderBottom: "1px solid var(--border)" }}>
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              backgroundColor: "transparent",
              border: "none",
              borderBottom: activeTab === tab.key ? "2px solid var(--accent)" : "2px solid transparent",
              color:
                activeTab === tab.key ? "var(--accent)" : "var(--text-secondary)",
              padding: "10px 16px",
              cursor: "pointer",
              marginBottom: "-1px",
            }}
            className="text-sm font-medium"
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "stats" && (
        <>
          {stats.isLoading && (
            <div className="text-center py-8" style={{ color: "var(--text-secondary)" }}>
              加载中...
            </div>
          )}
          {stats.error && (
            <div className="text-center py-8" style={{ color: "var(--danger)" }}>
              加载失败，请点击"运行分析"
            </div>
          )}
          {stats.data && <StatsCards stats={stats.data} />}
        </>
      )}

      {activeTab === "insight" && (
        <div className="space-y-6">
          {insight.isLoading && (
            <div className="text-center py-8" style={{ color: "var(--text-secondary)" }}>
              加载中...
            </div>
          )}
          {insight.error && (
            <div className="text-center py-8" style={{ color: "var(--danger)" }}>
              请先运行分析
            </div>
          )}
          {insight.data && (
            <>
              <div>
                <h2 className="text-sm font-medium mb-3" style={{ color: "var(--text-secondary)" }}>
                  最佳模式
                </h2>
                <div
                  style={{
                    backgroundColor: "var(--bg-secondary)",
                    borderRadius: "12px",
                    border: "1px solid var(--border)",
                  }}
                  className="p-4"
                >
                  <pre className="text-sm m-0 whitespace-pre-wrap font-sans">
                    {JSON.stringify(insight.data.best_pattern, null, 2)}
                  </pre>
                </div>
              </div>
              <div>
                <h2 className="text-sm font-medium mb-3" style={{ color: "var(--text-secondary)" }}>
                  最差模式
                </h2>
                <div
                  style={{
                    backgroundColor: "var(--bg-secondary)",
                    borderRadius: "12px",
                    border: "1px solid var(--border)",
                  }}
                  className="p-4"
                >
                  <pre className="text-sm m-0 whitespace-pre-wrap font-sans">
                    {JSON.stringify(insight.data.worst_pattern, null, 2)}
                  </pre>
                </div>
              </div>
              {insight.data.pattern_breakdown && (
                <PatternChart data={insight.data.pattern_breakdown} />
              )}
            </>
          )}
        </div>
      )}

      {activeTab === "whatif" && (
        <>
          {whatIf.isLoading && (
            <div className="text-center py-8" style={{ color: "var(--text-secondary)" }}>
              加载中...
            </div>
          )}
          {whatIf.error && (
            <div className="text-center py-8" style={{ color: "var(--danger)" }}>
              请先运行分析
            </div>
          )}
          {whatIf.data && (
            <>
              {whatIf.data.total && (
                <div
                  style={{
                    backgroundColor: "var(--bg-secondary)",
                    borderRadius: "12px",
                    border: "1px solid var(--border)",
                  }}
                  className="p-4 mb-6"
                >
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-xs" style={{ color: "var(--text-secondary)" }}>
                        原始总收益
                      </div>
                      <div className="text-lg font-semibold" style={{ color: "var(--success)" }}>
                        {whatIf.data.total.original_return?.toFixed(2)}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs" style={{ color: "var(--text-secondary)" }}>
                        删除后总收益
                      </div>
                      <div className="text-lg font-semibold" style={{ color: "var(--warning)" }}>
                        {whatIf.data.total.whatif_return?.toFixed(2)}
                      </div>
                    </div>
                  </div>
                </div>
              )}
              {whatIf.data.breakdown && <WhatIfChart data={whatIf.data.breakdown} />}
            </>
          )}
        </>
      )}
    </div>
  );
}
