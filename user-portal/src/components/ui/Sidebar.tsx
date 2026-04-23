import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';

export type SidebarCounter = {
  label: number | string;
  /** Override badge palette, e.g. {'bg-[#eaf6ff]','text-cobalt'}. */
  badgeClass?: string;
};

export type SidebarItem = {
  id: string;
  label: string;
  href: string;
  icon: LucideIcon;
  counter?: number | string | SidebarCounter;
};

export type SidebarSection = {
  label: string;
  items: SidebarItem[];
};

type Props = {
  sections: SidebarSection[];
  activeId: string;
  header?: ReactNode;
  footer?: ReactNode;
};

const INACTIVE_BADGE = 'bg-[#ece9e2] text-[#6b6966]';
const ACTIVE_BADGE = 'bg-white/15 text-white';

function resolveCounter(
  counter: SidebarItem['counter'],
): { label: number | string; badgeClass?: string } | null {
  if (counter === undefined || counter === '' || counter === null) return null;
  if (typeof counter === 'object') return counter;
  return { label: counter };
}

export function Sidebar({ sections, activeId, header, footer }: Props) {
  return (
    <aside className="hidden w-64 flex-col border-r border-line bg-[#faf9f6] p-4 lg:flex">
      {header && <div className="px-2 pt-1">{header}</div>}

      <div className="mt-6 flex flex-1 flex-col gap-6 overflow-y-auto">
        {sections.map((section) => (
          <div key={section.label}>
            <div className="px-3 pb-1.5 text-[10.5px] uppercase tracking-[0.16em] text-ink-4">
              {section.label}
            </div>
            <nav className="flex flex-col gap-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = item.id === activeId;
                const counter = resolveCounter(item.counter);
                return (
                  <a
                    key={item.id}
                    href={item.href}
                    className={
                      'group flex items-center gap-2.5 rounded-[10px] px-3 py-2 text-[13.5px] transition-colors duration-150 motion-reduce:transition-none ' +
                      (isActive
                        ? 'bg-cobalt text-white shadow-[0_6px_18px_-8px_rgba(37,99,235,0.55)]'
                        : 'text-ink-2 hover:bg-[#f0efeb]')
                    }
                  >
                    <Icon size={16} className="flex-none" strokeWidth={1.8} />
                    <span className="flex-1 truncate">{item.label}</span>
                    {counter !== null && (
                      <span
                        className={
                          'ml-auto rounded-full px-2 py-px text-[11px] font-medium ' +
                          (isActive
                            ? ACTIVE_BADGE
                            : counter.badgeClass ?? INACTIVE_BADGE)
                        }
                      >
                        {counter.label}
                      </span>
                    )}
                  </a>
                );
              })}
            </nav>
          </div>
        ))}
      </div>

      {footer && <div className="mt-auto pt-3">{footer}</div>}
    </aside>
  );
}
