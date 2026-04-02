import { describe, it, expect } from 'vitest';
import { IDX } from '@/constants/idx';

describe('IDX constants', () => {
  describe('getTickSize', () => {
    it('returns 1 for prices <= 200', () => {
      expect(IDX.getTickSize(100)).toBe(1);
      expect(IDX.getTickSize(200)).toBe(1);
    });

    it('returns 2 for prices 201-500', () => {
      expect(IDX.getTickSize(201)).toBe(2);
      expect(IDX.getTickSize(500)).toBe(2);
    });

    it('returns 5 for prices 501-2000', () => {
      expect(IDX.getTickSize(501)).toBe(5);
      expect(IDX.getTickSize(2000)).toBe(5);
    });

    it('returns 10 for prices 2001-5000', () => {
      expect(IDX.getTickSize(2001)).toBe(10);
      expect(IDX.getTickSize(5000)).toBe(10);
    });

    it('returns 25 for prices > 5000', () => {
      expect(IDX.getTickSize(5001)).toBe(25);
      expect(IDX.getTickSize(10000)).toBe(25);
    });
  });

  describe('estimateCost', () => {
    it('calculates buy commission correctly', () => {
      const result = IDX.estimateCost('buy', 10000, 100);
      expect(result.value).toBe(1_000_000);
      expect(result.commission).toBe(1_500); // 0.15%
      expect(result.tax).toBe(0);
      expect(result.total).toBe(1_001_500);
    });

    it('calculates sell commission and tax correctly', () => {
      const result = IDX.estimateCost('sell', 10000, 100);
      expect(result.value).toBe(1_000_000);
      expect(result.commission).toBe(2_500); // 0.25%
      expect(result.tax).toBe(1_000); // 0.1%
      expect(result.total).toBe(1_002_500);
    });
  });

  it('has correct lot size', () => {
    expect(IDX.LOT_SIZE).toBe(100);
  });

  it('disables short selling', () => {
    expect(IDX.SHORT_SELLING).toBe(false);
  });
});
