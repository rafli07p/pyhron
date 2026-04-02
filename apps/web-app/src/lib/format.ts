import { formatInTimeZone } from 'date-fns-tz';
import { formatDistanceToNow } from 'date-fns';
import { IDX } from '@/constants/idx';

const idrFormatter = new Intl.NumberFormat(IDX.LOCALE, {
  style: 'currency',
  currency: IDX.CURRENCY,
  maximumFractionDigits: 0,
});

const idrCompactFormatter = new Intl.NumberFormat(IDX.LOCALE, {
  style: 'currency',
  currency: IDX.CURRENCY,
  notation: 'compact',
  maximumFractionDigits: 1,
});

const numberFormatter = new Intl.NumberFormat(IDX.LOCALE);

const percentFormatter = new Intl.NumberFormat(IDX.LOCALE, {
  style: 'percent',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatIDR(value: number): string {
  return idrFormatter.format(value);
}

export function formatIDRCompact(value: number): string {
  return idrCompactFormatter.format(value);
}

export function formatNumber(value: number): string {
  return numberFormatter.format(value);
}

export function formatPercent(value: number): string {
  return percentFormatter.format(value / 100);
}

export function formatWIB(date: string | Date, format = 'dd MMM yyyy HH:mm'): string {
  return formatInTimeZone(new Date(date), IDX.TIMEZONE, format);
}

export function formatRelativeTime(date: string | Date): string {
  return formatDistanceToNow(new Date(date), { addSuffix: true });
}

export function formatVolume(volume: number): string {
  if (volume >= 1_000_000_000) return `${(volume / 1_000_000_000).toFixed(1)}B`;
  if (volume >= 1_000_000) return `${(volume / 1_000_000).toFixed(1)}M`;
  if (volume >= 1_000) return `${(volume / 1_000).toFixed(1)}K`;
  return volume.toString();
}
