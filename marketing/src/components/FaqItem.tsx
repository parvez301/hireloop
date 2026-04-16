interface FaqItemProps {
  question: string;
  answer: string;
}

export function FaqItem({ question, answer }: FaqItemProps) {
  return (
    <details className="group border-t border-border py-4 first:border-t-0 first:pt-0">
      <summary className="cursor-pointer list-none text-text-primary font-medium [&::-webkit-details-marker]:hidden">
        <span className="inline-flex w-full items-center justify-between gap-3">
          <span>{question}</span>
          <span className="text-text-secondary transition-transform group-open:rotate-180" aria-hidden>
            ▾
          </span>
        </span>
      </summary>
      <p className="mt-3 text-base text-text-secondary leading-relaxed">{answer}</p>
    </details>
  );
}
