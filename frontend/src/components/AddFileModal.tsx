import { useState } from "react";
import FileDropzone from "./FileDropzone";
import { uploadFile, confirmFormat, importTrades } from "../api/upload";
import { linkFilesToAnalysis } from "../api/analysis";
import { useToast } from "../context/ToastContext";

interface Props {
  analysisId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function AddFileModal({ analysisId, onClose, onSuccess }: Props) {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const toast = useToast();

  const processFile = async (file: File) => {
    setLoading(true);
    try {
      setStatus("正在上传文件...");
      const result = await uploadFile(file);
      const formats = result.detected_formats || [];
      if (formats.length === 0) {
        toast.addToast("warning", "无法识别文件格式");
        setLoading(false);
        return;
      }

      const sourceType = formats[0].source_type;
      setStatus("正在解析交易记录...");
      const confirmed = await confirmFormat(result.raw_file_id, sourceType);

      setStatus("正在导入交易记录...");
      await importTrades(result.raw_file_id);

      setStatus("正在添加到分析...");
      await linkFilesToAnalysis(analysisId, [result.raw_file_id]);

      toast.addToast("success", "文件已添加到分析");
      onSuccess();
      onClose();
    } catch (err) {
      toast.addToast("error", err instanceof Error ? err.message : "添加失败");
      setLoading(false);
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        style={{
          position: "fixed", inset: 0, zIndex: 200,
          backgroundColor: "rgba(0,0,0,0.5)",
          animation: "fadeIn 0.15s ease-out",
        }}
        onClick={loading ? undefined : onClose}
      />
      {/* Dialog */}
      <div
        role="dialog"
        aria-modal="true"
        style={{
          position: "fixed", top: "50%", left: "50%", transform: "translate(-50%, -50%)",
          zIndex: 201,
          backgroundColor: "var(--bg-secondary)",
          border: "1px solid var(--border)",
          borderRadius: "16px",
          padding: "24px",
          width: 440,
          maxWidth: "90%",
          boxShadow: "0 12px 40px rgba(0,0,0,0.5)",
          animation: "scaleIn 0.15s ease-out",
        }}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 style={{ fontSize: "16px", fontWeight: 600 }}>添加交割单</h2>
          <button
            onClick={onClose}
            disabled={loading}
            style={{
              background: "none", border: "none", cursor: loading ? "default" : "pointer",
              color: "var(--text-secondary)", fontSize: 18, padding: "2px 6px",
              opacity: loading ? 0.3 : 1,
            }}
          >
            ✕
          </button>
        </div>

        {!loading ? (
          <FileDropzone onFile={processFile} loading={false} />
        ) : (
          <div
            className="flex flex-col items-center justify-center gap-3 py-8 rounded-lg"
            style={{ border: "1px dashed var(--border)" }}
          >
            <span
              className="inline-block w-8 h-8 border-2 border-t-transparent rounded-full animate-spin"
              style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
            />
            <span className="text-sm" style={{ color: "var(--text-secondary)" }}>{status}</span>
          </div>
        )}

        <p className="text-xs mt-3" style={{ color: "var(--text-secondary)" }}>
          支持 .csv .xlsx .xls 格式，新文件的交易记录将合并到当前分析中。
        </p>
      </div>
      <style>{`
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes scaleIn { from { opacity: 0; transform: translate(-50%, -50%) scale(0.95); } to { opacity: 1; transform: translate(-50%, -50%) scale(1); } }
      `}</style>
    </>
  );
}
