interface ScanResultsCardData {
  scan_run_id: string;
  scan_name: string;
  scanned_count: number;
  new_count: number;
  top_jobs: Array<{
    job_id: string;
    title: string;
    company: string;
    location: string;
    salary_range: string | null;
    grade?: string;
    match_score?: number;
  }>;
}

export function ScanResultsCard({ data }: { data: ScanResultsCardData }) {
  return (
    <article className="mt-3 rounded-lg border border-[#e3e2e0] bg-white p-4">
      <header>
        <h3 className="text-base font-semibold">Scan results — {data.scan_name}</h3>
        <p className="mt-1 text-xs text-[#787774]">
          {data.scanned_count} jobs scanned · {data.new_count} new
        </p>
      </header>

      <ul className="mt-3 divide-y divide-[#e3e2e0]">
        {data.top_jobs.slice(0, 5).map((j) => (
          <li key={j.job_id} className="flex items-center justify-between py-2 text-sm">
            <div>
              <strong>{j.title}</strong> <span className="text-[#787774]">@ {j.company}</span>
              <div className="text-xs text-[#787774]">
                {j.location} {j.salary_range ? `· ${j.salary_range}` : ''}
              </div>
            </div>
          </li>
        ))}
      </ul>

      <footer className="mt-3 flex gap-2">
        <a
          href={`/scans/${data.scan_run_id}`}
          className="rounded border border-[#e3e2e0] px-3 py-1 text-xs"
        >
          View all
        </a>
      </footer>
    </article>
  );
}
