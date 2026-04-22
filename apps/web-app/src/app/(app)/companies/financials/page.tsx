'use client';
import { useCallback, useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useCompanyStore } from '@/stores/company';
import { CompanySelector } from '@/components/companies/CompanySelector';

// -- Types --------------------------------------------------------------------
interface FinancialRow {
  symbol: string;
  period: string;
  statement_type: string;
  revenue: string | null;
  net_income: string | null;
  total_assets: string | null;
  total_liabilities: string | null;
  total_equity: string | null;
  operating_income: string | null;
  gross_profit: string | null;
  operating_cash_flow: string | null;
  capex: string | null;
  free_cash_flow: string | null;
}

type StatementTab = 'income' | 'balance' | 'cashflow';

// -- Formatters ---------------------------------------------------------------
function safeNum(v: string | null | undefined): number | null {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return isFinite(n) ? n : null;
}

function fmtB(v: string | null | undefined): string {
  const n = safeNum(v);
  if (n === null) return '—';
  const b = n / 1e9;
  return b.toLocaleString('id-ID', { maximumFractionDigits: 1 }) + ' B';
}

function fmtT(v: string | null | undefined): string {
  const n = safeNum(v);
  if (n === null) return '—';
  const t = n / 1e12;
  return t.toFixed(2) + ' T';
}

function fmtAuto(v: string | null | undefined): string {
  const n = safeNum(v);
  if (n === null) return '—';
  if (Math.abs(n) >= 1e12) return fmtT(v);
  return fmtB(v);
}

function pctChange(curr: string | null, prev: string | null): string | null {
  const c = safeNum(curr);
  const p = safeNum(prev);
  if (c === null || p === null || p === 0) return null;
  return (((c - p) / Math.abs(p)) * 100).toFixed(1);
}

// -- Growth Badge -------------------------------------------------------------
function GrowthBadge({ pct }: { pct: string | null }) {
  if (pct === null) return <span style={{ color: 'var(--color-text-muted)', fontSize: 10 }}>—</span>;
  const n = Number(pct);
  const pos = n >= 0;
  return (
    <span style={{
      fontSize: 10, fontWeight: 700,
      color: pos ? 'var(--color-positive)' : 'var(--color-negative)',
    }}>
      {pos ? '+' : ''}{pct}%
    </span>
  );
}

// -- Statement row definitions ------------------------------------------------
type RowDef = {
  label: string;
  key: keyof FinancialRow;
  bold?: boolean;
  indent?: boolean;
};

const INCOME_ROWS: RowDef[] = [
  { label: 'Revenue / Interest Income', key: 'revenue', bold: true },
  { label: 'Gross Profit', key: 'gross_profit', indent: true },
  { label: 'Operating Income (EBIT)', key: 'operating_income', indent: true },
  { label: 'Net Income', key: 'net_income', bold: true },
];

const BALANCE_ROWS: RowDef[] = [
  { label: 'Total Assets', key: 'total_assets', bold: true },
  { label: 'Total Liabilities', key: 'total_liabilities', indent: true },
  { label: 'Total Equity', key: 'total_equity', bold: true },
];

const CASHFLOW_ROWS: RowDef[] = [
  { label: 'Operating Cash Flow', key: 'operating_cash_flow', bold: true },
  { label: 'Capital Expenditure', key: 'capex', indent: true },
  { label: 'Free Cash Flow', key: 'free_cash_flow', bold: true },
];

const ROWS_MAP: Record<StatementTab, RowDef[]> = {
  income: INCOME_ROWS,
  balance: BALANCE_ROWS,
  cashflow: CASHFLOW_ROWS,
};

// -- Main Page ----------------------------------------------------------------
export default function FinancialsPage() {
  const { data: session } = useSession();
  const { selectedSymbol } = useCompanyStore();
  const [tab, setTab] = useState<StatementTab>('income');
  const [rows, setRows] = useState<FinancialRow[]>([]);
  const [loading, setLoading] = useState(false);

  const authHeader = useCallback((): Record<string, string> => {
    const token = (session as { accessToken?: string } | null)?.accessToken;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [session]);

  useEffect(() => {
    const token = (session as { accessToken?: string } | null)?.accessToken;
    if (!token || !selectedSymbol) return;
    setLoading(true);
    fetch(`/api/v1/stocks/${selectedSymbol}/financials?statement_type=${tab}`, {
      headers: authHeader(),
    })
      .then(r => r.json())
      .then((data: FinancialRow[]) => setRows(Array.isArray(data) ? data : []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, [selectedSymbol, session, tab, authHeader]);

  // Periods as columns (sorted ascending for display)
  const periods = rows.map(r => r.period).sort((a, b) => a.localeCompare(b));

  // Quick lookup
  const byPeriod: Record<string, FinancialRow> = Object.fromEntries(
    rows.map(r => [r.period, r]),
  );

  const rowDefs = ROWS_MAP[tab];

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
          { id: 'income',   label: 'Income Statement' },
          { id: 'balance',  label: 'Balance Sheet' },
          { id: 'cashflow', label: 'Cash Flow' },
        ] as const).map(t => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            style={{
              padding: '10px 20px', fontSize: 13, fontWeight: tab === t.id ? 700 : 500,
              border: 'none', background: 'transparent', cursor: 'pointer',
              borderBottom: `2px solid ${tab === t.id ? 'var(--color-blue-primary)' : 'transparent'}`,
              color: tab === t.id ? 'var(--color-blue-primary)' : 'var(--color-text-secondary)',
              marginBottom: -1,
            }}
          >
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
        ) : rows.length === 0 ? (
          <div style={{ padding: 60, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13 }}>
            <p style={{ marginBottom: 8 }}>No {tab} data available for {selectedSymbol}</p>
            <p style={{ fontSize: 11 }}>Financial data is sourced from IDX XBRL filings. Data may not be available for all companies.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ background: 'var(--color-bg-page)', borderBottom: '1px solid var(--color-border)' }}>
                  <th style={{
                    padding: '10px 16px', textAlign: 'left', fontSize: 10, fontWeight: 700,
                    textTransform: 'uppercase', letterSpacing: '0.06em',
                    color: 'var(--color-text-muted)', minWidth: 200, position: 'sticky', left: 0,
                    background: 'var(--color-bg-page)', zIndex: 1,
                  }}>
                    Metric
                  </th>
                  {periods.map((p, i) => (
                    <th key={p} style={{
                      padding: '10px 16px', textAlign: 'right', fontSize: 10, fontWeight: 700,
                      textTransform: 'uppercase', letterSpacing: '0.06em',
                      color: i === periods.length - 1 ? 'var(--color-blue-primary)' : 'var(--color-text-muted)',
                      minWidth: 120,
                    }}>
                      {p}
                    </th>
                  ))}
                  <th style={{
                    padding: '10px 16px', textAlign: 'right', fontSize: 10, fontWeight: 700,
                    textTransform: 'uppercase', letterSpacing: '0.06em',
                    color: 'var(--color-text-muted)', minWidth: 80,
                  }}>
                    YoY
                  </th>
                </tr>
              </thead>
              <tbody>
                {rowDefs.map((def, ri) => {
                  const latestPeriod = periods.length > 0 ? periods[periods.length - 1] : undefined;
                  const prevPeriod = periods.length > 1 ? periods[periods.length - 2] : undefined;
                  const latestRow = latestPeriod ? byPeriod[latestPeriod] : undefined;
                  const prevRow = prevPeriod ? byPeriod[prevPeriod] : undefined;
                  const latestVal = (latestRow?.[def.key] ?? null) as string | null;
                  const prevVal = (prevRow?.[def.key] ?? null) as string | null;
                  const growth = pctChange(latestVal, prevVal);

                  return (
                    <tr key={def.key} style={{
                      borderBottom: '1px solid var(--color-border-subtle)',
                      background: ri % 2 === 0 ? 'transparent' : 'rgba(0,0,0,0.01)',
                    }}>
                      <td style={{
                        padding: '10px 16px',
                        paddingLeft: def.indent ? 28 : 16,
                        fontWeight: def.bold ? 700 : 400,
                        color: def.bold ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                        position: 'sticky', left: 0,
                        background: ri % 2 === 0 ? '#fff' : 'rgba(248,250,252,1)',
                        zIndex: 1,
                      }}>
                        {def.label}
                      </td>
                      {periods.map(p => {
                        const row = byPeriod[p];
                        const val = (row?.[def.key] ?? null) as string | null;
                        return (
                          <td key={p} style={{
                            padding: '10px 16px', textAlign: 'right',
                            fontWeight: def.bold ? 700 : 400,
                            color: def.bold ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                            fontFamily: 'monospace',
                          }}>
                            {fmtAuto(val)}
                          </td>
                        );
                      })}
                      <td style={{ padding: '10px 16px', textAlign: 'right' }}>
                        <GrowthBadge pct={growth} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Source note */}
      <p style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
        Source: IDX XBRL filings · Values in IDR · B = Billion, T = Trillion · YoY = latest vs prior period
      </p>
    </div>
  );
}
