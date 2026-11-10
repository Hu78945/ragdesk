"use client";

import { useEffect, useRef, useState } from "react";
import { DocumentInfo, listDocuments, uploadDocuments } from "@/lib/api";

const ACCEPT = ".md,.markdown,.txt,.html,.htm,.pdf";

export function Documents() {
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const refresh = () =>
    listDocuments()
      .then(setDocs)
      .catch((e) => setStatus(`Could not reach the API: ${e.message}`));

  useEffect(() => {
    refresh();
  }, []);

  async function upload(files: FileList | null) {
    if (!files?.length) return;
    setBusy(true);
    setStatus(null);
    try {
      const added = await uploadDocuments(files);
      setStatus(`Indexed ${added.map((d) => `${d.name} (${d.chunks} chunks)`).join(", ")}`);
      await refresh();
    } catch (e) {
      setStatus(`Upload failed: ${(e as Error).message}`);
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
      <h2 className="text-sm font-semibold">Documents</h2>
      <p className="mt-1 text-xs text-zinc-500">Markdown, HTML, PDF or text. Re-uploading a name replaces it.</p>
      <label
        className={`mt-3 flex cursor-pointer items-center justify-center rounded-lg border border-dashed border-zinc-300 px-3 py-4 text-sm text-zinc-600 hover:border-indigo-400 hover:text-indigo-600 dark:border-zinc-700 dark:text-zinc-400 ${busy ? "pointer-events-none opacity-50" : ""}`}
      >
        {busy ? "Indexing…" : "Choose files to upload"}
        <input
          ref={input}
          type="file"
          multiple
          accept={ACCEPT}
          className="sr-only"
          onChange={(e) => upload(e.target.files)}
        />
      </label>
      {status && <p className="mt-2 text-xs text-zinc-500">{status}</p>}
      <ul className="mt-3 max-h-80 space-y-1 overflow-y-auto text-sm">
        {docs.map((d) => (
          <li key={d.id} className="flex justify-between gap-2">
            <span className="truncate">{d.name}</span>
            <span className="shrink-0 text-xs text-zinc-400">{d.chunks} chunks</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
