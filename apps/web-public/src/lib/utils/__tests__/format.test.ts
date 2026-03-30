import { describe, it, expect } from 'vitest';
import { formatIDR, formatPct, parseWsDecimal, pctColor, formatDate } from '../format';

describe('formatIDR', () => {
  it('formats trillions', () => expect(formatIDR(1_500_000_000_000)).toBe('Rp 1.5T'));
  it('formats billions', () => expect(formatIDR(250_000_000_000)).toBe('Rp 250.0B'));
  it('formats millions', () => expect(formatIDR(50_000_000)).toBe('Rp 50.0M'));
  it('handles null', () => expect(formatIDR(null)).toBe('\u2014'));
  it('handles undefined', () => expect(formatIDR(undefined)).toBe('\u2014'));
  it('handles zero', () => expect(formatIDR(0)).toContain('0'));
  it('handles negative trillions', () => expect(formatIDR(-1_200_000_000_000)).toBe('Rp -1.2T'));
});

describe('formatPct', () => {
  it('positive signed', () => expect(formatPct(2.55)).toBe('+2.55%'));
  it('negative', () => expect(formatPct(-1.2)).toBe('-1.20%'));
  it('zero', () => expect(formatPct(0)).toBe('0.00%'));
  it('null', () => expect(formatPct(null)).toBe('\u2014'));
  it('unsigned', () => expect(formatPct(2.55, false)).toBe('2.55%'));
});

describe('parseWsDecimal', () => {
  it('parses string', () => expect(parseWsDecimal('1234.56')).toBe(1234.56));
  it('handles empty', () => expect(parseWsDecimal('')).toBe(0));
  it('handles invalid', () => expect(parseWsDecimal('abc')).toBe(0));
});

describe('pctColor', () => {
  it('returns positive class', () => expect(pctColor(1.5)).toBe('text-positive'));
  it('returns negative class', () => expect(pctColor(-0.5)).toBe('text-negative'));
  it('returns muted for null', () => expect(pctColor(null)).toBe('text-muted'));
  it('returns positive for zero', () => expect(pctColor(0)).toBe('text-positive'));
});

describe('formatDate', () => {
  it('formats ISO date', () => {
    const result = formatDate('2026-03-15T00:00:00Z');
    expect(result).toContain('Mar');
    expect(result).toContain('2026');
  });
});
