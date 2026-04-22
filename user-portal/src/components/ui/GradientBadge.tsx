export type Grade = 'A' | 'A-' | 'B+' | 'B' | 'C';

const GRADE_GRADIENT: Record<Grade, string> = {
  A: 'from-[#14b8a6] to-[#22c55e]',
  'A-': 'from-[#14b8a6] to-[#2563eb]',
  'B+': 'from-[#2563eb] to-[#7c3aed]',
  B: 'from-[#7c3aed] to-[#a855f7]',
  C: 'from-[#f59e0b] to-[#f97316]',
};

type Props = {
  grade: Grade;
  score: number;
  size?: 'sm' | 'lg';
};

export function GradientBadge({ grade, score, size = 'lg' }: Props) {
  const dim = size === 'lg' ? 'h-16 w-16 text-2xl' : 'h-8 w-8 text-sm';
  return (
    <div
      className={
        `flex flex-none items-center justify-center rounded-2xl bg-gradient-to-br ` +
        `${GRADE_GRADIENT[grade]} ${dim} font-black text-white ` +
        `shadow-[0_12px_28px_-10px_rgba(37,99,235,0.6)]`
      }
      aria-label={`Grade ${grade}, score ${score}`}
    >
      {score}
    </div>
  );
}
