import { describe, it, expect } from 'vitest';
import { formatVolume } from '@/lib/format';

describe('formatVolume', () => {
  it('formats billions', () => {
    expect(formatVolume(1_500_000_000)).toBe('1.5B');
  });

  it('formats millions', () => {
    expect(formatVolume(45_200_000)).toBe('45.2M');
  });

  it('formats thousands', () => {
    expect(formatVolume(1_500)).toBe('1.5K');
  });

  it('formats small numbers', () => {
    expect(formatVolume(500)).toBe('500');
  });
});
