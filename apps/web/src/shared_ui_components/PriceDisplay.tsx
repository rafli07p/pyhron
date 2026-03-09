import { formatNumber, formatPercent } from '@/design_system/typography_scale';

interface PriceDisplayProps {
  price: number;
  change?: number;
  changePercent?: number;
  size?: 'sm' | 'md' | 'lg';
  showSign?: boolean;
}

const sizeClasses = {
  sm: 'text-xs',
  md: 'text-sm',
  lg: 'text-lg',
};

function getColorClass(value: number | undefined): string {
  if (value === undefined || value === 0) return 'text-bloomberg-text-primary';
  return value > 0 ? 'text-bloomberg-green' : 'text-bloomberg-red';
}

function getArrow(value: number | undefined): string {
  if (value === undefined || value === 0) return '';
  return value > 0 ? '\u25B2' : '\u25BC';
}

export default function PriceDisplay({
  price,
  change,
  changePercent,
  size = 'md',
  showSign = true,
}: PriceDisplayProps) {
  const colorClass = getColorClass(change ?? changePercent);

  return (
    <div className={`inline-flex items-baseline gap-2 font-mono ${sizeClasses[size]}`}>
      <span className="text-bloomberg-text-primary font-semibold tabular-nums">
        {formatNumber(price)}
      </span>
      {change !== undefined && (
        <span className={`${colorClass} tabular-nums`}>
          {getArrow(change)}{' '}
          {showSign && change > 0 ? '+' : ''}
          {formatNumber(change)}
        </span>
      )}
      {changePercent !== undefined && (
        <span className={`${colorClass} tabular-nums text-xxs`}>
          ({formatPercent(changePercent)})
        </span>
      )}
    </div>
  );
}
