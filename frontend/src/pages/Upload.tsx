import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import FileDropzone from "../components/FileDropzone";
import FormatSelector from "../components/FormatSelector";
import UploadProgress, { deriveStep } from "../components/UploadProgress";
import { uploadFile, confirmFormat, importTrades } from "../api/upload";
import { runAnalysis, linkFilesToAnalysis } from "../api/analysis";
import { useToast } from "../context/ToastContext";
import { Card } from "../components/ui";

interface FormatOption {
  source_type: string;
  asset_type: string;
  score: number;
}

/* ─── Inline icons ────────────────────────────────────────────────────────── */
const CheckIconSmall = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="mt-px shrink-0 text-success">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

const BulbIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 text-amber-500">
    <path d="M9 18h6" />
    <path d="M10 22h4" />
    <path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14" />
  </svg>
);

/* ═══════════════════════════════════════════════════════════════════════════ */
export default function Upload() {
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState("");
  const [rawFileId, setRawFileId] = useState<string>("");
  const [fileName, setFileName] = useState<string>("");
  const [formats, setFormats] = useState<FormatOption[]>([]);
  const navigate = useNavigate();
  const toast = useToast();
  const [searchParams] = useSearchParams();
  const attachToAnalysisId = searchParams.get("attach_to");

  // Show a patience toast when analysis takes longer than expected
  useEffect(() => {
    if (!loading || !statusText.includes("分析")) return;
    const timer = setTimeout(() => {
      toast.addToast("info", "数据量较大，分析需要一些时间，请耐心等待...");
    }, 15_000);
    return () => clearTimeout(timer);
  }, [loading, statusText, toast]);

  const autoProcess = async (fileId: string, sourceType: string, fName: string) => {
    setStatusText("正在解析交易记录...");
    const confirmed = await confirmFormat(fileId, sourceType);
    const trades = confirmed.trades || [];

    setStatusText("正在导入交易记录...");
    const importResult = await importTrades(fileId);
    const { imported_count, skipped_count } = importResult;

    if (skipped_count > 0) {
      if (imported_count === 0) {
        toast.addToast("info", "所有交易记录已存在，无需重复导入");
      } else {
        toast.addToast(
          "info",
          `已导入 ${imported_count} 笔交易，跳过 ${skipped_count} 笔重复记录`
        );
      }
    }

    if (attachToAnalysisId) {
      setStatusText("正在添加到分析...");
      await linkFilesToAnalysis(attachToAnalysisId, [fileId]);
      toast.addToast("success", "文件已添加到分析");
      navigate(`/analysis/${attachToAnalysisId}`);
    } else {
      setStatusText("正在运行分析...");
      const dates = trades
        .map((t: any) => t.datetime)
        .filter(Boolean)
        .sort();
      const today = new Date().toISOString().split("T")[0];
      const dateStart = dates[0]?.split("T")[0] || "2020-01-01";
      const dateEnd = dates[dates.length - 1]?.split("T")[0] || today;
      const analysis = await runAnalysis(dateStart, dateEnd, fileId, fName);
      toast.addToast("success", "分析完成");
      navigate(`/analysis/${analysis.analysis_id}`);
    }
  };

  const handleFile = async (file: File) => {
    setLoading(true);
    setStatusText("正在上传文件...");
    try {
      const result = await uploadFile(file);
      const detectedFormats = result.detected_formats || [];
      setRawFileId(result.raw_file_id);
      setFileName(file.name);
      setFormats(detectedFormats);

      if (detectedFormats.length > 0 && detectedFormats[0].score >= 0.7) {
        await autoProcess(result.raw_file_id, detectedFormats[0].source_type, file.name);
      } else if (detectedFormats.length > 0) {
        setLoading(false);
        setStatusText("");
      } else {
        setLoading(false);
        toast.addToast("warning", "无法识别文件格式，请确认文件内容正确");
      }
    } catch (err) {
      setLoading(false);
      toast.addToast("error", err instanceof Error ? err.message : "上传失败");
    }
  };

  const handleConfirm = async (sourceType: string) => {
    setLoading(true);
    try {
      await autoProcess(rawFileId, sourceType, fileName);
    } catch (err) {
      setLoading(false);
      toast.addToast("error", err instanceof Error ? err.message : "处理失败");
    }
  };

  const pageTitle = attachToAnalysisId ? "添加交割单" : "上传交割单";

  const showTips = !loading && formats.length === 0 && !rawFileId;

  // Format selector view
  if (formats.length > 0 && formats[0].score < 0.7) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8 sm:py-12">
        <h1 className="mb-1 text-xl font-semibold">{pageTitle}</h1>
        <p className="mb-6 text-sm text-text-secondary">
          {attachToAnalysisId
            ? "选择交割单文件添加到现有分析中"
            : "上传券商交割单，自动分析您的交易行为"}
        </p>
        <FormatSelector formats={formats} onConfirm={handleConfirm} loading={loading} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:py-12">
      {/* Header */}
      <h1 className="mb-1 text-xl font-semibold">{pageTitle}</h1>
      <p className="mb-8 text-sm text-text-secondary">
        {attachToAnalysisId
          ? "选择交割单文件添加到现有分析中"
          : "上传券商交割单，自动分析您的交易行为"}
      </p>

      {/* Dropzone */}
      <FileDropzone onFile={handleFile} loading={loading} />

      {/* Progress timeline */}
      {loading && statusText && (
        <UploadProgress
          currentStep={deriveStep(statusText)}
          statusText={statusText}
        />
      )}

      {/* Tips card */}
      {showTips && (
        <>
          <hr className="my-8 border-border/50" />
          <Card className="p-5 text-left">
            <div className="flex items-start gap-3">
              <span className="mt-0.5">
                <BulbIcon />
              </span>
              <div className="min-w-0">
                <p className="mb-3 text-sm font-medium text-text-primary">
                  使用提示
                </p>
                <ul className="space-y-2">
                  {[
                    "支持 .csv .xlsx .xls 格式，自动识别券商",
                    "单文件建议不超过 10MB",
                    "数据仅用于本地分析，不上传第三方服务器",
                    "您可以随时一键清空所有数据",
                  ].map((text) => (
                    <li
                      key={text}
                      className="flex items-start gap-2 text-xs text-text-secondary"
                    >
                      <CheckIconSmall />
                      <span>{text}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
