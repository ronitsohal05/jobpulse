"use client";

import { useCallback, useMemo, useState } from "react";
import { useDropzone } from "react-dropzone";
import { uploadResume } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function UploadPage() {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  const onDrop = useCallback(async (accepted: File[]) => {
    const file = accepted[0];
    if (!file) return;
    setError(null);
    setResult(null);
    setUploading(true);
    try {
      const res = await uploadResume(file);
      setResult(res);
    } catch (e: any) {
      setError(e?.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "application/msword": [".doc"],
    },
  });

  const parsed = useMemo(() => result?.resume?.parsed?.data, [result]);
  const resumeId = result?.resume?.id as string | undefined;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Resume upload</h1>
        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
          Upload a PDF/DOCX resume. We’ll extract text, parse structured fields, and extract skills.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Drag and drop</CardTitle>
          <CardDescription>PDF or DOCX. Parsing runs immediately (MVP).</CardDescription>
        </CardHeader>
        <CardContent>
          <div
            {...getRootProps()}
            className={[
              "cursor-pointer rounded-xl border border-dashed p-10 text-center transition-colors",
              isDragActive
                ? "border-zinc-900 bg-zinc-50 dark:border-zinc-50 dark:bg-zinc-900/40"
                : "border-zinc-200 bg-white hover:bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-950 dark:hover:bg-zinc-900/40",
            ].join(" ")}
          >
            <input {...getInputProps()} />
            <div className="text-sm font-medium">
              {isDragActive ? "Drop the file to upload" : "Drop a resume here, or click to select"}
            </div>
            <div className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">
              Tip: include a Skills section for best extraction.
            </div>
          </div>

          {error ? (
            <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-200">
              {error}
            </div>
          ) : null}

          {uploading ? (
            <div className="mt-4 text-sm text-zinc-600 dark:text-zinc-400">Uploading…</div>
          ) : null}
        </CardContent>
      </Card>

      {result ? (
        <Card>
          <CardHeader>
            <CardTitle>Parsed resume</CardTitle>
            <CardDescription>
              Resume ID: <span className="font-mono text-xs">{resumeId}</span>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-3">
              <a href={`/dashboard/recommendations?resumeId=${encodeURIComponent(resumeId || "")}`}>
                <Button disabled={!resumeId}>Find job matches</Button>
              </a>
              <a href={`/dashboard/search?resumeId=${encodeURIComponent(resumeId || "")}`}>
                <Button variant="outline" disabled={!resumeId}>
                  Search with resume context
                </Button>
              </a>
            </div>
            <pre className="max-h-[420px] overflow-auto rounded-lg border border-zinc-200 bg-zinc-50 p-4 text-xs text-zinc-900 dark:border-zinc-800 dark:bg-zinc-900/30 dark:text-zinc-50">
              {JSON.stringify(parsed, null, 2)}
            </pre>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

