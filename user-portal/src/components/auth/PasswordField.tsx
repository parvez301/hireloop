import { useState, type InputHTMLAttributes } from 'react';

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & {
  label?: string;
  strength?: boolean;
};

function scoreOf(value: string): number {
  let score = 0;
  if (value.length >= 10) score += 1;
  if (/[A-Z]/.test(value) && /[a-z]/.test(value)) score += 1;
  if (/\d/.test(value)) score += 1;
  if (/[^A-Za-z0-9]/.test(value)) score += 1;
  return score;
}

const LABELS = ['—', 'Weak', 'Okay', 'Good', 'Strong'] as const;
const BAR_TINTS = [
  '', // 0
  'bg-red-400', // 1
  'bg-amber', // 2
  'bg-cobalt', // 3
  'bg-teal', // 4
] as const;

export function PasswordField({
  label = 'Password',
  strength = false,
  value,
  onChange,
  ...rest
}: Props) {
  const [show, setShow] = useState(false);
  const stringValue = typeof value === 'string' ? value : '';
  const score = scoreOf(stringValue);

  return (
    <label className="block">
      {label && (
        <span className="mb-1.5 block text-[12px] font-medium text-ink-2">
          {label}
        </span>
      )}
      <div className="flex items-center rounded-xl border border-line-2 bg-white focus-within:border-ink focus-within:ring-4 focus-within:ring-black/5">
        <input
          {...rest}
          type={show ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          className="block w-full bg-transparent px-3.5 py-3 text-[14px] text-ink placeholder:text-ink-4 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
        />
        <button
          type="button"
          onClick={() => setShow((current) => !current)}
          className="mr-2 rounded-md px-2 py-1 text-[12px] text-ink-3 hover:bg-card"
        >
          {show ? 'Hide' : 'Show'}
        </button>
      </div>
      {strength && (
        <div className="mt-2">
          <div className="flex gap-1" aria-hidden>
            {[1, 2, 3, 4].map((slot) => (
              <span
                key={slot}
                className={
                  'h-1 flex-1 rounded-full ' +
                  (score >= slot ? BAR_TINTS[score] : 'bg-line-2')
                }
              />
            ))}
          </div>
          <div className="mt-1.5 flex justify-between text-[11px] text-ink-3">
            <span>10+ chars · number · symbol · mixed case</span>
            <span className="text-ink-4">{LABELS[score]}</span>
          </div>
        </div>
      )}
    </label>
  );
}
