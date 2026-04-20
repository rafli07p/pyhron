'use client';

import { useEffect, useState, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { RefreshCw } from 'lucide-react';
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';

interface HoldingRow {
  symbol: string;
  company_name: string;
  quantity: number;
  avg_entry_price: number;
  current_price: number | null;
  market_value: number;
  cost_basis: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  weight: number;
  day_change_pct: number | null;
}

interface PortfolioSummary {
  total_market_value: number;
  total_cost_basis: number;
  total_unrealized_pnl: number;
  total_unrealized_pnl_pct: number;
  total_realized_pnl: number;
  num_positions: number;
  as_of: string;
}

const COLORS = ['#0057A8', '#00875A', '#F59E0B', '#6366F1', '#EC4899', '#14B8A6', '#F97316'];

function fmtB(v: number): string {
  const abs = Math.abs(v);
  const sign = v < 0 ? '-' : '';
  if (abs >= 1e12) return sign + (abs / 1e12).toFixed(2) + 'T';
  if (abs >= 1e9) return sign + (abs / 1e9).toFixed(1) + 'B';
  if (abs >= 1e6) return sign + (abs / 1e6).toFixed(1) + 'M';
  return v.toLocaleString('id-ID');
}

function KpiCard({ label, value, sub, positive }: {
  label: string;
  value: string;
  sub?: string;
  positive?: boolean;
}) {
  return (
    <div style={{
      background: '#fff', border: '1px solid var(--color-border)',
      borderRadius: 8, padding: '16px 20px',
    }}>
      <p style={{
        fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
        letterSpacing: '0.08em', color: 'var(--color-text-muted)', marginBottom: 8,
      }}>
        {label}
      </p>
      <p style={{
        fontSize: 22, fontWeight: 700, margin: 0,
        color: positive === undefined
          ? 'var(--color-text-primary)'
          : positive ? 'var(--color-positive)' : 'var(--color-negative)',
      }}>
        {value}
      </p>
      {sub && (
        <p style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 4 }}>{sub}</p>
      )}
    </div>
  );
}

export default function PortfolioPage() {
  const { data: session } = useSession();
  const [holdings, setHoldings] = useState<HoldingRow[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const authHeader = useCallback((): Record<string, string> => {
    const token = (session as { accessToken?: string } | null)?.accessToken;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [session]);

  const fetchAll = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    try {
      const [holdRes, sumRes] = await Promise.all([
        fetch('/api/v1/portfolio/holdings', { headers: authHeader() }),
        fetch('/api/v1/portfolio/summary', { headers: authHeader() }),
      ]);
      if (holdRes.ok) setHoldings(await holdRes.json());
      if (sumRes.ok) setSummary(await sumRes.json());
    } catch {
      /* noop */
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [authHeader]);

  useEffect(() => {
    if (session) void fetchAll();
  }, [session, fetchAll]);

  const allocationData = holdings.map((h, i) => ({
    name: h.symbol,
    value: h.weight,
    color: COLORS[i % COLORS.length] ?? '#0057A8',
  }));

  const pnlData = [...holdings]
    .sort((a, b) => b.unrealized_pnl - a.unrealized_pnl)
    .map(h => ({
      symbol: h.symbol,
      pnl: Math.round(h.unrealized_pnl / 1e6),
      fill: h.unrealized_pnl >= 0 ? 'var(--color-positive)' : 'var(--color-negative)',
    }));

  const isPositive = (summary?.total_unrealized_pnl ?? 0) >= 0;

  return (
    <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 2 }}>
            Portfolio
          </h1>
          <p style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
            Demo IDX Blue Chip Portfolio • As of {summary?.as_of ?? '—'}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void fetchAll(true)}
          disabled={refreshing}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '6px 14px', borderRadius: 6, fontSize: 12, fontWeight: 600,
            background: 'var(--color-blue-primary)', color: 'white',
            border: 'none', cursor: 'pointer', opacity: refreshing ? 0.7 : 1,
          }}
        >
          <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
          Refresh Prices
        </button>
      </div>

      {loading ? (
        <div style={{ padding: 80, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13 }}>
          Loading portfolio data…
        </div>
      ) : (
        <>
          {summary && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
              <KpiCard
                label="Total Market Value"
                value={'IDR ' + fmtB(summary.total_market_value)}
                sub={`${summary.num_positions} positions`}
              />
              <KpiCard
                label="Total Cost Basis"
                value={'IDR ' + fmtB(summary.total_cost_basis)}
              />
              <KpiCard
                label="Unrealized P&L"
                value={(isPositive ? '+' : '') + 'IDR ' + fmtB(summary.total_unrealized_pnl)}
                sub={`${isPositive ? '+' : ''}${summary.total_unrealized_pnl_pct.toFixed(2)}%`}
                positive={isPositive}
              />
              <KpiCard
                label="Realized P&L"
                value={'IDR ' + fmtB(summary.total_realized_pnl)}
                positive={summary.total_realized_pnl >= 0}
              />
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 8, padding: '14px 16px' }}>
              <p style={{
                fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
                letterSpacing: '0.08em', color: 'var(--color-text-muted)', marginBottom: 12,
              }}>
                Portfolio Allocation
              </p>
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie
                    data={allocationData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={90}
                    label={({ name, value }) => `${name} ${value}%`}
                    labelLine={true}
                  >
                    {allocationData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={v => [`${Number(v).toFixed(1)}%`, 'Weight']} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 8, padding: '14px 16px' }}>
              <p style={{
                fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
                letterSpacing: '0.08em', color: 'var(--color-text-muted)', marginBottom: 12,
              }}>
                Unrealized P&L by Position (IDR Million)
              </p>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={pnlData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={v => v + 'M'} />
                  <YAxis type="category" dataKey="symbol" tick={{ fontSize: 11 }} width={45} />
                  <Tooltip formatter={v => ['IDR ' + Number(v) + 'M', 'Unrealized P&L']} />
                  <Legend />
                  <Bar dataKey="pnl" radius={[0, 3, 3, 0]}>
                    {pnlData.map((entry, i) => (
                      <Cell key={i} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 8, overflow: 'hidden' }}>
            <div style={{
              padding: '12px 16px', borderBottom: '1px solid var(--color-border)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)' }}>
                Holdings
              </span>
              <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                {holdings.length} positions
              </span>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: 'var(--color-bg-page)', borderBottom: '1px solid var(--color-border)' }}>
                    {['Symbol', 'Company', 'Qty', 'Avg Entry', 'Current Price', 'Market Value', 'Cost Basis', 'Unrealized P&L', 'P&L %', 'Day Change', 'Weight'].map(h => (
                      <th key={h} style={{
                        padding: '9px 14px',
                        textAlign: h === 'Symbol' || h === 'Company' ? 'left' : 'right',
                        fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
                        textTransform: 'uppercase', color: 'var(--color-text-muted)',
                        whiteSpace: 'nowrap',
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {holdings.map((h, i) => {
                    const pnlPos = h.unrealized_pnl >= 0;
                    const dayPos = (h.day_change_pct ?? 0) >= 0;
                    return (
                      <tr key={h.symbol} style={{
                        borderBottom: '1px solid var(--color-border-subtle)',
                        background: i % 2 === 0 ? 'transparent' : 'rgba(0,0,0,0.01)',
                      }}>
                        <td style={{
                          padding: '10px 14px', fontWeight: 700,
                          color: 'var(--color-blue-primary)', fontFamily: 'monospace',
                        }}>
                          {h.symbol}
                        </td>
                        <td style={{
                          padding: '10px 14px', color: 'var(--color-text-secondary)',
                          maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                        }}>
                          {h.company_name}
                        </td>
                        <td style={{ padding: '10px 14px', textAlign: 'right', color: 'var(--color-text-secondary)' }}>
                          {h.quantity.toLocaleString('id-ID')}
                        </td>
                        <td style={{ padding: '10px 14px', textAlign: 'right', color: 'var(--color-text-secondary)' }}>
                          {h.avg_entry_price.toLocaleString('id-ID')}
                        </td>
                        <td style={{
                          padding: '10px 14px', textAlign: 'right', fontWeight: 600,
                          color: 'var(--color-text-primary)',
                        }}>
                          {h.current_price ? h.current_price.toLocaleString('id-ID') : '—'}
                        </td>
                        <td style={{
                          padding: '10px 14px', textAlign: 'right', fontWeight: 600,
                          color: 'var(--color-text-primary)',
                        }}>
                          {fmtB(h.market_value)}
                        </td>
                        <td style={{ padding: '10px 14px', textAlign: 'right', color: 'var(--color-text-secondary)' }}>
                          {fmtB(h.cost_basis)}
                        </td>
                        <td style={{
                          padding: '10px 14px', textAlign: 'right', fontWeight: 600,
                          color: pnlPos ? 'var(--color-positive)' : 'var(--color-negative)',
                        }}>
                          {pnlPos ? '+' : ''}{fmtB(h.unrealized_pnl)}
                        </td>
                        <td style={{
                          padding: '10px 14px', textAlign: 'right', fontWeight: 600,
                          color: pnlPos ? 'var(--color-positive)' : 'var(--color-negative)',
                        }}>
                          {pnlPos ? '+' : ''}{h.unrealized_pnl_pct.toFixed(2)}%
                        </td>
                        <td style={{
                          padding: '10px 14px', textAlign: 'right',
                          color: h.day_change_pct === null
                            ? 'var(--color-text-muted)'
                            : dayPos ? 'var(--color-positive)' : 'var(--color-negative)',
                        }}>
                          {h.day_change_pct !== null
                            ? `${dayPos ? '+' : ''}${h.day_change_pct.toFixed(2)}%`
                            : '—'}
                        </td>
                        <td style={{ padding: '10px 14px', textAlign: 'right', color: 'var(--color-text-secondary)' }}>
                          {h.weight.toFixed(1)}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <p style={{ fontSize: 11, color: 'var(--color-text-muted)', margin: 0 }}>
            Demo portfolio for illustration purposes. Prices sourced from Yahoo Finance.
            Data may be delayed.
          </p>
        </>
      )}
    </div>
  );
}
