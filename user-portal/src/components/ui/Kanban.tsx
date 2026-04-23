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
    <div
      className="grid gap-3.5 overflow-x-auto pb-2"
      style={{
        gridTemplateColumns: `repeat(${columns.length}, minmax(220px, 1fr))`,
      }}
    >
      {columns.map((column) => {
        const columnItems = items.filter((item) => item.stage === column.id);
        const isOver = over === column.id;
        return (
          <div
            key={column.id}
            className="flex flex-col"
            onDragEnter={(event) => {
              event.preventDefault();
              setOver(column.id);
            }}
            onDragOver={(event) => {
              event.preventDefault();
              event.dataTransfer.dropEffect = 'move';
            }}
            onDragLeave={() =>
              setOver((previous) => (previous === column.id ? null : previous))
            }
            onDrop={(event) => {
              event.preventDefault();
              const id = event.dataTransfer.getData('text/plain');
              if (id) onStageChange(id, column.id);
              setOver(null);
            }}
          >
            <div className="mb-2 flex items-center justify-between px-1">
              <span className="text-[12px] font-semibold tracking-[0.02em] text-ink">
                {column.label}
              </span>
              <span className="text-[11px] text-ink-3">
                {columnItems.length}
              </span>
            </div>
            <div
              className={
                'flex flex-1 flex-col gap-2 rounded-xl p-1 transition-colors duration-150 motion-reduce:transition-none ' +
                (isOver
                  ? 'bg-[#f0efeb] outline outline-1 outline-dashed outline-line-2'
                  : '')
              }
            >
              {columnItems.length === 0 ? (
                <div className="mt-6 px-2 text-center text-[12px] text-ink-4">
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
                    className="cursor-grab rounded-[12px] border border-line bg-white p-3 shadow-[0_1px_0_rgba(31,29,26,0.02)] transition-shadow duration-150 hover:shadow-[0_8px_20px_-12px_rgba(31,29,26,0.18)] active:cursor-grabbing motion-reduce:transition-none"
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
