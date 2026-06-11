interface FormatOption {
  source_type: string;
  asset_type: string;
  score: number;
}

interface FormatSelectorProps {
  formats: FormatOption[];
  onConfirm: (sourceType: string) => void;
  loading?: boolean;
}

const SOURCE_LABELS: Record<string, string> = {
  qmt: "QMT (迅投)",
  vnpy: "VN.PY",
  dfcf: "东方财富",
  ths: "同花顺",
  wenhua: "文华财经",
  boyi: "博易大师",
  ctp: "CTP / 快期 / 易盛",
  huatai: "华泰涨乐",
  broker: "通用券商",
};

export default function FormatSelector({ formats, onConfirm, loading }: FormatSelectorProps) {
  const best = formats[0];
  const autoConfirm = best && best.score >= 0.7;

  if (autoConfirm) {
    const label = SOURCE_LABELS[best.source_type] || best.source_type.toUpperCase();
    return (
      <div className="text-center p-8" style={{ backgroundColor: "var(--bg-secondary)", borderRadius: "12px" }}>
        <div className="text-3xl mb-3">✅</div>
        <p className="font-medium mb-2">自动识别为：{label}</p>
        <p className="text-sm mb-4" style={{ color: "var(--text-secondary)" }}>
          置信度：{(best.score * 100).toFixed(0)}%
        </p>
        <button
          onClick={() => onConfirm(best.source_type)}
          disabled={loading}
          style={{
            backgroundColor: "var(--accent)",
            color: "#fff",
            border: "none",
            borderRadius: "8px",
            padding: "10px 24px",
            cursor: "pointer",
            opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? "确认中..." : "确认格式"}
        </button>
      </div>
    );
  }

  return (
    <div style={{ backgroundColor: "var(--bg-secondary)", borderRadius: "12px" }} className="p-6">
      <p className="font-medium mb-4">识别到多个可能的格式，请选择：</p>
      <div className="flex flex-col gap-3">
        {formats.map((f) => {
          const label = SOURCE_LABELS[f.source_type] || f.source_type.toUpperCase();
          return (
            <button
              key={f.source_type}
              onClick={() => onConfirm(f.source_type)}
              disabled={loading}
              style={{
                backgroundColor: "var(--bg-tertiary)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                padding: "12px 16px",
                cursor: "pointer",
                textAlign: "left",
                color: "var(--text-primary)",
                opacity: loading ? 0.6 : 1,
              }}
            >
              <div className="flex justify-between items-center">
                <span className="font-medium">{label}</span>
                <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
                  {(f.score * 100).toFixed(0)}%
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
