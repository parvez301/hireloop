import type {
  InputHTMLAttributes,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from 'react';

type Shared = {
  label?: string;
  helper?: string;
  error?: string | null;
};

const INPUT_BASE =
  'block w-full rounded-[10px] border border-line-2 bg-white px-3 py-2 text-[13.5px] text-ink ' +
  'placeholder:text-ink-4 focus:border-ink focus:outline-none focus:ring-4 focus:ring-black/5 ' +
  'disabled:cursor-not-allowed disabled:opacity-60';

function Frame({
  label,
  helper,
  error,
  children,
}: Shared & { children: React.ReactNode }) {
  return (
    <label className="block">
      {label && (
        <span className="mb-1.5 block text-[13px] font-medium text-ink-2">
          {label}
        </span>
      )}
      {children}
      {helper && !error && (
        <span className="mt-1 block text-[12px] text-ink-3">{helper}</span>
      )}
      {error && (
        <span className="mt-1 block text-[12px] text-amber">{error}</span>
      )}
    </label>
  );
}

export function TextField({
  label,
  helper,
  error,
  className = '',
  ...rest
}: Shared & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <Frame label={label} helper={helper} error={error}>
      <input {...rest} className={`${INPUT_BASE} ${className}`} />
    </Frame>
  );
}

export function SelectField({
  label,
  helper,
  error,
  className = '',
  children,
  ...rest
}: Shared & SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <Frame label={label} helper={helper} error={error}>
      <select {...rest} className={`${INPUT_BASE} ${className}`}>
        {children}
      </select>
    </Frame>
  );
}

export function TextareaField({
  label,
  helper,
  error,
  className = '',
  ...rest
}: Shared & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <Frame label={label} helper={helper} error={error}>
      <textarea {...rest} className={`${INPUT_BASE} ${className}`} />
    </Frame>
  );
}
