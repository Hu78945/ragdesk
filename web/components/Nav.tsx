"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Ask" },
  { href: "/evals", label: "Evals" },
];

export function Nav() {
  const path = usePathname();
  return (
    <header className="border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/80">
      <nav className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3">
        <span className="font-semibold tracking-tight">
          rag<span className="text-indigo-600 dark:text-indigo-400">desk</span>
        </span>
        {LINKS.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            aria-current={path === href ? "page" : undefined}
            className={`text-sm ${path === href ? "font-medium text-zinc-900 dark:text-zinc-100" : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300"}`}
          >
            {label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
