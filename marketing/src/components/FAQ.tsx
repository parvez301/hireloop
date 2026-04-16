import type { FaqItem as FaqEntry } from '../content/faq-home';
import { FaqItem } from './FaqItem';

interface FAQProps {
  id?: string;
  title: string;
  items: FaqEntry[];
}

export function FAQ({ id, title, items }: FAQProps) {
  return (
    <section className="mt-16" id={id} aria-labelledby={id ? `${id}-heading` : undefined}>
      <h2 className="text-3xl font-semibold tracking-tight" id={id ? `${id}-heading` : undefined}>
        {title}
      </h2>
      <div className="mt-8 max-w-3xl">
        {items.map((item) => (
          <FaqItem key={item.q} question={item.q} answer={item.a} />
        ))}
      </div>
    </section>
  );
}
