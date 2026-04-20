import type { FaqItem as FaqEntry } from '../content/faq-home';
import { FaqItem } from './FaqItem';

interface FAQProps {
  id?: string;
  title: string;
  items: FaqEntry[];
}

export function FAQ({ id, title, items }: FAQProps) {
  return (
    <section className="py-4" id={id} aria-labelledby={id ? `${id}-heading` : undefined}>
      <p className="text-xs font-medium uppercase tracking-wider text-accent">FAQ</p>
      <h2 className="mt-3 text-3xl font-bold tracking-tight md:text-4xl" id={id ? `${id}-heading` : undefined}>
        {title}
      </h2>
      <div className="mt-10 max-w-3xl">
        {items.map((item) => (
          <FaqItem key={item.q} question={item.q} answer={item.a} />
        ))}
      </div>
    </section>
  );
}
