'use client';
import { Fragment, useCallback, useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useCompanyStore } from '@/stores/company';
import { CompanySelector } from '@/components/companies/CompanySelector';

// -- Types --------------------------------------------------------------------
interface FactRow {
  label: string;
  metric: string;
  bold: boolean;
  indent: boolean;
  values: Record<string, string | null>;
}
interface FactSection {
  title: string;
  rows: FactRow[];
}
interface FinancialFactsResponse {
  symbol: string;
  periods: string[];
  sections: FactSection[];
}

type StatementTab = 'income_current' | 'balance_current';

// -- Formatters ---------------------------------------------------------------
function safeNum(v: string | null | undefined): number | null {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return isFinite(n) ? n : null;
}

function fmtValue(v: string | null | undefined, isEps?: boolean): string {
  const n = safeNum(v);
  if (n === null) return '—';
  if (isEps) return n.toLocaleString('id-ID', { maximumFractionDigits: 0 });
  const abs = Math.abs(n);
  const sign = n < 0 ? '-' : '';
  if (abs >= 1e12) return `${sign}${(abs / 1e12).toFixed(2)} T`;
  if (abs >= 1e9)  return `${sign}${(abs / 1e9).toFixed(1)} B`;
  if (abs >= 1e6)  return `${sign}${(abs / 1e6).toFixed(1)} M`;
  return n.toLocaleString('id-ID');
}

function pctChange(curr: string | null, prev: string | null): number | null {
  const c = safeNum(curr);
  const p = safeNum(prev);
  if (c === null || p === null || p === 0) return null;
  return ((c - p) / Math.abs(p)) * 100;
}

// -- Growth chip --------------------------------------------------------------
function GrowthChip({ pct }: { pct: number | null }) {
  if (pct === null) return <span style={{ color: 'var(--color-text-muted)', fontSize: 10 }}>—</span>;
  const pos = pct >= 0;
  return (
    <span style={{
      fontSize: 10, fontWeight: 700,
      color: pos ? 'var(--color-positive)' : 'var(--color-negative)',
    }}>
      {pos ? '+' : ''}{pct.toFixed(1)}%
    </span>
  );
}

// -- Main Page ----------------------------------------------------------------
export default function FinancialsPage() {
  const { data: session } = useSession();
  const { selectedSymbol } = useCompanyStore();
  const [tab, setTab] = useState<StatementTab>('income_current');
  const [data, setData] = useState<FinancialFactsResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const authHeader = useCallback((): Record<string, string> => {
    const token = (session as { accessToken?: string } | null)?.accessToken;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [session]);

  useEffect(() => {
    const token = (session as { accessToken?: string } | null)?.accessToken;
    if (!token || !selectedSymbol) return;
    setLoading(true);
    setData(null);
    fetch(
      `/api/v1/stocks/${selectedSymbol}/financial-facts?context_type=${tab}`,
      { headers: authHeader() },
    )
      .then(r => r.json())
      .then((d: FinancialFactsResponse) => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [selectedSymbol, session, tab, authHeader]);

  const periods = data?.periods ?? [];
  const latestPeriod = periods.length > 0 ? periods[periods.length - 1] : undefined;
  const prevPeriod = periods.length > 1 ? periods[periods.length - 2] : undefined;

  return (
    <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 2 }}>
            Financial Statements
          </h1>
          <p style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
            {selectedSymbol} · IDX XBRL · IDR
          </p>
        </div>
        <CompanySelector />
      </div>

      {/* Statement tabs */}
      <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid var(--color-border)' }}>
        {([
          { id: 'income_current',  label: 'Income Statement' },
          { id: 'balance_current', label: 'Balance Sheet' },
        ] as const).map(t => (
          <button key={t.id} type="button" onClick={() => setTab(t.id)} style={{
            padding: '10px 20px', fontSize: 13, fontWeight: tab === t.id ? 700 : 500,
            border: 'none', background: 'transparent', cursor: 'pointer',
            borderBottom: `2px solid ${tab === t.id ? 'var(--color-blue-primary)' : 'transparent'}`,
            color: tab === t.id ? 'var(--color-blue-primary)' : 'var(--color-text-secondary)',
            marginBottom: -1,
          }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 8, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 60, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13 }}>
            Loading financial data…
          </div>
        ) : !data || data.sections.length === 0 ? (
          <div style={{ padding: 60, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13 }}>
            <p style={{ marginBottom: 8, fontWeight: 600 }}>No data available for {selectedSymbol}</p>
            <p style={{ fontSize: 11 }}>Financial data is sourced from IDX XBRL filings.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ background: 'var(--color-bg-page)', borderBottom: '2px solid var(--color-border)' }}>
                  <th style={{
                    padding: '10px 16px', textAlign: 'left', fontSize: 10, fontWeight: 700,
                    textTransform: 'uppercase', letterSpacing: '0.06em',
                    color: 'var(--color-text-muted)', minWidth: 240,
                    position: 'sticky', left: 0, background: 'var(--color-bg-page)', zIndex: 2,
                  }}>
                    Metric
                  </th>
                  {periods.map((p, i) => (
                    <th key={p} style={{
                      padding: '10px 16px', textAlign: 'right', fontSize: 10, fontWeight: 700,
                      textTransform: 'uppercase', letterSpacing: '0.06em', minWidth: 120,
                      color: i === periods.length - 1 ? 'var(--color-blue-primary)' : 'var(--color-text-muted)',
                    }}>
                      {p}
                    </th>
                  ))}
                  <th style={{
                    padding: '10px 16px', textAlign: 'right', fontSize: 10, fontWeight: 700,
                    textTransform: 'uppercase', letterSpacing: '0.06em',
                    color: 'var(--color-text-muted)', minWidth: 70,
                  }}>
                    YoY
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.sections.map((section, si) => (
                  <Fragment key={`section-${si}`}>
                    {/* Section header */}
                    <tr>
                      <td colSpan={periods.length + 2} style={{
                        padding: '10px 16px 6px',
                        fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
                        letterSpacing: '0.08em', color: 'var(--color-blue-primary)',
                        background: 'rgba(0,87,168,0.04)',
                        borderTop: si > 0 ? '1px solid var(--color-border)' : 'none',
                        borderBottom: '1px solid var(--color-border)',
                      }}>
                        {section.title}
                      </td>
                    </tr>
                    {section.rows.map((row, ri) => {
                      const isEps = row.metric.includes('EarningsPerShare')
                        || row.metric.includes('EarningsLossPerShare');
                      const latestVal = latestPeriod ? (row.values[latestPeriod] ?? null) : null;
                      const prevVal = prevPeriod ? (row.values[prevPeriod] ?? null) : null;
                      const growth = pctChange(latestVal, prevVal);
                      return (
                        <tr key={`${si}-${ri}`} style={{
                          borderBottom: '1px solid var(--color-border-subtle)',
                          background: row.bold ? 'rgba(0,0,0,0.01)' : 'transparent',
                        }}>
                          <td style={{
                            padding: '9px 16px',
                            paddingLeft: row.indent ? 28 : 16,
                            fontWeight: row.bold ? 700 : 400,
                            color: row.bold ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                            position: 'sticky', left: 0, zIndex: 1,
                            background: row.bold ? 'rgba(248,250,252,1)' : '#fff',
                          }}>
                            {row.label}
                          </td>
                          {periods.map(p => (
                            <td key={p} style={{
                              padding: '9px 16px', textAlign: 'right',
                              fontFamily: 'monospace', fontSize: 12,
                              fontWeight: row.bold ? 700 : 400,
                              color: row.bold ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                            }}>
                              {fmtValue(row.values[p] ?? null, isEps)}
                            </td>
                          ))}
                          <td style={{ padding: '9px 16px', textAlign: 'right' }}>
                            <GrowthChip pct={growth} />
                          </td>
                        </tr>
                      );
                    })}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
        Source: IDX XBRL · Values in IDR · T = Trillion, B = Billion · YoY compares latest vs prior period
      </p>
    </div>
  );
}
