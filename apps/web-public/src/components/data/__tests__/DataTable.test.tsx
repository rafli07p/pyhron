import { render, screen, fireEvent } from '@testing-library/react';
import { ScreenerView } from '@/components/data/ScreenerView';
import { mockScreenerResults } from '@/lib/mock/data/instruments';

vi.mock('lucide-react', () => ({
  ArrowUpDown: (props: any) => <div data-testid="arrow-icon" {...props} />,
  Download: (props: any) => <div data-testid="download-icon" {...props} />,
}));

vi.mock('next-auth/react', () => ({
  SessionProvider: ({ children }: any) => children,
  useSession: () => ({ data: null }),
  getSession: () => null,
}));

describe('ScreenerView', () => {
  it('renders correct number of rows matching mockScreenerResults.length', () => {
    render(<ScreenerView />);
    const rows = screen.getAllByRole('row');
    // One header row + data rows
    expect(rows.length - 1).toBe(mockScreenerResults.length);
  });

  it('renders ticker symbols in table cells', () => {
    render(<ScreenerView />);
    expect(screen.getByText('BBCA')).toBeInTheDocument();
    expect(screen.getByText('BBRI')).toBeInTheDocument();
    expect(screen.getByText('TLKM')).toBeInTheDocument();
  });

  it('clicking sort header toggles sort direction', () => {
    render(<ScreenerView />);
    const mktCapHeader = screen.getByRole('columnheader', { name: /Mkt Cap/i });
    // Default sort is market_cap descending
    expect(mktCapHeader.getAttribute('aria-sort')).toBe('descending');

    fireEvent.click(mktCapHeader);
    expect(mktCapHeader.getAttribute('aria-sort')).toBe('ascending');
  });

  it('table has aria-sort on active column header', () => {
    render(<ScreenerView />);
    const headers = screen.getAllByRole('columnheader');
    const sortedHeaders = headers.filter(
      (h) => h.getAttribute('aria-sort') === 'ascending' || h.getAttribute('aria-sort') === 'descending',
    );
    expect(sortedHeaders.length).toBe(1);
  });
});
