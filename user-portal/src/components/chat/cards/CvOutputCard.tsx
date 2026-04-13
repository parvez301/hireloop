import { FeedbackWidget } from '../../shared/FeedbackWidget';

interface CvOutputCardData {
  cv_output_id: string;
  job_id: string;
  job_title: string;
  company: string | null;
  changes_summary: string | null;
  keywords_injected: string[];
  pdf_url: string;
}

export function CvOutputCard({ data }: { data: CvOutputCardData }) {
  return (
    <article className="mt-3 rounded-lg border border-[#e3e2e0] bg-white p-4">
      <header>
        <h3 className="text-base font-semibold">Tailored CV — {data.job_title}</h3>
        {data.company && <p className="text-sm text-[#787774]">{data.company}</p>}
      </header>

      {data.changes_summary && (
        <pre className="mt-3 whitespace-pre-wrap rounded bg-[#fbfbfa] px-3 py-2 text-xs text-[#37352f]">
          {data.changes_summary}
        </pre>
      )}

      {data.keywords_injected.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {data.keywords_injected.map((k) => (
            <span
              key={k}
              className="rounded-full bg-[#f7f6f3] px-2 py-0.5 text-xs text-[#787774]"
            >
              {k}
            </span>
          ))}
        </div>
      )}

      <FeedbackWidget
        resource="cv_output"
        resourceId={data.cv_output_id}
        className="mt-3"
      />

      <footer className="mt-3 flex gap-2">
        <a
          href={data.pdf_url}
          target="_blank"
          rel="noreferrer"
          className="rounded bg-[#2383e2] px-3 py-1 text-xs text-white"
        >
          Download PDF
        </a>
        <button
          type="button"
          disabled
          className="rounded border border-[#e3e2e0] px-3 py-1 text-xs text-[#787774]"
          title="Available in Phase 5"
        >
          Regenerate
        </button>
      </footer>
    </article>
  );
}
