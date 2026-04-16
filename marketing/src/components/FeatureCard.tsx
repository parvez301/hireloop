import type { FeatureEntry } from '../content/features';
import { FeatureIcon } from './FeatureIcon';

export function FeatureCard({ feature }: { feature: FeatureEntry }) {
  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <FeatureIcon name={feature.icon} />
      <h3 className="mt-4 text-xl font-semibold">{feature.title}</h3>
      <p className="mt-2 text-base text-text-secondary leading-relaxed">{feature.summary}</p>
    </div>
  );
}
