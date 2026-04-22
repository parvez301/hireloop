type Props = {
  values: number[];
  width?: number;
  height?: number;
  stroke?: string;
  fill?: string;
  label?: string;
};

export function Sparkline({
  values,
  width = 112,
  height = 24,
  stroke = '#6b6966',
  fill = 'rgba(107,105,102,0.12)',
  label,
}: Props) {
  if (values.length < 2) {
    return <span className="inline-block text-[11px] text-ink-4">—</span>;
  }
  const max = Math.max(...values, 1);
  const stepX = width / (values.length - 1);
  const points = values.map((value, index) => ({
    x: index * stepX,
    y: height - (value / max) * height,
  }));
  const path = points
    .map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x},${point.y}`)
    .join(' ');
  const area = `${path} L${width},${height} L0,${height} Z`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role={label ? 'img' : undefined}
      aria-label={label}
    >
      <path d={area} fill={fill} />
      <path d={path} fill="none" stroke={stroke} strokeWidth={1.25} />
    </svg>
  );
}
