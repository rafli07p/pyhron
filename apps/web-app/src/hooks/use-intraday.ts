import { useQuery } from '@tanstack/react-query';

export interface IntradayData {
  symbol: string;
  current: number;
  open: number;
  change: number;
  points: number[];
  timestamps: string[];
  lastUpdate: string;
}

function isIDXMarketOpen(): boolean {
  const now = new Date();
  const wibHour = (now.getUTCHours() + 7) % 24;
  const wibMinute = now.getUTCMinutes();
  const day = now.getDay();

  if (day === 0 || day === 6) return false;

  const t = wibHour * 60 + wibMinute;
  // Session I: 09:00-11:30, Session II: 13:30-15:10
  return (t >= 540 && t <= 690) || (t >= 810 && t <= 910);
}

export function useIntraday(symbol: string) {
  return useQuery<IntradayData>({
    queryKey: ['intraday', symbol],
    queryFn: async () => {
      const res = await fetch(`/api/v1/markets/intraday/${encodeURIComponent(symbol)}`);
      if (!res.ok) throw new Error('Intraday fetch failed');
      return res.json() as Promise<IntradayData>;
    },
    refetchInterval: isIDXMarketOpen() ? 30_000 : false,
    staleTime: 15_000,
    enabled: !!symbol,
  });
}
