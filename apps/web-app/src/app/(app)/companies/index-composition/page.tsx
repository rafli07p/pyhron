'use client';

import {
  Fragment,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from 'react';
import { useSession } from 'next-auth/react';
import { useQuery } from '@tanstack/react-query';
import {
  Check,
  ChevronDown,
  Filter as FilterIcon,
  Info,
  Maximize2,
  MoreVertical,
  Search as SearchIcon,
  X,
  Minimize2,
} from 'lucide-react';

import {
  AS_OF_DATES,
  AVAILABLE_PEERS,
  BBCA_SUSTAINABILITY,
  DEFAULT_PEER_SYMBOLS,
  type SustainabilityMetrics,
} from '@/lib/index-composition/data';
import { rowsToCsv } from '@/lib/index-composition/csv';
import type {
  EsgRating,
  IndexMembershipResponse,
  IndexRow,
  TabKey,
} from '@/lib/index-composition/types';
import { useCompanyStore } from '@/stores/company';

const MAX_PEERS = 8;

const TAB_LABELS: Record<TabKey, string> = {
  weight: 'Index Analysis - Weight (%)',
  usd: 'Index Analysis - US Dollar',
  esg: 'Sustainability & Climate Metrics',
};

const CARD_TITLES: Record<TabKey, string> = {
  weight: 'Index Analysis by Weight (%)',
  usd: 'Index Analysis by Indexed AUM (US Dollar)',
  esg: 'Sustainability & Climate Metrics',
};

type SortKey = 'rank' | 'indexCode' | 'indexName' | 'nextRebalancingDate' | 'indexedAumMillionUsd';
type SortDir = 'asc' | 'desc';

// Date selection is UI-only; full historical data pipeline is out of scope for this change.

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'] as const;

function formatAsOfDate(iso: string): string {
  const parts = iso.split('-');
  const y = parts[0] ?? '';
  const m = parts[1] ?? '01';
  const d = parts[2] ?? '01';
  const monthName = MONTH_NAMES[parseInt(m, 10) - 1] ?? '';
  return `${d}-${monthName}-${y}`;
}

function formatRebalDate(iso: string | null): string {
  if (!iso) return '—';
  return formatAsOfDate(iso);
}

function esgBadgeColor(rating: EsgRating): { bg: string; fg: string } {
  if (rating === 'AAA' || rating === 'AA') return { bg: 'var(--color-positive-bg)', fg: 'var(--color-positive)' };
  if (rating === 'A' || rating === 'BBB') return { bg: '#FFF4D6', fg: '#8A5B00' };
  return { bg: 'var(--color-negative-bg)', fg: 'var(--color-negative)' };
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function IndexCompositionPage() {
  const { data: session } = useSession();
  const { selectedSymbol, selectedName, setSelected } = useCompanyStore();

  const [asOfDate, setAsOfDate] = useState<string>(AS_OF_DATES[0] ?? '2025-09-30');
  const [nameQuery, setNameQuery] = useState<string>('');
  // Store non-subject peers only; subject is always prepended at render time.
  const [peerExtras, setPeerExtras] = useState<string[]>(
    DEFAULT_PEER_SYMBOLS.filter(s => s !== 'BBCA'),
  );
  const [activeTab, setActiveTab] = useState<TabKey>('weight');
  const [sort, setSort] = useState<{ key: SortKey; dir: SortDir } | null>(null);

  const [peerModalOpen, setPeerModalOpen] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [filterEsgOnly, setFilterEsgOnly] = useState(false);
  const [filterHideNotListed, setFilterHideNotListed] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [moreMenuOpen, setMoreMenuOpen] = useState(false);
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const [companyPickerOpen, setCompanyPickerOpen] = useState(false);

  const authHeader = useCallback((): Record<string, string> => {
    const token = (session as { accessToken?: string } | null)?.accessToken;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [session]);

  const membershipQuery = useQuery<IndexMembershipResponse>({
    queryKey: ['index-membership', selectedSymbol],
    queryFn: async () => {
      const res = await fetch(
        `/api/companies/index-membership/${encodeURIComponent(selectedSymbol)}`,
        { headers: authHeader() },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    },
    staleTime: 60_000,
  });

  const rows = useMemo(() => membershipQuery.data?.rows ?? [], [membershipQuery.data]);
  const industry = membershipQuery.data?.industry ?? 'Banks';

  // Always-current peer column list: subject symbol prepended, then extras (deduped).
  const selectedPeers = useMemo(
    () => [selectedSymbol, ...peerExtras.filter(s => s !== selectedSymbol)].slice(0, MAX_PEERS),
    [selectedSymbol, peerExtras],
  );

  // Escape key: close fullscreen or any open overlay
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key !== 'Escape') return;
      if (fullscreen) setFullscreen(false);
      else if (peerModalOpen) setPeerModalOpen(false);
      else if (companyPickerOpen) setCompanyPickerOpen(false);
      else if (filterOpen) setFilterOpen(false);
      else if (moreMenuOpen) setMoreMenuOpen(false);
      else if (exportMenuOpen) setExportMenuOpen(false);
    }
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [fullscreen, peerModalOpen, companyPickerOpen, filterOpen, moreMenuOpen, exportMenuOpen]);

  const filteredRows = useMemo(() => {
    let out = rows;
    if (nameQuery.trim()) {
      const q = nameQuery.toLowerCase();
      out = out.filter(r => r.isParent || r.indexName.toLowerCase().includes(q));
    }
    if (filterEsgOnly) {
      out = out.filter(r => r.isParent || r.esg !== undefined);
    }
    if (filterHideNotListed) {
      out = out.filter(r => r.isParent || (r.weights[selectedSymbol] ?? null) !== null);
    }
    return out;
  }, [rows, nameQuery, filterEsgOnly, filterHideNotListed, selectedSymbol]);

  const sortedRows = useMemo(() => {
    if (!sort) return filteredRows;
    const parents = filteredRows.filter(r => r.isParent);
    const children = [...filteredRows.filter(r => !r.isParent)].sort((a, b) => {
      const av = a[sort.key];
      const bv = b[sort.key];
      if (av === null && bv === null) return 0;
      if (av === null) return 1;
      if (bv === null) return -1;
      if (typeof av === 'number' && typeof bv === 'number') return sort.dir === 'asc' ? av - bv : bv - av;
      return sort.dir === 'asc'
        ? String(av).localeCompare(String(bv))
        : String(bv).localeCompare(String(av));
    });
    return [...parents, ...children];
  }, [filteredRows, sort]);

  const activeFilterCount = (filterEsgOnly ? 1 : 0) + (filterHideNotListed ? 1 : 0);

  const toggleSort = useCallback((key: SortKey) => {
    setSort(prev => {
      if (!prev || prev.key !== key) return { key, dir: 'desc' };
      if (prev.dir === 'desc') return { key, dir: 'asc' };
      return null;
    });
  }, []);

  const resetFilters = useCallback(() => {
    setNameQuery('');
    setFilterEsgOnly(false);
    setFilterHideNotListed(false);
    setSort(null);
  }, []);

  const doExport = useCallback(
    (kind: 'csv' | 'json' | 'clipboard') => {
      const csv = rowsToCsv(sortedRows, selectedPeers);
      const baseFilename = `${selectedSymbol.toLowerCase()}-index-composition-${asOfDate}`;
      if (kind === 'clipboard') {
        void navigator.clipboard.writeText(csv);
      } else if (kind === 'csv') {
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
        triggerDownload(URL.createObjectURL(blob), `${baseFilename}.csv`);
      } else {
        const json = JSON.stringify({ symbol: selectedSymbol, asOfDate, peers: selectedPeers, rows: sortedRows }, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        triggerDownload(URL.createObjectURL(blob), `${baseFilename}.json`);
      }
      setExportMenuOpen(false);
    },
    [sortedRows, selectedPeers, selectedSymbol, asOfDate],
  );

  const copyTable = useCallback(() => {
    const tsv = sortedRows
      .map(r => [r.rank ?? '', r.indexCode, r.indexName, r.nextRebalancingDate ?? '', r.indexedAumMillionUsd ?? '', ...selectedPeers.map(p => r.weights[p] ?? '')].join('\t'))
      .join('\n');
    void navigator.clipboard.writeText(tsv);
    setMoreMenuOpen(false);
  }, [sortedRows, selectedPeers]);

  const subjectDisplay = membershipQuery.data
    ? selectedName || AVAILABLE_PEERS.find(p => p.symbol === selectedSymbol)?.name || selectedSymbol
    : selectedSymbol;

  const cardContent = (
    <div className="card-base" style={fullscreen ? undefined : { margin: '12px 24px' }}>
      <div className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-3">
        <h2 className="text-[13px] font-semibold text-[var(--color-text-primary)]">
          {CARD_TITLES[activeTab]}
        </h2>
        {fullscreen && (
          <button
            type="button"
            onClick={() => setFullscreen(false)}
            className="flex h-6 w-6 items-center justify-center rounded border border-[var(--color-border)] hover:bg-[var(--color-border-subtle)]"
            aria-label="Exit fullscreen"
          >
            <Minimize2 size={13} className="text-[var(--color-text-muted)]" />
          </button>
        )}
      </div>
      <DataTable
        rows={sortedRows}
        peers={selectedPeers}
        tab={activeTab}
        sort={sort}
        onSort={toggleSort}
        loading={membershipQuery.isLoading}
      />
    </div>
  );

  return (
    <div className="flex w-full flex-1 flex-col bg-[var(--color-bg-page)]">
      {/* A. Page header */}
      <div className="flex items-center justify-between border-b border-[var(--color-border)] px-6 py-5">
        <h1 className="text-[20px] font-semibold text-[var(--color-text-primary)]">
          Index Composition Viewer
        </h1>
        <div className="flex items-center gap-6 text-[13px]">
          <a href="/methodology" target="_blank" rel="noreferrer" className="link-blue">
            Index Methodologies
          </a>
          <a href="/help/index-composition" target="_blank" rel="noreferrer" className="link-blue">
            User Guide
          </a>
          <div className="relative">
            <button
              type="button"
              onClick={() => setExportMenuOpen(o => !o)}
              className="link-blue flex items-center gap-1"
            >
              Export
              <ChevronDown size={13} />
            </button>
            {exportMenuOpen && (
              <div className="absolute right-0 top-full z-40 mt-1 w-48 rounded-md border border-[var(--color-border)] bg-white shadow-lg">
                {([
                  ['Export as CSV', 'csv'],
                  ['Export as JSON', 'json'],
                  ['Copy to clipboard', 'clipboard'],
                ] as const).map(([label, kind]) => (
                  <button
                    key={kind}
                    type="button"
                    onClick={() => doExport(kind)}
                    className="block w-full px-3 py-2 text-left text-[12px] hover:bg-[var(--color-border-subtle)]"
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* B. Description */}
      <p className="mt-2 max-w-[1000px] px-6 text-[13px] leading-relaxed text-[var(--color-text-secondary)]">
        Identify the financial impact (through indexed AUM flows) of a company&apos;s inclusion or exclusion
        in MSCI Indonesia&apos;s Sustainability and Climate indexes. Inclusion in these indexes can have a
        measurable impact on shareholder composition given the AUM benchmarked to MSCI Sustainability and
        Climate indexes.
      </p>

      {/* C. Controls row */}
      <div className="grid grid-cols-[220px_180px_240px_1fr] items-end gap-5 px-6 py-4">
        <CompanyPicker
          symbol={selectedSymbol}
          display={subjectDisplay}
          open={companyPickerOpen}
          setOpen={setCompanyPickerOpen}
          onSelect={(sym, name) => {
            setSelected(sym, name);
            setCompanyPickerOpen(false);
          }}
        />
        <AsOfDateSelect value={asOfDate} onChange={setAsOfDate} />
        <IndexSearchField value={nameQuery} onChange={setNameQuery} />
        <div>
          <button
            type="button"
            onClick={() => setPeerModalOpen(true)}
            className="h-9 rounded bg-[var(--color-blue-primary)] px-4 text-[13px] font-semibold text-white hover:bg-[var(--color-blue-dark)]"
          >
            Edit Peer Group
          </button>
        </div>
      </div>

      {/* D. Industry line */}
      <p className="px-6 text-[13px]">
        <span className="text-[var(--color-text-muted)]">Industry: </span>
        <span className="font-semibold text-[var(--color-text-primary)]">{industry}</span>
      </p>

      {/* E. Tabs row */}
      <div className="mt-4 flex items-center justify-between px-6">
        <div className="flex gap-2">
          {(Object.keys(TAB_LABELS) as TabKey[]).map((key) => {
            const active = activeTab === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => setActiveTab(key)}
                className={`h-9 rounded border px-5 text-[13px] transition-colors ${
                  active
                    ? 'border-[var(--color-blue-primary)] bg-[var(--color-blue-primary)] font-semibold text-white'
                    : 'border-[var(--color-border)] bg-white text-[var(--color-text-secondary)] hover:bg-[var(--color-border-subtle)]'
                }`}
              >
                {TAB_LABELS[key]}
              </button>
            );
          })}
        </div>
        <div className="flex items-center gap-1">
          <div className="relative">
            <IconButton
              label="Filters"
              onClick={() => setFilterOpen(o => !o)}
              active={filterOpen}
            >
              <FilterIcon size={13} />
              {activeFilterCount > 0 && (
                <span className="absolute -right-1 -top-1 flex h-[14px] min-w-[14px] items-center justify-center rounded-full bg-[var(--color-blue-primary)] px-1 text-[9px] font-bold text-white">
                  {activeFilterCount}
                </span>
              )}
            </IconButton>
            {filterOpen && (
              <FilterPopover
                esgOnly={filterEsgOnly}
                setEsgOnly={setFilterEsgOnly}
                hideNotListed={filterHideNotListed}
                setHideNotListed={setFilterHideNotListed}
                onClose={() => setFilterOpen(false)}
              />
            )}
          </div>
          <IconButton
            label={fullscreen ? 'Exit fullscreen' : 'Fullscreen'}
            onClick={() => setFullscreen(v => !v)}
          >
            {fullscreen ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
          </IconButton>
          <div className="relative">
            <IconButton
              label="More"
              onClick={() => setMoreMenuOpen(o => !o)}
              active={moreMenuOpen}
            >
              <MoreVertical size={13} />
            </IconButton>
            {moreMenuOpen && (
              <div className="absolute right-0 top-full z-40 mt-1 w-44 rounded-md border border-[var(--color-border)] bg-white shadow-lg">
                <MenuItem onClick={copyTable}>Copy table</MenuItem>
                <MenuItem onClick={() => { window.print(); setMoreMenuOpen(false); }}>Print</MenuItem>
                <MenuItem onClick={() => { resetFilters(); setMoreMenuOpen(false); }}>Reset filters</MenuItem>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* F. Table card */}
      {fullscreen ? (
        <div className="fixed inset-0 z-50 flex flex-col overflow-auto bg-white p-8">
          {cardContent}
        </div>
      ) : (
        cardContent
      )}

      {/* G. Footnote */}
      <p className="px-6 py-3 text-[11px] text-[var(--color-text-muted)]">
        * Indexed AUM figures are indicative, based on publicly reported benchmarking data. Actual AUM may vary.
      </p>

      {/* I. Sustainability Panel — shown only on ESG tab */}
      {activeTab === 'esg' && (
        <SustainabilityPanel peers={selectedPeers} symbol={selectedSymbol} />
      )}

      {/* H. Indexed AUM Analysis card */}
      <div style={{
        margin: '0 24px 24px',
        border: '1px solid var(--color-border)',
        borderRadius: 8,
        background: '#fff',
        overflow: 'hidden',
      }}>
        <div style={{
          padding: '12px 16px',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <ChevronDown size={14} style={{ color: 'var(--color-text-muted)' }} />
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)' }}>
            Indexed AUM Analysis (US Dollar)
          </span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                <th style={{
                  padding: '10px 16px', textAlign: 'left', width: 400,
                  fontSize: 11, color: 'var(--color-text-muted)', fontWeight: 600,
                }}>
                  Metric
                </th>
                {selectedPeers.map(sym => (
                  <th key={sym} style={{
                    padding: '10px 16px', textAlign: 'right', minWidth: 140,
                    fontSize: 11, fontWeight: 700, color: 'var(--color-text-primary)',
                    textTransform: 'uppercase', letterSpacing: '0.04em',
                  }}>
                    {sym}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                { label: 'Free Float Market Capitalization ($M)**', key: 'freefloat' },
                { label: 'Total Indexed AUM ($M)', key: 'totalAum' },
                { label: 'Indexed Free Float Ratio***', key: 'ratio' },
              ].map(({ label, key }) => (
                <tr key={key} style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                  <td style={{
                    padding: '10px 16px', fontSize: 12,
                    color: 'var(--color-text-primary)', fontWeight: 500,
                  }}>
                    {label}
                  </td>
                  {selectedPeers.map(sym => (
                    <td key={sym} style={{
                      padding: '10px 16px', textAlign: 'right',
                      fontSize: 12, color: 'var(--color-text-muted)',
                      fontFamily: 'var(--font-mono, monospace)',
                    }}>
                      —
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={{
          padding: '10px 16px',
          borderTop: '1px solid var(--color-border)',
          display: 'flex', alignItems: 'center', gap: 16,
          justifyContent: 'flex-end',
        }}>
          {[
            { label: 'Outperforms', bg: '#00875A' },
            { label: 'Slightly Outperforms', bg: '#E3F5ED' },
            { label: 'Slightly Underperforms', bg: '#FDECEA' },
            { label: 'Underperforms', bg: '#D92D20' },
          ].map(({ label, bg }) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <div style={{
                width: 12, height: 12, borderRadius: 2,
                background: bg, flexShrink: 0,
              }} />
              <span style={{ fontSize: 11, color: 'var(--color-text-secondary)' }}>{label}</span>
            </div>
          ))}
        </div>

        <div style={{ padding: '8px 16px 12px', borderTop: '1px solid var(--color-border)' }}>
          <p style={{ fontSize: 11, color: 'var(--color-text-muted)', lineHeight: 1.6 }}>
            Displaying all data as of the current date, based on AUM.<br />
            *Indexed AUM includes, to the extent available, open-ended/closed-ended funds,
            separately managed accounts, pools/commingled funds, and institutional mutual funds<br />
            **MSCI defines the free float as the proportion of shares outstanding that is deemed
            to be available for purchase in public equity markets by international investors<br />
            *** Total Indexed AUM/Free Float Market Capitalization
          </p>
        </div>
      </div>

      {/* Peer group modal */}
      {peerModalOpen && (
        <PeerGroupModal
          subjectSymbol={selectedSymbol}
          currentPeers={selectedPeers}
          onClose={() => setPeerModalOpen(false)}
          onSave={(next) => {
            setPeerExtras(next.filter(s => s !== selectedSymbol));
            setPeerModalOpen(false);
          }}
        />
      )}
    </div>
  );
}

// ── helpers ──────────────────────────────────────────────────────────────────

function triggerDownload(url: string, filename: string): void {
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ── sub-components ───────────────────────────────────────────────────────────

function CompanyPicker({
  symbol,
  display,
  open,
  setOpen,
  onSelect,
}: {
  symbol: string;
  display: string;
  open: boolean;
  setOpen: (o: boolean) => void;
  onSelect: (sym: string, name: string) => void;
}) {
  const [search, setSearch] = useState('');
  const filtered = AVAILABLE_PEERS.filter(i =>
    i.symbol.includes(search.toUpperCase()) || i.name.toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <div>
      <label className="label-caps mb-1 block">Company</label>
      <div className="relative">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="flex w-full items-center justify-between rounded border border-[var(--color-border)] bg-white px-3 py-[7px] text-[13px] font-semibold text-[var(--color-text-primary)] hover:bg-[var(--color-border-subtle)]"
        >
          <span className="truncate">{symbol}</span>
          <ChevronDown size={12} className="ml-2 shrink-0 text-[var(--color-text-muted)]" />
        </button>
        {open && (
          <div className="absolute left-0 top-full z-40 mt-1 w-[320px] overflow-hidden rounded-md border border-[var(--color-border)] bg-white shadow-lg">
            <div className="border-b border-[var(--color-border)] p-2">
              <input
                autoFocus
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search symbol or company…"
                className="w-full rounded border border-[var(--color-border)] bg-[var(--color-bg-page)] px-2 py-1 text-[12px] text-[var(--color-text-primary)] outline-none"
              />
            </div>
            <div className="max-h-[260px] overflow-y-auto">
              {filtered.map(i => (
                <button
                  key={i.symbol}
                  type="button"
                  onClick={() => onSelect(i.symbol, i.name)}
                  className={`flex w-full items-center gap-2 border-b border-[var(--color-border-subtle)] px-3 py-2 text-left text-[12px] hover:bg-[var(--color-border-subtle)] ${i.symbol === symbol ? 'bg-[rgba(0,87,168,0.06)]' : ''}`}
                >
                  <span className="data-mono w-12 shrink-0 text-[11px] font-bold text-[var(--color-blue-primary)]">
                    {i.symbol}
                  </span>
                  <span className="flex-1 truncate text-[var(--color-text-secondary)]">{i.name}</span>
                  {i.symbol === symbol && <Check size={13} className="text-[var(--color-blue-primary)]" />}
                </button>
              ))}
              {filtered.length === 0 && (
                <div className="px-3 py-4 text-center text-[12px] text-[var(--color-text-muted)]">
                  No matches
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      <span className="sr-only">{display}</span>
    </div>
  );
}

function AsOfDateSelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <div className="mb-1 flex items-center gap-1">
        <label className="label-caps">As of date</label>
        <span title="Quarterly review date for index constituents">
          <Info size={11} className="text-[var(--color-text-muted)]" />
        </span>
      </div>
      <div className="relative">
        <select
          value={value}
          onChange={e => onChange(e.target.value)}
          className="w-full appearance-none rounded border border-[var(--color-border)] bg-white px-3 py-[7px] pr-8 text-[13px] text-[var(--color-text-primary)] outline-none hover:bg-[var(--color-border-subtle)]"
        >
          {AS_OF_DATES.map(d => (
            <option key={d} value={d}>
              {formatAsOfDate(d)}
            </option>
          ))}
        </select>
        <ChevronDown
          size={12}
          className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]"
        />
      </div>
    </div>
  );
}

function IndexSearchField({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <div className="mb-1 flex items-center gap-1">
        <label className="label-caps">Index Name Selection</label>
        <span title="Filter visible indexes by name">
          <Info size={11} className="text-[var(--color-text-muted)]" />
        </span>
      </div>
      <div className="relative">
        <SearchIcon
          size={13}
          className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]"
        />
        <input
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder="Search"
          className="w-full rounded border border-[var(--color-border)] bg-white py-[7px] pl-7 pr-3 text-[13px] outline-none hover:bg-[var(--color-border-subtle)]"
        />
      </div>
    </div>
  );
}

function IconButton({
  label,
  onClick,
  active,
  children,
}: {
  label: string;
  onClick: () => void;
  active?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className={`relative flex h-6 w-6 items-center justify-center rounded border border-[var(--color-border)] transition-colors ${
        active ? 'bg-[var(--color-border-subtle)]' : 'bg-white hover:bg-[var(--color-border-subtle)]'
      }`}
    >
      {children}
    </button>
  );
}

function MenuItem({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="block w-full px-3 py-2 text-left text-[12px] hover:bg-[var(--color-border-subtle)]"
    >
      {children}
    </button>
  );
}

function FilterPopover({
  esgOnly,
  setEsgOnly,
  hideNotListed,
  setHideNotListed,
  onClose,
}: {
  esgOnly: boolean;
  setEsgOnly: (v: boolean) => void;
  hideNotListed: boolean;
  setHideNotListed: (v: boolean) => void;
  onClose: () => void;
}) {
  return (
    <div className="absolute right-0 top-full z-40 mt-1 w-60 rounded-md border border-[var(--color-border)] bg-white p-3 shadow-lg">
      <div className="mb-2 flex items-center justify-between">
        <span className="label-caps">Filters</span>
        <button type="button" onClick={onClose} aria-label="Close filters">
          <X size={13} className="text-[var(--color-text-muted)]" />
        </button>
      </div>
      <label className="flex items-center gap-2 py-1.5 text-[12px] text-[var(--color-text-primary)]">
        <input
          type="checkbox"
          checked={esgOnly}
          onChange={e => setEsgOnly(e.target.checked)}
          className="accent-[var(--color-blue-primary)]"
        />
        Show ESG indexes only
      </label>
      <label className="flex items-center gap-2 py-1.5 text-[12px] text-[var(--color-text-primary)]">
        <input
          type="checkbox"
          checked={hideNotListed}
          onChange={e => setHideNotListed(e.target.checked)}
          className="accent-[var(--color-blue-primary)]"
        />
        Hide not-listed rows
      </label>
    </div>
  );
}

function PeerGroupModal({
  subjectSymbol,
  currentPeers,
  onClose,
  onSave,
}: {
  subjectSymbol: string;
  currentPeers: string[];
  onClose: () => void;
  onSave: (next: string[]) => void;
}) {
  const [draft, setDraft] = useState<string[]>(currentPeers);
  const firstRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    firstRef.current?.focus();
  }, []);

  const toggle = (sym: string) => {
    if (sym === subjectSymbol) return;
    setDraft(prev => (prev.includes(sym) ? prev.filter(s => s !== sym) : [...prev, sym]));
  };

  const count = draft.length;
  const canSave = count > 0 && count <= MAX_PEERS && JSON.stringify([...draft].sort()) !== JSON.stringify([...currentPeers].sort());

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="mx-auto mt-20 max-w-md rounded-lg bg-white p-6 shadow-xl"
        onClick={e => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="peer-modal-title"
      >
        <h2 id="peer-modal-title" className="text-[16px] font-semibold text-[var(--color-text-primary)]">
          Edit Peer Group
        </h2>
        <p className="mt-1 text-[12px] text-[var(--color-text-muted)]">
          Select up to {MAX_PEERS} peer companies in the Banks industry.
        </p>
        <ul className="mt-4 max-h-[320px] overflow-y-auto">
          {AVAILABLE_PEERS.map((p, i) => {
            const isSubject = p.symbol === subjectSymbol;
            const checked = draft.includes(p.symbol) || isSubject;
            const disabled = isSubject || (!checked && count >= MAX_PEERS);
            return (
              <li key={p.symbol}>
                <label className={`flex items-center gap-3 border-b border-[var(--color-border-subtle)] py-2 ${disabled && !isSubject ? 'opacity-50' : ''}`}>
                  <input
                    ref={i === 0 ? firstRef : undefined}
                    type="checkbox"
                    checked={checked}
                    disabled={disabled}
                    onChange={() => toggle(p.symbol)}
                    className="accent-[var(--color-blue-primary)]"
                  />
                  <span className="data-mono w-14 text-[12px] font-bold text-[var(--color-blue-primary)]">
                    {p.symbol}
                  </span>
                  <span className="flex-1 text-[12px] text-[var(--color-text-primary)]">{p.name}</span>
                  {isSubject && (
                    <span className="rounded bg-[var(--color-blue-soft)] px-1.5 py-0.5 text-[9px] font-bold tracking-wider text-[var(--color-blue-primary)]">
                      SUBJECT
                    </span>
                  )}
                </label>
              </li>
            );
          })}
        </ul>
        <div className="mt-4 flex items-center justify-between">
          <span className="text-[11px] text-[var(--color-text-muted)]">
            {count}/{MAX_PEERS} selected
          </span>
          <div className="flex items-center gap-3">
            <button type="button" onClick={onClose} className="link-blue text-[13px]">
              Cancel
            </button>
            <button
              type="button"
              onClick={() => onSave([subjectSymbol, ...draft.filter(s => s !== subjectSymbol)])}
              disabled={!canSave}
              className="h-9 rounded bg-[var(--color-blue-primary)] px-4 text-[13px] font-semibold text-white hover:bg-[var(--color-blue-dark)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── table ────────────────────────────────────────────────────────────────────

function DataTable({
  rows,
  peers,
  tab,
  sort,
  onSort,
  loading,
}: {
  rows: IndexRow[];
  peers: string[];
  tab: TabKey;
  sort: { key: SortKey; dir: SortDir } | null;
  onSort: (key: SortKey) => void;
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="px-6 py-10 text-center text-[13px] text-[var(--color-text-muted)]">
        Loading index membership…
      </div>
    );
  }
  if (rows.length === 0) {
    return (
      <div className="px-6 py-10 text-center text-[13px] text-[var(--color-text-muted)]">
        No matching indexes.
      </div>
    );
  }

  return (
    <div style={{ overflowX: 'auto', overflowY: 'auto', maxHeight: 420 }}>
      <table className="w-full border-collapse text-[12px]">
        <colgroup>
          <col style={{ width: 40 }} />
          <col style={{ width: 70 }} />
          <col style={{ width: 110 }} />
          <col style={{ width: 280 }} />
          <col style={{ width: 160 }} />
          <col style={{ width: 140 }} />
          {tab === 'esg'
            ? (['rating', 'carbon', 'quality'] as const).map(k => <col key={k} style={{ width: 140 }} />)
            : peers.map(p => <col key={p} style={{ width: 140 }} />)}
        </colgroup>
        <thead style={{ position: 'sticky', top: 0, zIndex: 2, background: 'var(--color-bg-page)' }}>
          <tr className="border-b border-[var(--color-border)]">
            <ThCell align="center">—</ThCell>
            <SortableTh label="Rank" col="rank" sort={sort} onSort={onSort} align="right" prefix />
            <SortableTh label="Index Code" col="indexCode" sort={sort} onSort={onSort} align="right" prefix />
            <SortableTh label="Index Name" col="indexName" sort={sort} onSort={onSort} align="left" prefix />
            <SortableTh label="Next Rebalancing Date" col="nextRebalancingDate" sort={sort} onSort={onSort} align="right" prefix />
            <ThCell align="right" divider>Indexed AUM ($M)&nbsp;*</ThCell>
            {tab === 'esg' ? (
              <>
                <ThCell align="right">ESG Rating</ThCell>
                <ThCell align="right">Carbon Intensity</ThCell>
                <ThCell align="right">ESG Quality Score</ThCell>
              </>
            ) : (
              peers.map(p => (
                <ThCell key={p} align="right">
                  {p}
                </ThCell>
              ))
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIdx) => (
            <TableRow key={row.indexCode} row={row} peers={peers} tab={tab} rowIdx={rowIdx} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TableRow({
  row,
  peers,
  tab,
  rowIdx,
}: {
  row: IndexRow;
  peers: string[];
  tab: TabKey;
  rowIdx: number;
}) {
  const bg = row.isParent
    ? 'bg-[var(--color-blue-soft)]'
    : rowIdx % 2 === 0
      ? 'bg-white'
      : 'bg-[var(--color-bg-page)]';

  return (
    <tr className={`border-b border-[var(--color-border-subtle)] ${bg} transition-colors hover:bg-[var(--color-border-subtle)]`}>
      <TdCell align="center" muted>—</TdCell>
      <TdCell align="right">
        {row.rank === null ? <span className="text-[var(--color-text-muted)]">—</span> : row.rank}
      </TdCell>
      <TdCell align="right" mono>
        <span className="text-[var(--color-text-muted)]">—&nbsp;</span>
        {row.indexCode}
      </TdCell>
      <TdCell align="left">
        <a
          href={`/indexes/${row.indexCode}`}
          target="_blank"
          rel="noreferrer"
          className="link-blue cursor-pointer hover:underline"
        >
          <span className="text-[var(--color-text-muted)]">—&nbsp;</span>
          {row.indexName}
        </a>
      </TdCell>
      <TdCell align="right" mono>
        {row.nextRebalancingDate ? (
          <>
            <span className="text-[var(--color-text-muted)]">—&nbsp;</span>
            {formatRebalDate(row.nextRebalancingDate)}
          </>
        ) : (
          <span className="text-[var(--color-text-muted)]">—</span>
        )}
      </TdCell>
      <TdCell align="right" mono divider>
        {row.indexedAumMillionUsd !== null
          ? row.indexedAumMillionUsd.toFixed(2)
          : <span className="text-[var(--color-text-muted)]">—</span>}
      </TdCell>

      {tab === 'esg' ? (
        <EsgCells esg={row.esg} />
      ) : (
        peers.map(p => <PeerCell key={p} row={row} peer={p} tab={tab} />)
      )}
    </tr>
  );
}

function PeerCell({ row, peer, tab }: { row: IndexRow; peer: string; tab: TabKey }) {
  const weight = row.weights[peer] ?? null;
  if (row.isParent) {
    if (weight === 1) {
      return (
        <TdCell align="right">
          <Check size={14} className="ml-auto text-[var(--color-positive)]" />
        </TdCell>
      );
    }
    return <TdCell align="right" muted>—</TdCell>;
  }
  if (weight === null) {
    return <TdCell align="right" muted>—</TdCell>;
  }
  if (tab === 'usd') {
    const usd = row.indexedAumMillionUsd !== null ? (weight * row.indexedAumMillionUsd) / 100 : null;
    return (
      <TdCell align="right" mono>
        {usd !== null ? usd.toFixed(2) : <span className="text-[var(--color-text-muted)]">—</span>}
      </TdCell>
    );
  }
  return (
    <TdCell align="right" mono>
      {weight.toFixed(2)}
    </TdCell>
  );
}

function EsgCells({ esg }: { esg: IndexRow['esg'] }) {
  if (!esg) {
    return (
      <>
        <TdCell align="right" muted>—</TdCell>
        <TdCell align="right" muted>—</TdCell>
        <TdCell align="right" muted>—</TdCell>
      </>
    );
  }
  const color = esgBadgeColor(esg.rating);
  return (
    <>
      <TdCell align="right">
        <span
          className="inline-block rounded px-2 py-0.5 text-[10px] font-bold tracking-wider"
          style={{ background: color.bg, color: color.fg }}
        >
          {esg.rating}
        </span>
      </TdCell>
      <TdCell align="right" mono>
        {esg.carbonIntensity.toFixed(2)}
      </TdCell>
      <TdCell align="right" mono>
        {esg.esgQualityScore.toFixed(1)}/10
      </TdCell>
    </>
  );
}

function SortableTh({
  label,
  col,
  sort,
  onSort,
  align,
  prefix,
}: {
  label: string;
  col: SortKey;
  sort: { key: SortKey; dir: SortDir } | null;
  onSort: (col: SortKey) => void;
  align: 'left' | 'right' | 'center';
  prefix?: boolean;
}) {
  const isSorted = sort?.key === col;
  const arrow: CSSProperties = {
    transform: isSorted && sort?.dir === 'asc' ? 'rotate(180deg)' : undefined,
    opacity: isSorted ? 1 : 0.4,
  };
  return (
    <th
      onClick={() => onSort(col)}
      className={`cursor-pointer select-none px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-[var(--color-text-muted)] ${
        align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left'
      } hover:text-[var(--color-text-secondary)]`}
    >
      <span className="inline-flex items-center gap-1">
        {prefix && <span className="text-[var(--color-text-muted)]">—</span>}
        {label}
        <ChevronDown size={11} style={arrow} />
      </span>
    </th>
  );
}

function ThCell({
  align,
  divider,
  children,
}: {
  align: 'left' | 'right' | 'center';
  divider?: boolean;
  children: React.ReactNode;
}) {
  return (
    <th
      className={`px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-[var(--color-text-muted)] ${
        align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left'
      } ${divider ? 'border-r border-[var(--color-border)]' : ''}`}
    >
      {children}
    </th>
  );
}

function TdCell({
  align,
  mono,
  muted,
  divider,
  children,
}: {
  align: 'left' | 'right' | 'center';
  mono?: boolean;
  muted?: boolean;
  divider?: boolean;
  children: React.ReactNode;
}) {
  return (
    <td
      className={`whitespace-nowrap px-3 py-2 ${
        align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left'
      } ${mono ? 'data-mono' : ''} ${muted ? 'text-[var(--color-text-muted)]' : 'text-[var(--color-text-primary)]'} ${
        divider ? 'border-r border-[var(--color-border)]' : ''
      }`}
    >
      {children}
    </td>
  );
}

// ── Sustainability panel (ESG tab only) ──────────────────────────────────────

interface SustainabilityRow {
  label: string;
  getValue: (d: SustainabilityMetrics) => string | number | null;
}

interface SustainabilitySection {
  title: string;
  rows: SustainabilityRow[];
}

const SUSTAINABILITY_SECTIONS: SustainabilitySection[] = [
  {
    title: 'General Information',
    rows: [
      { label: 'Sub Industry', getValue: d => d.subIndustry },
      { label: 'Size Category', getValue: d => d.sizeCategory },
      { label: 'Country', getValue: d => d.country },
    ],
  },
  {
    title: 'Security Identification',
    rows: [
      { label: 'TICKER', getValue: d => d.ticker },
      { label: 'ISIN', getValue: d => d.isin },
    ],
  },
  {
    title: 'Security Information',
    rows: [
      {
        label: 'Free Float Market Capitalization (USD M)**',
        getValue: d => d.freefloatMarketCapUsdM.toLocaleString('en-US'),
      },
      { label: 'Indexed AUM ($M)*', getValue: d => d.indexedAumUsdM.toFixed(2) },
      { label: 'Indexed Free Float Ratio***', getValue: d => d.indexedFreefloatRatio.toFixed(2) },
    ],
  },
  {
    title: 'ESG Ratings & Controversies',
    rows: [
      { label: 'ESG Rating (CCC to AAA)', getValue: d => d.esgRating },
      { label: 'Industry Adjusted Company Score (0-10)', getValue: d => d.industryAdjustedScore },
      { label: 'ESG Controversies Overall Score (0-10)', getValue: d => d.esgControversiesScore },
    ],
  },
  {
    title: 'Decarbonization Targets & Emissions',
    rows: [
      {
        label:
          'Indicates whether the company has a carbon emissions reduction target and (for carbon-intensive sectors) our assessment of how aggressive any target is.',
        getValue: d => d.ghgReductionTarget,
      },
      {
        label: 'Company has Science-based Approved Emissions Target (SBTi)',
        getValue: d => d.scienceBasedTarget,
      },
      { label: 'Implied Temperature Rise (1.3°C-10°C)', getValue: d => d.impliedTemperatureRise },
      {
        label: 'Carbon Emissions - Scope 1+2 (metric tons)',
        getValue: d => d.carbonScope12MetricTons.toLocaleString('en-US'),
      },
      {
        label: 'Carbon Emissions - Scope 1+2 (Reported or Estimated)',
        getValue: d => d.carbonScope12Type,
      },
      {
        label: 'Total Emission Estimated - Scope 3 (metric tons)',
        getValue: d =>
          d.totalEmissionScope3 !== null ? d.totalEmissionScope3.toLocaleString('en-US') : '—',
      },
      {
        label: 'Total Emission Scope (1, 2 and 3) Intensity EVIC (USD)',
        getValue: d => d.emissionIntensityEvic,
      },
    ],
  },
];

function SustainabilityPanel({
  peers,
  symbol,
}: {
  peers: string[];
  symbol: string;
}) {
  const subjectData = BBCA_SUSTAINABILITY[symbol] ?? BBCA_SUSTAINABILITY['BBCA'] ?? null;

  if (!subjectData) return null;

  return (
    <div style={{
      margin: '0 24px 24px',
      border: '1px solid var(--color-border)',
      borderRadius: 8,
      background: '#fff',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px', borderBottom: '1px solid var(--color-border)',
        display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16,
      }}>
        <div>
          <h2 style={{ fontSize: 14, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 4 }}>
            Comparison of Key Sustainability &amp; Climate Metrics across Peers
          </h2>
          <p style={{
            fontSize: 12, color: 'var(--color-text-secondary)',
            maxWidth: 700, lineHeight: 1.5, margin: 0,
          }}>
            MSCI Indonesia recommends choosing peers within the same industry, size segment and region
            for a more relevant comparison because these factors align with index methodology and construction.
          </p>
        </div>
        <label style={{
          display: 'flex', alignItems: 'center', gap: 8,
          fontSize: 12, color: 'var(--color-text-secondary)',
          cursor: 'pointer', whiteSpace: 'nowrap',
        }}>
          <input
            type="checkbox"
            defaultChecked
            style={{ accentColor: 'var(--color-blue-primary)' }}
          />
          Peer Conditional Formatting
        </label>
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <colgroup>
            <col style={{ width: 420 }} />
            {peers.map(p => <col key={p} style={{ width: 160 }} />)}
          </colgroup>
          <thead>
            <tr style={{ borderBottom: '2px solid var(--color-border)' }}>
              <th style={{
                padding: '10px 16px', textAlign: 'left',
                fontSize: 11, fontWeight: 600, color: 'var(--color-text-muted)',
              }}>
                Categories / Factors
              </th>
              {peers.map((p, i) => (
                <th key={p} style={{
                  padding: '10px 16px', textAlign: 'right', minWidth: 140,
                  fontSize: 12, fontWeight: 700,
                  color: i === 0 ? 'var(--color-blue-primary)' : 'var(--color-text-primary)',
                  borderLeft: '1px solid var(--color-border)',
                }}>
                  {p}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {SUSTAINABILITY_SECTIONS.map(section => (
              <Fragment key={section.title}>
                {/* Section header row */}
                <tr style={{
                  background: 'rgba(0,87,168,0.04)',
                  borderBottom: '1px solid var(--color-border)',
                }}>
                  <td
                    colSpan={peers.length + 1}
                    style={{
                      padding: '8px 16px',
                      fontSize: 12, fontWeight: 700, color: 'var(--color-text-primary)',
                    }}
                  >
                    <span style={{ fontSize: 11, color: 'var(--color-text-muted)', marginRight: 6 }}>−</span>
                    {section.title}
                  </td>
                </tr>
                {/* Data rows */}
                {section.rows.map((row, ri) => (
                  <tr
                    key={`${section.title}-${ri}`}
                    style={{
                      borderBottom: '1px solid var(--color-border-subtle)',
                      background: ri % 2 === 0 ? 'transparent' : 'rgba(0,0,0,0.01)',
                    }}
                  >
                    <td style={{
                      padding: '9px 16px 9px 28px',
                      fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.4,
                    }}>
                      {row.label}
                    </td>
                    {peers.map((p, pi) => {
                      const val = pi === 0 ? row.getValue(subjectData) : null;
                      return (
                        <td
                          key={p}
                          style={{
                            padding: '9px 16px', textAlign: 'right', fontSize: 12,
                            color: pi === 0 ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
                            borderLeft: '1px solid var(--color-border)',
                            fontWeight: pi === 0 ? 500 : 400,
                          }}
                        >
                          {val !== null && val !== undefined
                            ? String(val)
                            : <span style={{ color: 'var(--color-text-muted)' }}>XX.XXX</span>}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div style={{
        padding: '10px 16px', borderTop: '1px solid var(--color-border)',
        display: 'flex', alignItems: 'center', gap: 16, justifyContent: 'flex-end',
      }}>
        {[
          { label: 'Outperforms', bg: '#057a55' },
          { label: 'Slightly Outperforms', bg: '#e3f5ed' },
          { label: 'Slightly Underperforms', bg: '#fdecea' },
          { label: 'Underperforms', bg: '#e02424' },
        ].map(({ label, bg }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 12, height: 12, borderRadius: 2, background: bg }} />
            <span style={{ fontSize: 11, color: 'var(--color-text-secondary)' }}>{label}</span>
          </div>
        ))}
      </div>

      {/* Footnotes */}
      <div style={{ padding: '8px 16px 12px', borderTop: '1px solid var(--color-border)' }}>
        <p style={{ fontSize: 11, color: 'var(--color-text-muted)', lineHeight: 1.6, margin: 0 }}>
          * Indexed AUM includes open-ended/closed-ended funds, separately managed accounts, and institutional mutual funds.<br />
          ** Free float as proportion of shares outstanding available for purchase by international investors.<br />
          *** Total Indexed AUM / Free Float Market Capitalization.<br />
          Data sourced from MSCI ESG Research and company disclosures. Peer data requires MSCI subscription.
        </p>
      </div>
    </div>
  );
}
