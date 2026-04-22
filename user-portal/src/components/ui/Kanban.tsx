import { useState, type ReactNode } from 'react';

export type KanbanColumn<S extends string> = {
  id: S;
  label: string;
  color?: string;
};

export type KanbanItem<S extends string> = {
  id: string;
  stage: S;
};

type Props<S extends string, I extends KanbanItem<S>> = {
  columns: KanbanColumn<S>[];
  items: I[];
  onStageChange: (id: string, nextStage: S) => void;
  renderCard: (item: I) => ReactNode;
  emptyHint?: string;
};

export function Kanban<S extends string, I extends KanbanItem<S>>({
  columns,
  items,
  onStageChange,
  renderCard,
  emptyHint,
}: Props<S, I>) {
  const [over, setOver] = useState<S | null>(null);

  return (
    <div className="flex gap-3 overflow-x-auto pb-2">
      {columns.map((column) => {
        const columnItems = items.filter((item) => item.stage === column.id);
        const isOver = over === column.id;
        return (
          <div
            key={column.id}
            className="flex min-w-[260px] flex-1 flex-col"
            onDragEnter={(event) => {
              event.preventDefault();
              setOver(column.id);
            }}
            onDragOver={(event) => {
              event.preventDefault();
              event.dataTransfer.dropEffect = 'move';
            }}
            onDragLeave={() => setOver((previous) => (previous === column.id ? null : previous))}
            onDrop={(event) => {
              event.preventDefault();
              const id = event.dataTransfer.getData('text/plain');
              if (id) onStageChange(id, column.id);
              setOver(null);
            }}
          >
            <div
              className={
                'flex items-center justify-between rounded-t-xl border border-b-0 border-line px-3 py-2 text-[12px] font-medium uppercase tracking-[0.14em] text-ink-3 ' +
                (isOver ? 'bg-[#faf9f6]' : 'bg-card')
              }
            >
              <span>{column.label}</span>
              <span className="rounded-full bg-white px-1.5 text-[11px] text-ink-3">
                {columnItems.length}
              </span>
            </div>
            <div
              className={
                'flex flex-1 flex-col gap-2 rounded-b-xl border border-line p-2 transition-colors duration-150 motion-reduce:transition-none ' +
                (isOver ? 'bg-[#faf9f6]' : 'bg-white')
              }
            >
              {columnItems.length === 0 ? (
                <div className="mt-6 text-center text-[12px] text-ink-4">
                  {emptyHint ?? 'Nothing here yet.'}
                </div>
              ) : (
                columnItems.map((item) => (
                  <div
                    key={item.id}
                    draggable
                    onDragStart={(event) => {
                      event.dataTransfer.setData('text/plain', item.id);
                      event.dataTransfer.effectAllowed = 'move';
                    }}
                    className="cursor-grab rounded-xl border border-line bg-white p-3 shadow-[0_1px_0_rgba(31,29,26,0.02)] active:cursor-grabbing"
                  >
                    {renderCard(item)}
                  </div>
                ))
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
