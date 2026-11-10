"use client";

import { useEffect, useState } from "react";
import { EvalResults, latestEval, RetrievalRow } from "@/lib/api";

const METRICS = ["recall@1", "recall@3", "recall@5", "mrr@10"] as const;
const pct = (x: number) => `${(x * 100).toFixed(0)}%`;

export default function EvalsPage() {
  const [results, setResults] = useState<EvalResults | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    latestEval().then(setResults, (e) => setError(e.message));
  }, []);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!results) return <p className="animate-pulse text-zinc-400">Loading eval results…</p>;

  const best = Object.fromEntries(
    METRICS.map((m) => [m, Math.max(...results.retrieval.map((r) => r[m]))]),
  ) as Record<(typeof METRICS)[number], number>;
  const modes = results.retrieval.map((r) => r.mode);
  const { configured, best_threshold_on_this_set: sweep } = results.refusal;

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Retrieval evaluation</h1>
        <p className="mt-1 text-sm text-zinc-500">
          {results.questions.in_scope} in-scope + {results.questions.out_of_scope} out-of-scope questions over{" "}
          {results.corpus.documents} documents ({results.corpus.chunks} chunks) · store{" "}
          <code>{results.store}</code> · embedder <code>{results.embedder}</code> · {results.generated_at}
        </p>
      </header>

      <section className="overflow-x-auto rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase text-zinc-500">
            <tr>
              <th className="px-4 py-3">Mode</th>
              {METRICS.map((m) => (
                <th key={m} className="px-4 py-3 text-right">
                  {m}
                </th>
              ))}
              <th className="px-4 py-3 text-right">p50 latency</th>
            </tr>
          </thead>
          <tbody>
            {results.retrieval.map((r: RetrievalRow) => (
              <tr key={r.mode} className="border-t border-zinc-100 dark:border-zinc-800">
                <td className="px-4 py-3 font-mono">{r.mode}</td>
                {METRICS.map((m) => (
                  <td key={m} className={`px-4 py-3 text-right tabular-nums ${r[m] === best[m] ? "font-semibold text-indigo-600 dark:text-indigo-400" : ""}`}>
                    {r[m].toFixed(3)}
                  </td>
                ))}
                <td className="px-4 py-3 text-right tabular-nums text-zinc-500">{r.latency_ms_p50} ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <h2 className="text-sm font-semibold">Refusal gate (threshold {configured.threshold})</h2>
          <p className="mt-2 text-sm">
            {pct(configured.in_scope_answered)} of in-scope questions answered ·{" "}
            {pct(configured.out_of_scope_refused)} of out-of-scope questions refused
          </p>
          <p className="mt-2 text-xs text-zinc-500">
            Best threshold on this set: {sweep.threshold} ({pct(sweep.in_scope_answered)} answered /{" "}
            {pct(sweep.out_of_scope_refused)} refused). Confidence ranges overlap: in-scope{" "}
            {results.refusal.in_scope_confidence.join("–")}, out-of-scope {results.refusal.out_of_scope_confidence.join("–")}.
          </p>
        </div>
        <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <h2 className="text-sm font-semibold">Offline answers</h2>
          <p className="mt-2 text-sm">
            {pct(results.extractive_answers.evidence_in_answer)} of extractive answers quote the gold evidence
          </p>
          <p className="mt-2 text-xs text-zinc-500">
            Retrieval: <code>{results.extractive_answers.retrieval}</code>, no LLM involved.
          </p>
        </div>
        <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <h2 className="text-sm font-semibold">Faithfulness (LLM-as-judge)</h2>
          {results.faithfulness ? (
            <p className="mt-2 text-sm">
              {pct(results.faithfulness.faithful_rate)} of {results.faithfulness.judged} answers by{" "}
              <code>{results.faithfulness.answer_model}</code> judged faithful by <code>{results.faithfulness.judge_model}</code>
            </p>
          ) : (
            <p className="mt-2 text-sm text-zinc-500">Not run — requires ANTHROPIC_API_KEY and --judge.</p>
          )}
        </div>
      </section>

      <section>
        <h2 className="mb-2 text-sm font-semibold">Rank of first relevant chunk per question (— = not in top {results.k})</h2>
        <div className="overflow-x-auto rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase text-zinc-500">
              <tr>
                <th className="px-4 py-2">Question</th>
                {modes.map((m) => (
                  <th key={m} className="px-3 py-2 text-right font-mono normal-case">
                    {m}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {results.per_question.map((row) => (
                <tr key={row.q} className="border-t border-zinc-100 dark:border-zinc-800">
                  <td className="px-4 py-2">{row.q}</td>
                  {modes.map((m) => {
                    const rank = row.ranks[m];
                    const tone = rank === 1 ? "text-emerald-600" : rank === null ? "text-red-600" : rank > 3 ? "text-amber-600" : "";
                    return (
                      <td key={m} className={`px-3 py-2 text-right tabular-nums ${tone}`}>
                        {rank ?? "—"}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
