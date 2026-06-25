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
      className={[
        "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-12 transition-all duration-200 focus-ring",
        dragging
          ? "border-accent bg-accent/[0.08]"
          : "border-border bg-bg-secondary hover:border-text-secondary",
      ].join(" ")}
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
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          <span className="text-sm text-text-secondary">上传中...</span>
        </div>
      ) : (
        <>
          <span className="mb-3 text-3xl">📄</span>
          <span className="text-sm font-medium text-text-secondary">
            拖拽交割单到此处，或点击选择文件
          </span>
          <span className="mt-2 text-xs text-text-secondary">
            支持 .csv .xlsx .xls 格式
          </span>
        </>
      )}
    </div>
  );
}
