import { useDraggable, useDroppable } from '@dnd-kit/core';

import { type Application } from '../../lib/api';
import { ApplicationCard } from './ApplicationCard';

interface Props {
  title: string;
  status: Application['status'];
  applications: Application[];
  metaByJob: Record<string, { title: string; company: string | null; grade?: string }>;
}

function DraggableApplicationCard({
  application,
  meta,
}: {
  application: Application;
  meta: { title: string; company: string | null; grade?: string };
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: application.id,
  });
  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined;
  return (
    <div
      ref={setNodeRef}
      style={style}
      className={isDragging ? 'cursor-grabbing opacity-60' : 'cursor-grab'}
      {...listeners}
      {...attributes}
    >
      <ApplicationCard
        application={application}
        jobTitle={meta.title}
        company={meta.company ?? undefined}
        grade={meta.grade}
      />
    </div>
  );
}

export function KanbanColumn({ title, status, applications, metaByJob }: Props) {
  const { setNodeRef, isOver } = useDroppable({ id: status });
  return (
    <div
      ref={setNodeRef}
      className={`flex w-64 flex-shrink-0 flex-col rounded-lg border ${
        isOver ? 'border-[#2383e2] bg-[#f0f7ff]' : 'border-[#e3e2e0] bg-[#fbfbfa]'
      } p-3`}
    >
      <header className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold">{title}</h3>
        <span className="text-xs text-[#787774]">{applications.length}</span>
      </header>
      <div className="flex flex-col gap-2">
        {applications.map((a) => (
          <DraggableApplicationCard
            key={a.id}
            application={a}
            meta={metaByJob[a.job_id] ?? { title: 'Job', company: null }}
          />
        ))}
        {applications.length === 0 && <p className="text-xs text-[#787774]">Empty</p>}
      </div>
    </div>
  );
}
