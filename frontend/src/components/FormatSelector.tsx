import { Card, Button } from "./ui";

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

  if (formats.length === 0) {
    return (
      <Card className="p-6 text-center">
        <div className="text-3xl mb-3">⚠️</div>
        <p className="font-medium mb-2">无法识别文件格式</p>
        <p className="text-sm mb-4" style={{ color: "var(--text-secondary)" }}>
          当前支持以下格式，请确保文件列名匹配：
        </p>
        <div className="text-sm text-left inline-block" style={{ color: "var(--text-secondary)", lineHeight: 2 }}>
          {Object.entries(SOURCE_LABELS).map(([key, label]) => (
            <div key={key}>• {label}</div>
          ))}
        </div>
        <p className="text-xs mt-4" style={{ color: "var(--text-secondary)" }}>
          也可提供标准 CSV（列名：委托时间, 证券代码, 买卖方向, 成交价格, 成交数量）
        </p>
      </Card>
    );
  }

  if (autoConfirm) {
    const label = SOURCE_LABELS[best.source_type] || best.source_type.toUpperCase();
    return (
      <Card className="text-center p-8">
        <div className="text-3xl mb-3">✅</div>
        <p className="font-medium mb-2">自动识别为：{label}</p>
        <p className="text-sm mb-4" style={{ color: "var(--text-secondary)" }}>
          置信度：{(best.score * 100).toFixed(0)}%
        </p>
        <Button onClick={() => onConfirm(best.source_type)} disabled={loading}>
          {loading ? "确认中..." : "确认格式"}
        </Button>
      </Card>
    );
  }

  return (
    <Card className="p-6">
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
                cursor: loading ? "not-allowed" : "pointer",
                textAlign: "left",
                color: "var(--text-primary)",
                opacity: loading ? 0.6 : 1,
                transition: "opacity 0.15s",
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
    </Card>
  );
}
