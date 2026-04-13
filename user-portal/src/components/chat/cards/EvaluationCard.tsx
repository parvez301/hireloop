import { FeedbackWidget } from '../../shared/FeedbackWidget';

interface EvaluationCardData {
  evaluation_id: string;
  job_id: string;
  job_title: string;
  company: string | null;
  location: string | null;
  salary_range: string | null;
  overall_grade: string;
  match_score: number;
  recommendation: 'strong_match' | 'worth_exploring' | 'skip';
  dimension_scores: Record<string, { score: number; grade: string; reasoning: string; signals?: string[] }>;
  reasoning: string;
  red_flags: string[];
  personalization: string | null;
  cached: boolean;
}

const GRADE_COLOR: Record<string, string> = {
  A: 'bg-[#35a849] text-white',
  'A-': 'bg-[#35a849] text-white',
  'B+': 'bg-[#2383e2] text-white',
  B: 'bg-[#2383e2] text-white',
  'B-': 'bg-[#2383e2] text-white',
  'C+': 'bg-[#cb912f] text-white',
  C: 'bg-[#cb912f] text-white',
  D: 'bg-[#e03e3e] text-white',
  F: 'bg-[#e03e3e] text-white',
};

export function EvaluationCard({ data }: { data: EvaluationCardData }) {
  const gradeClass = GRADE_COLOR[data.overall_grade] ?? 'bg-[#787774] text-white';

  return (
    <article className="mt-3 rounded-lg border border-[#e3e2e0] bg-white p-4">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold">{data.job_title}</h3>
          <p className="text-sm text-[#787774]">
            {[data.company, data.location].filter(Boolean).join(' · ')}
          </p>
          {data.salary_range && (
            <p className="text-sm text-[#787774]">{data.salary_range}</p>
          )}
        </div>
        <span className={`rounded px-3 py-1 text-sm font-semibold ${gradeClass}`}>
          {data.overall_grade}
        </span>
      </header>

      <p className="mt-3 text-sm">{data.reasoning}</p>

      {data.red_flags.length > 0 && (
        <ul className="mt-3 rounded bg-[#fbfbfa] px-3 py-2 text-xs text-[#e03e3e]">
          {data.red_flags.map((flag, i) => (
            <li key={i}>⚠ {flag}</li>
          ))}
        </ul>
      )}

      <details className="mt-3 text-sm">
        <summary className="cursor-pointer text-[#2383e2]">Dimension breakdown</summary>
        <ul className="mt-2 space-y-1">
          {Object.entries(data.dimension_scores).map(([key, dim]) => (
            <li key={key} className="flex justify-between text-xs">
              <span className="text-[#787774]">{key.replaceAll('_', ' ')}</span>
              <span className="font-mono">
                {dim.grade} ({dim.score.toFixed(2)})
              </span>
            </li>
          ))}
        </ul>
      </details>

      <FeedbackWidget
        resource="evaluation"
        resourceId={data.evaluation_id}
        className="mt-3"
      />

      <footer className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          disabled
          className="rounded border border-[#e3e2e0] px-3 py-1 text-xs text-[#787774]"
          title="Available in Phase 5"
        >
          Save
        </button>
        <button
          type="button"
          disabled
          className="rounded border border-[#e3e2e0] px-3 py-1 text-xs text-[#787774]"
          title="Available in Phase 5"
        >
          Tailor CV
        </button>
        {data.cached && (
          <span className="ml-auto rounded bg-[#f7f6f3] px-2 py-0.5 text-xs text-[#787774]">
            Cached
          </span>
        )}
      </footer>
    </article>
  );
}
