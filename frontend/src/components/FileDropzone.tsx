import { useState, useRef, type DragEvent } from "react";

interface FileDropzoneProps {
  onFile: (file: File) => void;
  loading?: boolean;
}

export default function FileDropzone({ onFile, loading }: FileDropzoneProps) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = () => setDragging(false);

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) onFile(file);
  };

  const handleClick = () => inputRef.current?.click();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onFile(file);
  };

  return (
    <div
      onClick={handleClick}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      style={{
        border: `2px dashed ${dragging ? "var(--accent)" : "var(--border)"}`,
        backgroundColor: dragging ? "rgba(79,140,255,0.08)" : "var(--bg-secondary)",
        borderRadius: "12px",
        cursor: "pointer",
        transition: "all 0.2s",
      }}
      className="flex flex-col items-center justify-center p-12"
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.xlsx,.xls"
        onChange={handleChange}
        className="hidden"
      />
      {loading ? (
        <div className="flex flex-col items-center gap-3">
          <div className="animate-spin w-8 h-8 border-2 border-t-transparent rounded-full" style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }} />
          <span className="text-sm" style={{ color: "var(--text-secondary)" }}>上传中...</span>
        </div>
      ) : (
        <>
          <span className="text-3xl mb-3">📄</span>
          <span className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
            拖拽交割单到此处，或点击选择文件
          </span>
          <span className="text-xs mt-2" style={{ color: "var(--text-secondary)" }}>
            支持 .csv .xlsx .xls 格式
          </span>
        </>
      )}
    </div>
  );
}
