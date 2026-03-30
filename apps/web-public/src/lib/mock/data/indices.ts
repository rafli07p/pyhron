import { generateGBM } from '../utils';
import type { OHLCVBar } from '@/types/market';

function generateOHLCVData(baseName: string, startPrice: number, seed: number): OHLCVBar[] {
  const gbm = generateGBM(startPrice, 1260, 0.10, 0.22, seed);
  return gbm.map((d) => {
    const dayVol = d.price * 0.015;
    return {
      timestamp: d.date + 'T00:00:00Z',
      open: Math.round((d.price - dayVol * 0.3) * 100) / 100,
      high: Math.round((d.price + dayVol) * 100) / 100,
      low: Math.round((d.price - dayVol) * 100) / 100,
      close: d.price,
      volume: d.volume,
      value: d.volume * d.price,
    };
  });
}

export const mockIndexData: Record<string, OHLCVBar[]> = {
  composite: generateOHLCVData('Composite', 100, 42),
  value: generateOHLCVData('Value', 100, 43),
  momentum: generateOHLCVData('Momentum', 100, 44),
  quality: generateOHLCVData('Quality', 100, 45),
  lowvol: generateOHLCVData('Low Volatility', 100, 46),
};

export const mockIndexPerformance = [
  { index: 'Pyhron Composite', level: 142.35, d1: 0.59, w1: 1.23, m1: 2.45, ytd: 8.92, y1: 14.25 },
  { index: 'Pyhron Value', level: 138.92, d1: 0.34, w1: 0.89, m1: 1.87, ytd: 6.45, y1: 11.82 },
  { index: 'Pyhron Momentum', level: 156.78, d1: 1.12, w1: 2.45, m1: 4.23, ytd: 15.34, y1: 22.18 },
  { index: 'Pyhron Quality', level: 145.23, d1: 0.45, w1: 1.12, m1: 2.12, ytd: 9.87, y1: 16.45 },
  { index: 'Pyhron Low Vol', level: 128.45, d1: 0.12, w1: 0.45, m1: 0.98, ytd: 4.23, y1: 8.92 },
];
