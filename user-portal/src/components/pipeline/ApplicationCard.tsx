import { type Application } from '../../lib/api';

interface Props {
  application: Application;
  jobTitle?: string;
  company?: string;
  grade?: string;
}

export function ApplicationCard({ application, jobTitle, company, grade }: Props) {
  return (
    <div className="rounded border border-[#e3e2e0] bg-white p-3 text-sm shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate font-medium">{jobTitle ?? 'Job'}</div>
          {company && <div className="truncate text-xs text-[#787774]">{company}</div>}
        </div>
        {grade && (
          <span className="rounded bg-[#f7f6f3] px-2 py-0.5 text-xs font-semibold">
            {grade}
          </span>
        )}
      </div>
      {application.notes && (
        <p className="mt-2 line-clamp-2 text-xs text-[#787774]">{application.notes}</p>
      )}
      <div className="mt-2 text-xs text-[#787774]">
        Updated {new Date(application.updated_at).toLocaleDateString()}
      </div>
    </div>
  );
}
