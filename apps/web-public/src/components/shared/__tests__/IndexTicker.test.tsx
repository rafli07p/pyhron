import { render, screen } from '@testing-library/react';
import { IndexTicker } from '@/components/shared/IndexTicker';

vi.mock('@/lib/hooks/use-market', () => ({
  useMarketOverview: () => ({ data: undefined }),
}));

vi.mock('next-themes', () => ({
  useTheme: () => ({ theme: 'light', setTheme: vi.fn() }),
}));

describe('IndexTicker', () => {
  it('renders IHSG ticker text', () => {
    render(<IndexTicker />);
    const ihsgElements = screen.getAllByText('IHSG');
    expect(ihsgElements.length).toBeGreaterThan(0);
  });

  it('renders positive change values with text-positive class', () => {
    render(<IndexTicker />);
    // IHSG has +0.59% change which is positive
    const positiveElements = screen.getAllByText('+0.59%');
    expect(positiveElements.length).toBeGreaterThan(0);
    expect(positiveElements[0].className).toContain('text-positive');
  });

  it('renders negative change values with text-negative class', () => {
    render(<IndexTicker />);
    // BBRI has -0.45% change which is negative
    const negativeElements = screen.getAllByText('-0.45%');
    expect(negativeElements.length).toBeGreaterThan(0);
    expect(negativeElements[0].className).toContain('text-negative');
  });

  it('renders multiple ticker items', () => {
    render(<IndexTicker />);
    // The component duplicates tickers for scrolling, so each symbol appears twice
    const bbcaElements = screen.getAllByText('BBCA');
    const tlkmElements = screen.getAllByText('TLKM');
    expect(bbcaElements.length).toBe(2);
    expect(tlkmElements.length).toBe(2);
  });

  it('has Market ticker aria-label', () => {
    render(<IndexTicker />);
    expect(screen.getByLabelText('Market ticker')).toBeInTheDocument();
  });
});
