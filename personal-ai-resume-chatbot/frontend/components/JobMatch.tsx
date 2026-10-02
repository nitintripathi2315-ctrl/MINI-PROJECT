import type { ReactNode } from "react";
import type { JobMatchResult } from "@/lib/types";

// Only picks a color for display; the percentage itself comes from the backend
function tone(percent: number) {
  if (percent >= 70)
    return { bar: "bg-emerald-500", text: "text-emerald-600 dark:text-emerald-400" };
  if (percent >= 40)
    return { bar: "bg-amber-500", text: "text-amber-600 dark:text-amber-400" };
  return { bar: "bg-rose-500", text: "text-rose-600 dark:text-rose-400" };
}

function Chips({ items, className }: { items: string[]; className: string }) {
  if (items.length === 0) {
    return <p className="text-sm text-muted">None identified.</p>;
  }
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item, i) => (
        <span
          key={`${item}-${i}`}
          className={`rounded-full px-2.5 py-1 text-xs font-medium ${className}`}
        >
          {item}
        </span>
      ))}
    </div>
  );
}

function Block({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-5">
      <h4 className="mb-2 text-sm font-semibold">{title}</h4>
      {children}
    </section>
  );
}

export default function JobMatch({ result }: { result: JobMatchResult }) {
  const p = result.match_percentage;
  const t = tone(p);

  return (
    <div className="rounded-2xl border border-line bg-surface p-4 sm:p-5">
      <h3 className="text-base font-semibold">Job Match Analysis</h3>

      <div className="mt-4">
        <div className="flex items-baseline justify-between">
          <span className="text-sm text-muted">Overall Match</span>
          <span className={`text-2xl font-semibold ${t.text}`}>{p}%</span>
        </div>
        <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-line">
          <div
            className={`h-full rounded-full transition-all duration-700 ${t.bar}`}
            style={{ width: `${p}%` }}
          />
        </div>
      </div>

      <Block title="Matching Skills">
        <Chips
          items={result.matching_skills}
          className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
        />
      </Block>

      <Block title="Missing / Limited Skills">
        <Chips
          items={result.missing_skills}
          className="bg-rose-500/10 text-rose-700 dark:text-rose-300"
        />
      </Block>

      <Block title="Relevant Projects">
        {result.relevant_projects.length === 0 ? (
          <p className="text-sm text-muted">None identified.</p>
        ) : (
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {result.relevant_projects.map((proj, i) => (
              <li key={`${proj}-${i}`}>{proj}</li>
            ))}
          </ul>
        )}
      </Block>

      {result.education_fit && (
        <Block title="Education">
          <p className="text-sm leading-relaxed">{result.education_fit}</p>
        </Block>
      )}

      <Block title="Explanation">
        <p className="text-sm leading-relaxed">{result.explanation}</p>
      </Block>
    </div>
  );
}