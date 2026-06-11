import { useState } from "react";
import { useNavigate } from "react-router-dom";
import FileDropzone from "../components/FileDropzone";
import FormatSelector from "../components/FormatSelector";
import TradePreview from "../components/TradePreview";
import { uploadFile, confirmFormat, importTrades } from "../api/upload";
import { runAnalysis } from "../api/analysis";

type Step = "upload" | "confirm" | "preview";

interface FormatOption {
  source_type: string;
  asset_type: string;
  score: number;
}

export default function Upload() {
  const [step, setStep] = useState<Step>("upload");
  const [loading, setLoading] = useState(false);
  const [rawFileId, setRawFileId] = useState<string>("");
  const [formats, setFormats] = useState<FormatOption[]>([]);
  const [parsedData, setParsedData] = useState<Record<string, unknown>[]>([]);
  const navigate = useNavigate();

  const handleFile = async (file: File) => {
    setLoading(true);
    try {
      const result = await uploadFile(file);
      setRawFileId(result.raw_file_id);
      setFormats(result.detected_formats || []);
      setStep("confirm");
    } catch (err) {
      alert(err instanceof Error ? err.message : "上传失败");
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async (sourceType: string) => {
    setLoading(true);
    try {
      const result = await confirmFormat(rawFileId, sourceType);
      setParsedData(result.trades || []);
      setStep("preview");
    } catch (err) {
      alert(err instanceof Error ? err.message : "确认失败");
    } finally {
      setLoading(false);
    }
  };

  const handleImport = async () => {
    setLoading(true);
    try {
      await importTrades(rawFileId);
      // After import, auto-run analysis
      const today = new Date().toISOString().split("T")[0];
      const analysis = await runAnalysis("2020-01-01", today);
      navigate(`/analysis/${analysis.analysis_id}`);
    } catch (err) {
      alert(err instanceof Error ? err.message : "导入失败");
    } finally {
      setLoading(false);
    }
  };

  const steps: Step[] = ["upload", "confirm", "preview"];
  const stepIndex = steps.indexOf(step);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-xl font-semibold mb-6">上传交割单</h1>

      {step === "upload" && <FileDropzone onFile={handleFile} loading={loading} />}
      {step === "confirm" && (
        <FormatSelector formats={formats} onConfirm={handleConfirm} loading={loading} />
      )}
      {step === "preview" && (
        <TradePreview trades={parsedData} onImport={handleImport} loading={loading} />
      )}

      <div className="flex items-center justify-center gap-2 mt-8">
        {steps.map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <div
              style={{
                width: "28px",
                height: "28px",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "12px",
                fontWeight: 600,
                backgroundColor:
                  i <= stepIndex ? "var(--accent)" : "var(--bg-tertiary)",
                color: i <= stepIndex ? "#fff" : "var(--text-secondary)",
                border: i <= stepIndex ? "none" : "1px solid var(--border)",
              }}
            >
              {i + 1}
            </div>
            {i < steps.length - 1 && (
              <div
                style={{
                  width: "32px",
                  height: "2px",
                  backgroundColor:
                    i < stepIndex ? "var(--accent)" : "var(--border)",
                }}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
