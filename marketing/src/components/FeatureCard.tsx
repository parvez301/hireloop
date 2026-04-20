import type { FeatureAccent, FeatureEntry } from '../content/features';

const accentClasses: Record<FeatureAccent, { bar: string; title: string }> = {
  blue: { bar: 'bg-[#2383e2]', title: 'text-[#2383e2]' },
  violet: { bar: 'bg-[#8b5cf6]', title: 'text-[#8b5cf6]' },
  emerald: { bar: 'bg-[#10b981]', title: 'text-[#10b981]' },
  amber: { bar: 'bg-[#f59e0b]', title: 'text-[#d97706]' },
  rose: { bar: 'bg-[#f43f5e]', title: 'text-[#e11d48]' },
  teal: { bar: 'bg-[#14b8a6]', title: 'text-[#0d9488]' },
};

export function FeatureCard({ feature }: { feature: FeatureEntry }) {
  const accent = accentClasses[feature.accent];
  return (
    <div className="group relative pl-5">
      <span aria-hidden className={`absolute left-0 top-1 bottom-1 w-[3px] rounded-full ${accent.bar}`} />
      <h3 className={`flex items-center gap-2 text-xl font-bold tracking-tight ${accent.title}`}>
        <span>{feature.title}</span>
        <span className="text-2xl leading-none" aria-hidden>
          {feature.emoji}
        </span>
      </h3>
      <p className="mt-3 text-base text-text-secondary leading-relaxed">{feature.summary}</p>
    </div>
  );
}
