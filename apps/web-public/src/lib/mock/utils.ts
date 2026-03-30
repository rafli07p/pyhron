// Geometric Brownian Motion generator for realistic price data
export function generateGBM(
  startPrice: number,
  days: number,
  drift: number = 0.10,
  volatility: number = 0.22,
  seed: number = 42,
): { date: string; price: number; volume: number }[] {
  const dt = 1 / 252;
  const data: { date: string; price: number; volume: number }[] = [];
  let price = startPrice;
  let rng = seed;

  function nextRandom(): number {
    rng = (rng * 16807 + 0) % 2147483647;
    return rng / 2147483647;
  }

  function boxMuller(): number {
    const u1 = nextRandom();
    const u2 = nextRandom();
    return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
  }

  const startDate = new Date('2021-01-04');
  for (let i = 0; i < days; i++) {
    const date = new Date(startDate);
    date.setDate(date.getDate() + Math.floor(i * 7 / 5));
    const z = boxMuller();
    price = price * Math.exp((drift - 0.5 * volatility * volatility) * dt + volatility * Math.sqrt(dt) * z);
    const volume = Math.floor(5_000_000 + nextRandom() * 50_000_000);
    data.push({
      date: date.toISOString().split('T')[0],
      price: Math.round(price * 100) / 100,
      volume,
    });
  }
  return data;
}

export function randomBetween(min: number, max: number, seed: number): number {
  const rng = ((seed * 16807 + 0) % 2147483647) / 2147483647;
  return min + rng * (max - min);
}
