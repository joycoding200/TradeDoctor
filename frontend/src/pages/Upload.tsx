import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import FileDropzone from "../components/FileDropzone";
import FormatSelector from "../components/FormatSelector";
import { uploadFile, confirmFormat, importTrades } from "../api/upload";
import { runAnalysis, linkFilesToAnalysis } from "../api/analysis";
import { useToast } from "../context/ToastContext";

interface FormatOption {
  source_type: string;
  asset_type: string;
  score: number;
}

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

  const autoProcess = async (fileId: string, sourceType: string, fileName: string) => {
    setStatusText("正在解析交易记录...");
    const confirmed = await confirmFormat(fileId, sourceType);
    const trades = confirmed.trades || [];

    setStatusText("正在导入交易记录...");
    await importTrades(fileId);

    if (attachToAnalysisId) {
      // Linking mode: attach this file to an existing analysis
      setStatusText("正在添加到分析...");
      await linkFilesToAnalysis(attachToAnalysisId, [fileId]);
      toast.addToast("success", "文件已添加到分析");
      navigate(`/analysis/${attachToAnalysisId}`);
    } else {
      // New analysis mode
      setStatusText("正在运行分析...");
      const dates = trades
        .map((t: any) => t.datetime)
        .filter(Boolean)
        .sort();
      const today = new Date().toISOString().split("T")[0];
      const dateStart = dates[0]?.split("T")[0] || "2020-01-01";
      const dateEnd = dates[dates.length - 1]?.split("T")[0] || today;
      const analysis = await runAnalysis(dateStart, dateEnd, fileId, fileName);
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

  // Show format selector only when confidence is low
  if (formats.length > 0 && formats[0].score < 0.7) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <h1 className="text-xl font-semibold mb-6">{pageTitle}</h1>
        <FormatSelector formats={formats} onConfirm={handleConfirm} loading={loading} />
      </div>
    );
  }

  // Show error state when no formats detected (and not loading)
  if (formats.length === 0 && !loading && rawFileId) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <h1 className="text-xl font-semibold mb-6">{pageTitle}</h1>
        <FileDropzone onFile={handleFile} loading={false} />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-xl font-semibold mb-6">{pageTitle}</h1>
      <FileDropzone onFile={handleFile} loading={loading} />
      {loading && statusText && (
        <div className="mt-6 flex items-center justify-center gap-2 text-text-secondary">
          <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          <span className="text-sm">{statusText}</span>
        </div>
      )}
    </div>
  );
}
