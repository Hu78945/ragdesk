import { Fragment } from "react";

/** Renders answer text, turning [n] markers into buttons that select source n. */
export function Answer({ text, onCite }: { text: string; onCite: (n: number) => void }) {
  const parts = text.split(/(\[\d+\])/g);
  return (
    <p className="whitespace-pre-wrap leading-7">
      {parts.map((part, i) => {
        const m = part.match(/^\[(\d+)\]$/);
        if (!m) return <Fragment key={i}>{part}</Fragment>;
        const n = Number(m[1]);
        return (
          <button
            key={i}
            onClick={() => onCite(n)}
            className="mx-0.5 rounded bg-indigo-100 px-1.5 py-0.5 align-baseline font-mono text-xs text-indigo-700 hover:bg-indigo-200 dark:bg-indigo-950 dark:text-indigo-300 dark:hover:bg-indigo-900"
            aria-label={`Show source ${n}`}
          >
            {n}
          </button>
        );
      })}
    </p>
  );
}
