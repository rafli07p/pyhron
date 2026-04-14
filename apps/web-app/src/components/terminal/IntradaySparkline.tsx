interface IntradaySparklineProps {
  points: number[];
  positive: boolean;
  width?: number;
  height?: number;
}

export function IntradaySparkline({
  points,
  positive,
  width = 80,
  height = 32,
}: IntradaySparklineProps) {
  if (points.length < 2) return null;

  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;

  const pad = 2;
  const chartH = height - pad * 2;

  const coords = points.map((p, i) => {
    const x = (i / (points.length - 1)) * width;
    const y = pad + chartH - ((p - min) / range) * chartH;
    return { x, y };
  });

  const linePath = coords
    .map((c, i) => `${i === 0 ? 'M' : 'L'}${c.x.toFixed(1)},${c.y.toFixed(1)}`)
    .join(' ');

  const fillPath = `${linePath} L${width},${height} L0,${height} Z`;

  const color = positive ? '#16a34a' : '#dc2626';
  const gradId = `spark-${positive ? 'up' : 'dn'}`;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height} className="shrink-0">
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.2" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={fillPath} fill={`url(#${gradId})`} />
      <path
        d={linePath}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
