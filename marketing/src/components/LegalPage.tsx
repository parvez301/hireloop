import { marked } from 'marked';

const legalProseClass =
  'legal-prose text-text-secondary [&_a]:text-accent [&_a]:underline [&_h2]:mt-10 [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:text-text-primary [&_h2]:first:mt-0 [&_p]:mt-3 [&_p]:leading-relaxed [&_ul]:mt-3 [&_ul]:list-disc [&_ul]:pl-5 [&_strong]:text-text-primary';

interface LegalPageProps {
  title: string;
  markdown: string;
}

export function LegalPage({ title, markdown }: LegalPageProps) {
  const html = marked(markdown, { async: false });
  return (
    <article className="py-12">
      <div className={`mx-auto max-w-2xl px-6 ${legalProseClass}`}>
        <h1 className="text-3xl font-semibold tracking-tight text-text-primary">{title}</h1>
        <div className="mt-8" dangerouslySetInnerHTML={{ __html: html }} />
      </div>
    </article>
  );
}
