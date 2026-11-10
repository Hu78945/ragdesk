export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Source = {
  n: number;
  chunk_id: number;
  document: string;
  heading: string;
  text: string;
  score: number;
};

export type Done = { refused: boolean; answerer: string; confidence: number };

export type AskEvent =
  | { event: "sources"; data: { sources: Source[] } }
  | { event: "token"; data: { text: string } }
  | { event: "done"; data: Done }
  | { event: "error"; data: { message: string } };

export type DocumentInfo = { id: number; name: string; chunks: number };

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `${res.status} ${res.statusText}`);
  }
  return res.json();
}

export const listDocuments = () => fetch(`${API_URL}/api/documents`).then(json<DocumentInfo[]>);

export function uploadDocuments(files: FileList | File[]) {
  const form = new FormData();
  for (const f of Array.from(files)) form.append("files", f);
  return fetch(`${API_URL}/api/documents`, { method: "POST", body: form }).then(json<DocumentInfo[]>);
}

export const latestEval = () => fetch(`${API_URL}/api/evals/latest`, { cache: "no-store" }).then(json<EvalResults>);

/** POST /api/ask and yield parsed server-sent events (EventSource can't POST). */
export async function* ask(question: string, signal?: AbortSignal): AsyncGenerator<AskEvent> {
  const res = await fetch(`${API_URL}/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`${res.status} ${res.statusText}`);
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    let sep;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      let event = "message";
      let data = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7);
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      yield { event, data: JSON.parse(data) } as AskEvent;
    }
  }
}

export type RetrievalRow = {
  mode: string;
  "recall@1": number;
  "recall@3": number;
  "recall@5": number;
  "mrr@10": number;
  latency_ms_p50: number;
};

type RefusalPoint = { threshold: number; in_scope_answered: number; out_of_scope_refused: number };

export type EvalResults = {
  generated_at: string;
  store: string;
  embedder: string;
  corpus: { documents: number; chunks: number };
  questions: { in_scope: number; out_of_scope: number };
  k: number;
  retrieval: RetrievalRow[];
  refusal: {
    configured: RefusalPoint;
    best_threshold_on_this_set: RefusalPoint;
    in_scope_confidence: [number, number];
    out_of_scope_confidence: [number, number];
  };
  extractive_answers: { answerer: string; retrieval: string; evidence_in_answer: number };
  faithfulness: null | { answer_model: string; judge_model: string; judged: number; faithful_rate: number };
  per_question: { q: string; ranks: Record<string, number | null> }[];
};
