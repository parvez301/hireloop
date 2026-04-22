type Option<T extends string> = { value: T; label: string };

type Props<T extends string> = {
  options: Option<T>[];
  value: T;
  onChange: (next: T) => void;
  ariaLabel?: string;
};

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  ariaLabel,
}: Props<T>) {
  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className="inline-flex rounded-lg bg-card p-1 gap-1"
    >
      {options.map((option) => {
        const selected = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(option.value)}
            className={
              'rounded-md px-4 py-2 text-[12.5px] font-medium transition-colors duration-150 motion-reduce:transition-none ' +
              (selected
                ? 'bg-white text-ink shadow-[0_1px_0_rgba(31,29,26,0.04),0_4px_8px_-4px_rgba(31,29,26,0.12)]'
                : 'text-ink-3 hover:text-ink')
            }
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
