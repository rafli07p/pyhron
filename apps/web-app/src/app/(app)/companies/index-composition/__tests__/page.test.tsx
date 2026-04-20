import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import IndexCompositionPage from '../page';
import { AVAILABLE_PEERS, BBCA_INDEX_ROWS } from '@/lib/index-composition/data';
import type { IndexMembershipResponse } from '@/lib/index-composition/types';

vi.mock('next-auth/react', () => ({
  useSession: () => ({ data: { accessToken: 'test-token' }, status: 'authenticated' }),
}));

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <IndexCompositionPage />
    </QueryClientProvider>,
  );
}

const mockResponse: IndexMembershipResponse = {
  symbol: 'BBCA',
  industry: 'Banks',
  asOfDate: '2025-09-30',
  availablePeers: AVAILABLE_PEERS,
  rows: BBCA_INDEX_ROWS,
};

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(mockResponse) })),
  );
});

describe('IndexCompositionPage', () => {
  it('renders the table with default BBCA data', async () => {
    renderPage();
    expect(await screen.findByText('Index Composition Viewer')).toBeInTheDocument();
    // Card title for default (weight) tab
    await waitFor(() => {
      expect(screen.getByText('Index Analysis by Weight (%)')).toBeInTheDocument();
    });
    // A known index from BBCA_INDEX_ROWS renders
    expect(await screen.findByText('MSCI Indonesia IMI')).toBeInTheDocument();
    expect(screen.getByText('MSCI Indonesia ESG Leaders')).toBeInTheDocument();
  });

  it('switches card title when tab changes', async () => {
    renderPage();
    // Wait for initial render
    await screen.findByText('Index Analysis by Weight (%)');
    fireEvent.click(screen.getByRole('button', { name: 'Index Analysis - US Dollar' }));
    expect(screen.getByText('Index Analysis by Indexed AUM (US Dollar)')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Sustainability & Climate Metrics' }));
    const esgTitles = screen.getAllByText('Sustainability & Climate Metrics');
    // Both the tab button and the card title render the text
    expect(esgTitles.length).toBeGreaterThanOrEqual(2);
  });

  it('opens peer-group modal and saving updates column count', async () => {
    renderPage();
    // Wait for table data (row rendered) before counting columns
    await screen.findByText('MSCI Indonesia ESG Leaders');
    // Main table is the first table on the page (AUM analysis card adds a second table)
    const mainTable = screen.getAllByRole('table')[0]!;
    const header = within(mainTable).getAllByRole('columnheader');
    // First 6 cols are metadata; peer cols come after
    const initialPeerCols = header.length - 6;
    expect(initialPeerCols).toBe(4);

    fireEvent.click(screen.getByRole('button', { name: 'Edit Peer Group' }));
    const dialog = await screen.findByRole('dialog');
    // Check an additional peer (BRIS)
    const brisCheckbox = within(dialog).getByRole('checkbox', { name: /BRIS/i });
    fireEvent.click(brisCheckbox);
    fireEvent.click(within(dialog).getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      const afterMain = screen.getAllByRole('table')[0]!;
      const afterHeader = within(afterMain).getAllByRole('columnheader');
      expect(afterHeader.length - 6).toBe(5);
    });
  });
});
