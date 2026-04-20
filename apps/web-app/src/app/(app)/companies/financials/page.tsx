'use client';

import { useEffect, useState, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import {
  Area, AreaChart, Bar, CartesianGrid, ComposedChart,
  Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { useCompanyStore } from '@/stores/company';
import { CompanySelector } from '@/components/companies/CompanySelector';

// ── Types ─────────────────────────────────────────────────────────────────────
interface FinancialPosition {
  year: number; period: string;
  total_assets: number; total_earning_assets: number;
  total_loans: number; total_liabilities: number;
  third_party_funds: number; casa: number;
  time_deposits: number; total_equity: number;
}
interface Income {
  year: number; period: string;
  operating_income: number; net_interest_income: number;
  operating_expenses: number; impairment_losses: number;
  income_before_tax: number; net_income: number;
  total_comprehensive_income: number; eps: number;
}
interface Ratio {
  year: number; period: string;
  car: number; car_tier1: number; car_tier2: number;
  npl_gross: number; npl_net: number; lar: number;
  roa: number; roe: number; nim: number;
  cir: number; bopo: number;
  ldr: number; lcr: number; nsfr: number; casa_ratio: number;
}
interface StockHighlight {
  year: number;
  highest: number; lowest: number; closing: number;
  market_cap_trillion: number; eps: number; bvps: number;
  pe: number; pbv: number;
}
interface PricePoint {
  date: string; open: number; high: number;
  low: number; close: number; volume: number;
}
interface FinancialHighlights {
  symbol: string; source: string; currency: string;
  financial_position: FinancialPosition[];
  income: Income[];
  ratios: Ratio[];
  stock_highlights: StockHighlight[];
  message?: string;
}

type Cell = string | number | null | undefined;

// ── Formatters ────────────────────────────────────────────────────────────────
function safeNum(v: unknown): number | null {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}
const fmtB = (v: unknown): string => {
  const n = safeNum(v);
  return n !== null ? n.toLocaleString('id-ID') : '—';
};
const fmtPct = (v: unknown): string => {
  const n = safeNum(v);
  return n !== null ? n.toFixed(1) + '%' : '—';
};
const fmtX = (v: unknown): string => {
  const n = safeNum(v);
  return n !== null ? n.toFixed(1) + 'x' : '—';
};

// ── Styles ────────────────────────────────────────────────────────────────────
const sectionHeader: React.CSSProperties = {
  fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
  letterSpacing: '0.08em', color: 'var(--color-blue-primary)',
  padding: '10px 16px', background: 'rgba(0,87,168,0.04)',
  borderBottom: '1px solid var(--color-border)',
};
const cardStyle: React.CSSProperties = {
  background: '#fff', border: '1px solid var(--color-border)',
  borderRadius: 8, overflow: 'hidden',
};

// ── Table ─────────────────────────────────────────────────────────────────────
interface FinRow {
  label: string;
  values: Cell[];
  bold?: boolean;
  indent?: boolean;
}

function FinTable({
  title,
  rows,
  years,
}: {
  title: string;
  rows: FinRow[];
  years: number[];
}) {
  return (
    <div style={cardStyle}>
      <div style={sectionHeader}>{title}</div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: 'rgba(0,87,168,0.06)', borderBottom: '2px solid var(--color-border)' }}>
              <th style={{
                padding: '8px 16px', textAlign: 'left', fontWeight: 700,
                color: 'var(--color-text-primary)', minWidth: 280, fontSize: 11,
              }}>
                (in Billion Rupiah)
              </th>
              {years.map(y => (
                <th key={y} style={{
                  padding: '8px 16px', textAlign: 'right', fontWeight: 700,
                  color: 'var(--color-blue-primary)', minWidth: 100, fontSize: 12,
                }}>
                  {y}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} style={{
                borderBottom: '1px solid var(--color-border-subtle)',
                background: row.bold ? 'rgba(0,87,168,0.03)' : 'transparent',
              }}>
                <td style={{
                  padding: '7px 16px',
                  paddingLeft: row.indent ? 32 : 16,
                  fontWeight: row.bold ? 700 : 400,
                  color: row.bold ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                  fontSize: 12,
                }}>
                  {row.label}
                </td>
                {row.values.map((v, j) => (
                  <td key={j} style={{
                    padding: '7px 16px', textAlign: 'right',
                    fontFamily: 'var(--font-mono, monospace)',
                    fontWeight: row.bold ? 700 : 400,
                    color: row.bold ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                    fontSize: 12,
                  }}>
                    {v ?? '—'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function FinancialsPage() {
  const { data: session } = useSession();
  const { selectedSymbol } = useCompanyStore();
  const [highlights, setHighlights] = useState<FinancialHighlights | null>(null);
  const [priceHistory, setPriceHistory] = useState<PricePoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [priceLoading, setPriceLoading] = useState(false);
  const [activeChart, setActiveChart] = useState<'price' | 'netincome' | 'assets'>('price');

  const authHeader = useCallback((): Record<string, string> => {
    const token = (session as { accessToken?: string } | null)?.accessToken;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [session]);

  useEffect(() => {
    if (!session || !selectedSymbol) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    fetch(`/api/v1/stocks/${selectedSymbol}/financial-highlights`, { headers: authHeader() })
      .then(r => r.json())
      .then((data: FinancialHighlights) => { setHighlights(data); setLoading(false); })
      .catch(() => { setHighlights(null); setLoading(false); });
  }, [selectedSymbol, session, authHeader]);

  useEffect(() => {
    if (!session || !selectedSymbol) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPriceLoading(true);
    fetch(`/api/v1/stocks/${selectedSymbol}/price-history?period=5y`, { headers: authHeader() })
      .then(r => r.json())
      .then((data: PricePoint[]) => { setPriceHistory(Array.isArray(data) ? data : []); setPriceLoading(false); })
      .catch(() => { setPriceHistory([]); setPriceLoading(false); });
  }, [selectedSymbol, session, authHeader]);

  const years = highlights?.financial_position.map(r => r.year) ?? [];
  const fp = highlights?.financial_position ?? [];
  const inc = highlights?.income ?? [];
  const rat = highlights?.ratios ?? [];
  const stk = highlights?.stock_highlights ?? [];

  const netIncomeChartData = [...inc].reverse().map(r => ({
    year: r.year.toString(),
    'Net Income': r.net_income,
    'Operating Income': r.operating_income,
  }));

  const assetChartData = [...fp].reverse().map(r => ({
    year: r.year.toString(),
    'Total Assets': Math.round(r.total_assets / 1000),
    'Total Loans': Math.round(r.total_loans / 1000),
    'Total Equity': Math.round(r.total_equity / 1000),
  }));

  const pricePointsSampled = priceHistory.length > 52
    ? priceHistory.filter((_, i) => i % 2 === 0)
    : priceHistory;

  return (
    <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)', margin: 0 }}>
          Financial Highlights
        </h1>
        <CompanySelector />
        {highlights && (
          <p style={{ fontSize: 12, color: 'var(--color-text-muted)', margin: 0 }}>
            Key Financial Highlights over the last 5 years (Audited, Consolidated, as of December 31) •{' '}
            <span style={{ fontStyle: 'italic' }}>Source: {highlights.source}</span>
          </p>
        )}
      </div>

      {loading && (
        <div style={{ padding: 60, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13 }}>
          Loading financial data…
        </div>
      )}

      {!loading && highlights?.message && highlights.financial_position.length === 0 && (
        <div style={{ ...cardStyle, padding: '40px 24px', textAlign: 'center' }}>
          <p style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>{highlights.message}</p>
        </div>
      )}

      {!loading && highlights && highlights.financial_position.length > 0 && (
        <>
          {/* ── Chart section ── */}
          <div style={cardStyle}>
            <div style={{
              padding: '12px 16px', borderBottom: '1px solid var(--color-border)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)' }}>
                Performance Charts
              </span>
              <div style={{ display: 'flex', gap: 6 }}>
                {([
                  { key: 'price', label: 'Share Price (5Y)' },
                  { key: 'netincome', label: 'Income Trend' },
                  { key: 'assets', label: 'Balance Sheet' },
                ] as const).map(({ key, label }) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setActiveChart(key)}
                    style={{
                      padding: '4px 10px', fontSize: 11, borderRadius: 4,
                      border: '1px solid var(--color-border)',
                      background: activeChart === key ? 'var(--color-blue-primary)' : 'white',
                      color: activeChart === key ? 'white' : 'var(--color-text-secondary)',
                      cursor: 'pointer', fontWeight: activeChart === key ? 700 : 400,
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
            <div style={{ padding: 16, height: 320 }}>
              {activeChart === 'price' && priceLoading && (
                <div style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  height: '100%', color: 'var(--color-text-muted)', fontSize: 13,
                }}>
                  Loading price history…
                </div>
              )}
              {activeChart === 'price' && !priceLoading && priceHistory.length === 0 && (
                <div style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  height: '100%', color: 'var(--color-text-muted)', fontSize: 13,
                }}>
                  No price history available.
                </div>
              )}
              {activeChart === 'price' && !priceLoading && priceHistory.length > 0 && (
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={pricePointsSampled}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 10 }}
                      tickFormatter={d => d.slice(0, 7)}
                      interval={Math.max(1, Math.floor(pricePointsSampled.length / 12))}
                    />
                    <YAxis
                      yAxisId="price"
                      tick={{ fontSize: 10 }}
                      tickFormatter={v => (v / 1000).toFixed(1) + 'K'}
                    />
                    <YAxis
                      yAxisId="vol"
                      orientation="right"
                      tick={{ fontSize: 10 }}
                      tickFormatter={v => (v / 1e6).toFixed(0) + 'M'}
                    />
                    <Tooltip
                      formatter={(value, name) => [
                        name === 'Volume'
                          ? (Number(value) / 1e6).toFixed(1) + 'M'
                          : 'IDR ' + Number(value).toLocaleString('id-ID'),
                        name,
                      ]}
                      labelFormatter={l => 'Date: ' + l}
                    />
                    <Legend />
                    <Bar yAxisId="vol" dataKey="volume" name="Volume"
                      fill="rgba(0,87,168,0.15)" barSize={4} />
                    <Line yAxisId="price" type="monotone" dataKey="close"
                      name="Close Price (IDR)" stroke="var(--color-blue-primary)"
                      dot={false} strokeWidth={2} />
                  </ComposedChart>
                </ResponsiveContainer>
              )}
              {activeChart === 'netincome' && (
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={netIncomeChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                    <YAxis
                      tick={{ fontSize: 10 }}
                      tickFormatter={v => (v / 1000).toFixed(0) + 'T'}
                    />
                    <Tooltip formatter={(v, n) => ['IDR ' + Number(v).toLocaleString('id-ID') + 'B', n]} />
                    <Legend />
                    <Bar dataKey="Operating Income" fill="rgba(0,87,168,0.3)" barSize={32} />
                    <Line type="monotone" dataKey="Net Income"
                      stroke="var(--color-positive)" strokeWidth={2.5} dot={{ r: 4 }} />
                  </ComposedChart>
                </ResponsiveContainer>
              )}
              {activeChart === 'assets' && (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={assetChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                    <YAxis
                      tick={{ fontSize: 10 }}
                      tickFormatter={v => v.toFixed(0) + 'T'}
                    />
                    <Tooltip formatter={(v, n) => ['IDR ' + Number(v).toLocaleString('id-ID') + 'T', n]} />
                    <Legend />
                    <Area dataKey="Total Assets" fill="rgba(0,87,168,0.1)"
                      stroke="var(--color-blue-primary)" strokeWidth={2} />
                    <Area dataKey="Total Loans" fill="rgba(0,135,90,0.1)"
                      stroke="var(--color-positive)" strokeWidth={2} />
                    <Area dataKey="Total Equity" fill="rgba(245,158,11,0.1)"
                      stroke="#f59e0b" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* ── Financial Position ── */}
          <FinTable
            title="Financial Position"
            years={years}
            rows={[
              { label: 'Total Asset', bold: true, values: fp.map(r => fmtB(r.total_assets)) },
              { label: 'Total Earning Assets', values: fp.map(r => fmtB(r.total_earning_assets)) },
              { label: 'Total Loans', values: fp.map(r => fmtB(r.total_loans)) },
              { label: 'Total Liabilities', bold: true, values: fp.map(r => fmtB(r.total_liabilities)) },
              { label: 'Third Party Funds', values: fp.map(r => fmtB(r.third_party_funds)) },
              { label: 'CASA', indent: true, values: fp.map(r => fmtB(r.casa)) },
              { label: 'Time Deposits', indent: true, values: fp.map(r => fmtB(r.time_deposits)) },
              { label: 'Total Equity', bold: true, values: fp.map(r => fmtB(r.total_equity)) },
            ]}
          />

          {/* ── Comprehensive Income ── */}
          <FinTable
            title="Comprehensive Income"
            years={years}
            rows={[
              { label: 'Operating Income', bold: true, values: inc.map(r => fmtB(r.operating_income)) },
              { label: 'Net Interest and Sharia Income', indent: true, values: inc.map(r => fmtB(r.net_interest_income)) },
              { label: 'Operating Expenses', values: inc.map(r => '(' + fmtB(r.operating_expenses) + ')') },
              { label: 'Impairment Losses on Financial Assets', values: inc.map(r => '(' + fmtB(r.impairment_losses) + ')') },
              { label: 'Income Before Tax', bold: true, values: inc.map(r => fmtB(r.income_before_tax)) },
              { label: 'Net Income', bold: true, values: inc.map(r => fmtB(r.net_income)) },
              { label: 'Total Comprehensive Income', bold: true, values: inc.map(r => fmtB(r.total_comprehensive_income)) },
              { label: 'Earnings per Share (IDR, full amount)', bold: true, values: inc.map(r => fmtB(r.eps)) },
            ]}
          />

          {/* ── Ratios — Capital ── */}
          <FinTable
            title="Financial Ratios — Capital"
            years={years}
            rows={[
              { label: 'Capital Adequacy Ratio (CAR)', bold: true, values: rat.map(r => fmtPct(r.car)) },
              { label: 'CAR Tier 1', indent: true, values: rat.map(r => fmtPct(r.car_tier1)) },
              { label: 'CAR Tier 2', indent: true, values: rat.map(r => fmtPct(r.car_tier2)) },
            ]}
          />

          <FinTable
            title="Financial Ratios — Assets Quality"
            years={years}
            rows={[
              { label: 'NPL Gross', bold: true, values: rat.map(r => fmtPct(r.npl_gross)) },
              { label: 'NPL Net', values: rat.map(r => fmtPct(r.npl_net)) },
              { label: 'Loan at Risk (LAR)', values: rat.map(r => fmtPct(r.lar)) },
            ]}
          />

          <FinTable
            title="Financial Ratios — Rentability"
            years={years}
            rows={[
              { label: 'Return on Assets (ROA)', bold: true, values: rat.map(r => fmtPct(r.roa)) },
              { label: 'Return on Equity (ROE)', bold: true, values: rat.map(r => fmtPct(r.roe)) },
              { label: 'Net Interest Margin (NIM)', bold: true, values: rat.map(r => fmtPct(r.nim)) },
              { label: 'Cost to Income Ratio (CIR)', values: rat.map(r => fmtPct(r.cir)) },
              { label: 'BOPO', values: rat.map(r => fmtPct(r.bopo)) },
            ]}
          />

          <FinTable
            title="Financial Ratios — Liquidity"
            years={years}
            rows={[
              { label: 'Loan to Deposit Ratio (LDR)', bold: true, values: rat.map(r => fmtPct(r.ldr)) },
              { label: 'Liquidity Coverage Ratio (LCR)', values: rat.map(r => fmtPct(r.lcr)) },
              { label: 'Net Stable Funding Ratio (NSFR)', values: rat.map(r => fmtPct(r.nsfr)) },
              { label: 'CASA to Third Party Funds', values: rat.map(r => fmtPct(r.casa_ratio)) },
            ]}
          />

          {/* ── Stock Highlights ── */}
          <FinTable
            title="Stock and Bond Highlights (in Rupiah)"
            years={stk.map(r => r.year)}
            rows={[
              { label: 'Highest Price', values: stk.map(r => fmtB(r.highest)) },
              { label: 'Lowest Price', values: stk.map(r => fmtB(r.lowest)) },
              { label: 'Closing Price', bold: true, values: stk.map(r => fmtB(r.closing)) },
              { label: 'Market Capitalization (Trillion IDR)', bold: true, values: stk.map(r => fmtB(r.market_cap_trillion)) },
              { label: 'Earnings per Share (IDR)', values: stk.map(r => fmtB(r.eps)) },
              { label: 'Book Value per Share (IDR)', values: stk.map(r => fmtB(r.bvps)) },
              { label: 'P/E (x)', bold: true, values: stk.map(r => fmtX(r.pe)) },
              { label: 'P/BV (x)', bold: true, values: stk.map(r => fmtX(r.pbv)) },
            ]}
          />

          <p style={{ fontSize: 11, color: 'var(--color-text-muted)', margin: 0 }}>
            All figures in Billion Rupiah unless otherwise stated. Source: {highlights.source}
          </p>
        </>
      )}
    </div>
  );
}
