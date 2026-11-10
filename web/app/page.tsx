"use client";

import { FormEvent, useRef, useState } from "react";
import { Answer } from "@/components/Answer";
import { Documents } from "@/components/Documents";
import { ask, Done, Source } from "@/lib/api";

const EXAMPLES = [
  "How long are dead-lettered runs kept?",
  "What does error KST-4102 mean?",
  "How do I stop jobs from overlapping when migrating from cron?",
];

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [done, setDone] = useState<Done | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState<number | null>(null);
  const abort = useRef<AbortController | null>(null);

  async function submit(q: string) {
    if (!q.trim()) return;
    abort.current?.abort();
    abort.current = new AbortController();
    setAnswer("");
    setSources([]);
    setDone(null);
    setError(null);
    setActive(null);
    setLoading(true);
    try {
      for await (const ev of ask(q, abort.current.signal)) {
        if (ev.event === "sources") setSources(ev.data.sources);
        else if (ev.event === "token") setAnswer((a) => a + ev.data.text);
        else if (ev.event === "done") setDone(ev.data);
        else if (ev.event === "error") setError(ev.data.message);
      }
    } catch (e) {
      if ((e as Error).name !== "AbortError") setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    submit(question);
  }

  function cite(n: number) {
    setActive(n);
    document.getElementById(`source-${n}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[18rem_1fr]">
      <aside>
        <Documents />
      </aside>

      <div className="space-y-6">
        <form onSubmit={onSubmit} className="flex gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question about your documents…"
            aria-label="Question"
            className="flex-1 rounded-lg border border-zinc-300 bg-white px-4 py-2.5 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-zinc-700 dark:bg-zinc-900"
          />
          <button
            disabled={loading || !question.trim()}
            className="rounded-lg bg-indigo-600 px-5 font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {loading ? "Thinking…" : "Ask"}
          </button>
        </form>

        {!answer && !loading && !error && (
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((q) => (
              <button
                key={q}
                onClick={() => {
                  setQuestion(q);
                  submit(q);
                }}
                className="rounded-full border border-zinc-300 px-3 py-1 text-sm text-zinc-600 hover:border-indigo-400 hover:text-indigo-600 dark:border-zinc-700 dark:text-zinc-400"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {error && (
          <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
            {error}
          </p>
        )}

        {(answer || loading) && (
          <section className="rounded-xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
            {answer ? (
              <Answer text={answer} onCite={cite} />
            ) : (
              <p className="animate-pulse text-zinc-400">Retrieving…</p>
            )}
            {done && (
              <p className="mt-4 text-xs text-zinc-500">
                {done.refused ? "Refused · " : ""}
                answered by <span className="font-mono">{done.answerer}</span> · retrieval confidence{" "}
                {done.confidence.toFixed(2)}
              </p>
            )}
          </section>
        )}

        {sources.length > 0 && (
          <section>
            <h2 className="mb-2 text-sm font-semibold">Sources</h2>
            <ol className="space-y-2">
              {sources.map((s) => (
                <li
                  key={s.chunk_id}
                  id={`source-${s.n}`}
                  className={`rounded-lg border bg-white p-3 transition-colors dark:bg-zinc-900 ${active === s.n ? "border-indigo-500 ring-2 ring-indigo-500/20" : "border-zinc-200 dark:border-zinc-800"}`}
                >
                  <button onClick={() => setActive(active === s.n ? null : s.n)} className="w-full text-left">
                    <span className="mr-2 font-mono text-xs text-indigo-600 dark:text-indigo-400">[{s.n}]</span>
                    <span className="text-sm font-medium">{s.document}</span>
                    <span className="ml-2 text-xs text-zinc-500">{s.heading}</span>
                  </button>
                  <p
                    className={`mt-2 whitespace-pre-wrap text-sm text-zinc-600 dark:text-zinc-400 ${active === s.n ? "" : "line-clamp-2"}`}
                  >
                    {s.text}
                  </p>
                </li>
              ))}
            </ol>
          </section>
        )}
      </div>
    </div>
  );
}
