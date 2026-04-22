import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';

export type SidebarItem = {
  id: string;
  label: string;
  href: string;
  icon: LucideIcon;
  counter?: number | string;
};

type Props = {
  items: SidebarItem[];
  activeId: string;
  footer?: ReactNode;
};

export function Sidebar({ items, activeId, footer }: Props) {
  return (
    <aside className="sticky top-14 flex h-[calc(100vh-56px)] w-[260px] flex-col border-r border-line bg-white">
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="space-y-0.5">
          {items.map((item) => {
            const Icon = item.icon;
            const isActive = item.id === activeId;
            return (
              <li key={item.id}>
                <a
                  href={item.href}
                  className={
                    'group flex items-center gap-2.5 rounded-md border-l-2 px-2.5 py-1.5 text-[14px] transition-colors duration-150 motion-reduce:transition-none ' +
                    (isActive
                      ? 'border-ink bg-card font-semibold text-ink'
                      : 'border-transparent text-ink-2 hover:bg-[#faf9f6]')
                  }
                >
                  <Icon size={16} className="flex-none" strokeWidth={1.6} />
                  <span className="flex-1 truncate">{item.label}</span>
                  {item.counter !== undefined && item.counter !== '' && (
                    <span className="ml-auto rounded-full bg-[#f2f0ea] px-1.5 py-px text-[11px] font-medium text-ink-3">
                      {item.counter}
                    </span>
                  )}
                </a>
              </li>
            );
          })}
        </ul>
      </nav>
      {footer && <div className="border-t border-line px-3 py-3">{footer}</div>}
    </aside>
  );
}
