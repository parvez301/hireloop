import { FeedbackWidget } from '../../shared/FeedbackWidget';

interface InterviewPrepCardData {
  interview_prep_id: string;
  job_id: string | null;
  role: string;
  story_count?: number;
  question_count?: number;
  top_questions: Array<{
    question: string;
    category: string;
    suggested_story_title: string | null;
  }>;
  red_flag_questions: Array<{
    question: string;
    what_to_listen_for: string;
  }>;
}

export function InterviewPrepCard({ data }: { data: InterviewPrepCardData }) {
  return (
    <article className="mt-3 rounded-lg border border-line-2 bg-white p-4">
      <header>
        <h3 className="text-base font-semibold">Interview prep</h3>
        <p className="text-sm text-ink-3">{data.role}</p>
      </header>

      <ul className="mt-3 space-y-2 text-sm">
        {data.top_questions.slice(0, 5).map((q, i) => (
          <li key={i} className="rounded bg-sidebar px-2 py-1">
            <span className="text-xs uppercase text-ink-3">{q.category}</span>
            <p>{q.question}</p>
          </li>
        ))}
      </ul>

      {data.red_flag_questions.length > 0 && (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer text-cobalt">Questions to ask them</summary>
          <ul className="mt-2 space-y-1 text-xs">
            {data.red_flag_questions.map((r, i) => (
              <li key={i}>
                <strong>{r.question}</strong>
                {r.what_to_listen_for && (
                  <span className="text-ink-3"> — {r.what_to_listen_for}</span>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}

      <footer className="mt-3">
        <a
          href={`/interview-prep/${data.interview_prep_id}`}
          className="text-xs text-cobalt hover:underline"
        >
          Open full prep
        </a>
        <FeedbackWidget
          resource="interview_prep"
          resourceId={data.interview_prep_id}
          className="mt-3"
        />
      </footer>
    </article>
  );
}
