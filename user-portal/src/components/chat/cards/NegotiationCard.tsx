import { FeedbackWidget } from '../../shared/FeedbackWidget';

interface NegotiationCardData {
  negotiation_id?: string;
  job_id?: string;
  job_title?: string;
  market_research?: { range_mid?: number; range_low?: number; range_high?: number };
  counter_offer?: { target?: number; minimum_acceptable?: number };
}

export function NegotiationCard({ data }: { data: NegotiationCardData }) {
  const id = data.negotiation_id;
  const mid = data.market_research?.range_mid;

  return (
    <article className="mt-3 rounded-lg border border-line-2 bg-white p-4">
      <header>
        <h3 className="text-base font-semibold">Negotiation playbook</h3>
        {data.job_title && <p className="text-sm text-ink-3">{data.job_title}</p>}
      </header>

      {mid != null && (
        <p className="mt-2 text-sm">
          Market mid (indicative): <strong>${mid.toLocaleString()}</strong>
        </p>
      )}
      {data.counter_offer?.target != null && (
        <p className="text-sm text-ink-3">
          Suggested counter target: ${data.counter_offer.target.toLocaleString()}
        </p>
      )}

      {id && (
        <footer className="mt-3">
          <a href={`/negotiations/${id}`} className="text-xs text-cobalt hover:underline">
            Open full playbook
          </a>
          <FeedbackWidget resource="negotiation" resourceId={id} className="mt-3" />
        </footer>
      )}
    </article>
  );
}
