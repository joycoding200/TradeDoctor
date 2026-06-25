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
        <div className="mb-3 text-3xl">⚠️</div>
        <p className="mb-2 font-medium">无法识别文件格式</p>
        <p className="mb-4 text-sm text-text-secondary">
          当前支持以下格式，请确保文件列名匹配：
        </p>
        <div className="inline-block text-left text-sm leading-8 text-text-secondary">
          {Object.entries(SOURCE_LABELS).map(([key, label]) => (
            <div key={key}>• {label}</div>
          ))}
        </div>
        <p className="mt-4 text-xs text-text-secondary">
          也可提供标准 CSV（列名：委托时间, 证券代码, 买卖方向, 成交价格, 成交数量）
        </p>
      </Card>
    );
  }

  if (autoConfirm) {
    const label = SOURCE_LABELS[best.source_type] || best.source_type.toUpperCase();
    return (
      <Card className="p-8 text-center">
        <div className="mb-3 text-3xl">✅</div>
        <p className="mb-2 font-medium">自动识别为：{label}</p>
        <p className="mb-4 text-sm text-text-secondary">
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
      <p className="mb-4 font-medium">识别到多个可能的格式，请选择：</p>
      <div className="flex flex-col gap-3">
        {formats.map((f) => {
          const label = SOURCE_LABELS[f.source_type] || f.source_type.toUpperCase();
          return (
            <button
              key={f.source_type}
              type="button"
              onClick={() => onConfirm(f.source_type)}
              disabled={loading}
              className="cursor-pointer rounded-lg border border-border bg-bg-tertiary px-4 py-3 text-left text-text-primary opacity-100 transition-opacity duration-150 hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60 focus-ring"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">{label}</span>
                <span className="text-sm text-text-secondary">
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
