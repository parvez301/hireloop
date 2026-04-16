import type { FeatureIconName } from '../content/features';

const paths: Record<
  FeatureIconName,
  { viewBox: string; d: string } | { viewBox: string; ds: string[] }
> = {
  search: {
    viewBox: '0 0 24 24',
    d: 'M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15ZM21 21l-5.2-5.2',
  },
  document: {
    viewBox: '0 0 24 24',
    d: 'M7 3h7l5 5v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z M14 3v5h5',
  },
  rss: {
    viewBox: '0 0 24 24',
    ds: [
      'M4 11a9 9 0 0 1 9 9',
      'M4 4a16 16 0 0 1 16 16',
      'M5 19a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z',
    ],
  },
  layers: {
    viewBox: '0 0 24 24',
    ds: ['M12 2 2 7l10 5 10-5-10-5Z', 'M2 17l10 5 10-5', 'M2 12l10 5 10-5'],
  },
  chat: {
    viewBox: '0 0 24 24',
    d: 'M21 12a8 8 0 0 1-8 8H8l-5 3v-3H5a8 8 0 1 1 16-1Z',
  },
  handshake: {
    viewBox: '0 0 24 24',
    d: 'M8 11V7l3-3h2l2 2 2-2h2l3 3v4l-6 6-2-2-6 6-5-5 6-6Z',
  },
};

export function FeatureIcon({ name }: { name: FeatureIconName }) {
  const icon = paths[name];
  return (
    <svg
      className="h-6 w-6 shrink-0 text-accent"
      width={24}
      height={24}
      viewBox={icon.viewBox}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      {'d' in icon ? (
        <path d={icon.d} stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
      ) : (
        icon.ds.map((d) => (
          <path
            key={d}
            d={d}
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ))
      )}
    </svg>
  );
}
