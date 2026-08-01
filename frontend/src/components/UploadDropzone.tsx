import { useRef, useState, type DragEvent } from "react";

const ACCEPTED_TYPES = [
  "application/pdf",
  "image/png",
  "image/jpeg",
  "image/jpg",
  "image/tiff",
];

interface Props {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
}

export function UploadDropzone({ onFileSelected, disabled }: Props) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (files: FileList | null) => {
    const file = files?.[0];
    if (!file) return;
    if (!ACCEPTED_TYPES.includes(file.type)) {
      alert(`Unsupported file type: ${file.type || "unknown"}. Please upload a PDF or image.`);
      return;
    }
    onFileSelected(file);
  };

  return (
    <div
      onDragOver={(e: DragEvent) => {
        e.preventDefault();
        if (!disabled) setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e: DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        if (!disabled) handleFiles(e.dataTransfer.files);
      }}
      onClick={() => !disabled && inputRef.current?.click()}
      className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
        disabled
          ? "cursor-not-allowed border-slate-200 bg-slate-50 opacity-60"
          : isDragging
            ? "border-blue-400 bg-blue-50"
            : "border-slate-300 bg-white hover:border-blue-300 hover:bg-slate-50"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES.join(",")}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
        disabled={disabled}
      />
      <svg
        className="mb-3 h-9 w-9 text-slate-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"
        />
      </svg>
      <p className="text-sm font-medium text-slate-700">
        {disabled ? "Uploading..." : "Drop a lab report here, or click to browse"}
      </p>
      <p className="mt-1 text-xs text-slate-400">PDF, PNG, JPG, or TIFF</p>
    </div>
  );
}
