export function formatIDR(value: number | null | undefined): string {
  if (value == null) return '\u2014';
  if (Math.abs(value) >= 1e12) return `Rp ${(value / 1e12).toFixed(1)}T`;
  if (Math.abs(value) >= 1e9) return `Rp ${(value / 1e9).toFixed(1)}B`;
  if (Math.abs(value) >= 1e6) return `Rp ${(value / 1e6).toFixed(1)}M`;
  return new Intl.NumberFormat('id-ID', {
    style: 'currency', currency: 'IDR', minimumFractionDigits: 0,
  }).format(value);
}

export function formatPct(value: number | null | undefined, signed = true): string {
  if (value == null) return '\u2014';
  const f = value.toFixed(2);
  return signed && value > 0 ? `+${f}%` : `${f}%`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
}

export function pctColor(value: number | null | undefined): string {
  if (value == null) return 'text-muted';
  return value >= 0 ? 'text-positive' : 'text-negative';
}

export function parseWsDecimal(str: string): number {
  return parseFloat(str) || 0;
}
