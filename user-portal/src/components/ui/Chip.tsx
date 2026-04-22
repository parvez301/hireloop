import { X, Plus } from 'lucide-react';

export type ChipVariant = 'on' | 'add' | 'suggest';

type Props = {
  label: string;
  variant?: ChipVariant;
  onClick?: () => void;
  onRemove?: () => void;
};

export function Chip({ label, variant = 'on', onClick, onRemove }: Props) {
  if (variant === 'on') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-ink px-2.5 py-1 text-[12px] font-medium text-white">
        {label}
        {onRemove && (
          <button
            type="button"
            onClick={onRemove}
            aria-label={`Remove ${label}`}
            className="-mr-0.5 ml-0.5 inline-flex h-4 w-4 items-center justify-center rounded-full text-white/55 hover:text-white"
          >
            <X size={12} />
          </button>
        )}
      </span>
    );
  }
  if (variant === 'add') {
    return (
      <button
        type="button"
        onClick={onClick}
        className="inline-flex items-center gap-1 rounded-full border border-dashed border-line-2 bg-white px-3 py-1 text-[12px] text-ink-3 hover:border-ink hover:text-ink"
      >
        <Plus size={12} />
        {label}
      </button>
    );
  }
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1 rounded-full border border-line bg-white px-3 py-1 text-[12px] text-ink-3 hover:text-ink"
    >
      <Plus size={12} />
      {label}
    </button>
  );
}

type SetProps = {
  values: string[];
  suggestions?: string[];
  onChange: (next: string[]) => void;
  addLabel?: string;
  addable?: boolean;
};

export function ChipSet({
  values,
  suggestions = [],
  onChange,
  addLabel = '+ Add',
  addable = true,
}: SetProps) {
  const lowerValues = new Set(values.map((v) => v.toLowerCase()));
  const visibleSuggestions = suggestions.filter(
    (sample) => !lowerValues.has(sample.toLowerCase()),
  );

  function remove(label: string) {
    onChange(values.filter((value) => value !== label));
  }
  function add(label: string) {
    if (!label) return;
    if (lowerValues.has(label.toLowerCase())) return;
    onChange([...values, label]);
  }

  return (
    <div className="flex flex-wrap gap-2">
      {values.map((value) => (
        <Chip
          key={value}
          label={value}
          variant="on"
          onRemove={() => remove(value)}
        />
      ))}
      {visibleSuggestions.map((value) => (
        <Chip
          key={`sg-${value}`}
          label={value}
          variant="suggest"
          onClick={() => add(value)}
        />
      ))}
      {addable && (
        <Chip
          label={addLabel.replace(/^\+\s*/, '')}
          variant="add"
          onClick={() => {
            const next = prompt('Add:')?.trim();
            if (next) add(next);
          }}
        />
      )}
    </div>
  );
}
