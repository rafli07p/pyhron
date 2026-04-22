"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSession } from "next-auth/react";
import Link from "next/link";

// ---------- Types ----------
interface Strategy {
  id: string;
  name: string;
  strategy_type: string;
  is_enabled: boolean;
  parameters: Record<string, unknown>;
  risk_limits: Record<string, number>;
  description: string | null;
  created_at: string;
  updated_at: string;
}

interface StrategyPerformance {
  strategy_id: string;
  name: string;
  total_return_pct: number | string | null;
  sharpe_ratio: number | string | null;
  max_drawdown_pct: number | string | null;
  win_rate: number | string | null;
  total_trades: number;
  avg_holding_period_days: number | string | null;
  period_start: string | null;
  period_end: string | null;
}

type EnrichedStrategy = Strategy & { perf?: StrategyPerformance };

// ---------- Formatters ----------
const safeNum = (v: unknown): number | null => {
  if (v === null || v === undefined) return null;
  const n = typeof v === "number" ? v : parseFloat(String(v));
  return Number.isFinite(n) ? n : null;
};

const fmtPct = (v: unknown, digits = 2): string => {
  const n = safeNum(v);
  if (n === null) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(digits)}%`;
};

const fmtNum = (v: unknown, digits = 2): string => {
  const n = safeNum(v);
  if (n === null) return "—";
  return n.toFixed(digits);
};

const fmtDate = (iso: string | null | undefined): string => {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return "—";
  }
};

// ---------- Badges ----------
function StatusBadge({ enabled }: { enabled: boolean }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "3px 10px",
        borderRadius: 12,
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: 0.3,
        textTransform: "uppercase",
        background: enabled ? "rgba(0, 135, 90, 0.1)" : "rgba(107, 114, 128, 0.1)",
        color: enabled ? "var(--color-positive)" : "#6b7280",
        border: `1px solid ${enabled ? "rgba(0, 135, 90, 0.3)" : "rgba(107, 114, 128, 0.25)"}`,
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: enabled ? "var(--color-positive)" : "#9ca3af",
          animation: enabled ? "pulse 2s ease-in-out infinite" : undefined,
        }}
      />
      {enabled ? "Enabled" : "Inactive"}
    </span>
  );
}

function TypeBadge({ type }: { type: string }) {
  const palette: Record<string, { bg: string; fg: string; border: string }> = {
    momentum: { bg: "rgba(0, 87, 168, 0.1)", fg: "var(--color-blue-primary)", border: "rgba(0, 87, 168, 0.3)" },
    mean_reversion: { bg: "rgba(168, 85, 247, 0.1)", fg: "#a855f7", border: "rgba(168, 85, 247, 0.3)" },
    arbitrage: { bg: "rgba(217, 119, 6, 0.1)", fg: "#d97706", border: "rgba(217, 119, 6, 0.3)" },
    ml_signal: { bg: "rgba(6, 182, 212, 0.1)", fg: "#0891b2", border: "rgba(6, 182, 212, 0.3)" },
  };
  const c = palette[type] ?? { bg: "rgba(107, 114, 128, 0.1)", fg: "#374151", border: "rgba(107, 114, 128, 0.25)" };
  return (
    <span
      style={{
        display: "inline-block",
        padding: "3px 10px",
        borderRadius: 4,
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: 0.3,
        textTransform: "uppercase",
        background: c.bg,
        color: c.fg,
        border: `1px solid ${c.border}`,
      }}
    >
      {type.replace(/_/g, " ")}
    </span>
  );
}

// ---------- KPI Card ----------
function KpiCard({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: string;
  hint?: string;
  accent?: string;
}) {
  return (
    <div
      style={{
        background: "#fff",
        border: "1px solid var(--color-border)",
        borderRadius: 8,
        padding: "18px 20px",
        display: "flex",
        flexDirection: "column",
        gap: 6,
        minHeight: 92,
      }}
    >
      <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: 0.5, textTransform: "uppercase", color: "#6b7280" }}>
        {label}
      </div>
      <div style={{ fontSize: 26, fontWeight: 700, color: accent ?? "var(--color-text-primary)", lineHeight: 1.1 }}>
        {value}
      </div>
      {hint && <div style={{ fontSize: 12, color: "#6b7280" }}>{hint}</div>}
    </div>
  );
}

// ---------- Create Modal ----------
function CreateModal({
  open,
  onClose,
  onCreate,
  creating,
}: {
  open: boolean;
  onClose: () => void;
  onCreate: (body: { name: string; strategy_type: string; description: string }) => Promise<void>;
  creating: boolean;
}) {
  const [name, setName] = useState("");
  const [stype, setStype] = useState("momentum");
  const [description, setDescription] = useState("");

  useEffect(() => {
    if (!open) {
      setName("");
      setStype("momentum");
      setDescription("");
    }
  }, [open]);

  if (!open) return null;

  const canSubmit = name.trim().length > 0 && !creating;

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(15, 23, 42, 0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 50,
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: 480,
          background: "#fff",
          borderRadius: 10,
          padding: 24,
          boxShadow: "0 20px 40px rgba(0,0,0,0.15)",
        }}
      >
        <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>Create strategy</div>
        <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 20 }}>
          Register a new trading strategy. You can configure parameters later.
        </div>

        <label style={{ display: "block", marginBottom: 14 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 6 }}>Name</div>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Indonesia Blue-Chip Momentum"
            style={{
              width: "100%",
              padding: "8px 10px",
              border: "1px solid var(--color-border)",
              borderRadius: 6,
              fontSize: 14,
              outline: "none",
            }}
          />
        </label>

        <label style={{ display: "block", marginBottom: 14 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 6 }}>Type</div>
          <select
            value={stype}
            onChange={(e) => setStype(e.target.value)}
            style={{
              width: "100%",
              padding: "8px 10px",
              border: "1px solid var(--color-border)",
              borderRadius: 6,
              fontSize: 14,
              background: "#fff",
              outline: "none",
            }}
          >
            <option value="momentum">Momentum</option>
            <option value="mean_reversion">Mean Reversion</option>
            <option value="arbitrage">Arbitrage</option>
            <option value="ml_signal">ML Signal</option>
          </select>
        </label>

        <label style={{ display: "block", marginBottom: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 6 }}>Description (optional)</div>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            placeholder="Short description of the thesis..."
            style={{
              width: "100%",
              padding: "8px 10px",
              border: "1px solid var(--color-border)",
              borderRadius: 6,
              fontSize: 14,
              outline: "none",
              resize: "vertical",
              fontFamily: "inherit",
            }}
          />
        </label>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button
            type="button"
            onClick={onClose}
            disabled={creating}
            style={{
              padding: "8px 14px",
              border: "1px solid var(--color-border)",
              background: "#fff",
              borderRadius: 6,
              fontSize: 13,
              fontWeight: 600,
              cursor: creating ? "not-allowed" : "pointer",
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!canSubmit}
            onClick={() => onCreate({ name: name.trim(), strategy_type: stype, description: description.trim() })}
            style={{
              padding: "8px 14px",
              border: "none",
              background: canSubmit ? "var(--color-blue-primary)" : "#93b7db",
              color: "#fff",
              borderRadius: 6,
              fontSize: 13,
              fontWeight: 600,
              cursor: canSubmit ? "pointer" : "not-allowed",
            }}
          >
            {creating ? "Creating…" : "Create strategy"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------- Page ----------
export default function StrategiesPage() {
  const { data: session, status } = useSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;

  const [strategies, setStrategies] = useState<EnrichedStrategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  const authHeader = useMemo(
    (): HeadersInit => (token ? { Authorization: `Bearer ${token}` } : {}),
    [token],
  );

  const refresh = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/v1/strategies", { headers: authHeader });
      if (!res.ok) throw new Error(`Failed to load strategies (${res.status})`);
      const list = (await res.json()) as Strategy[];

      // Enrich with performance in parallel
      const enriched = await Promise.all(
        list.map(async (s) => {
          try {
            const pr = await fetch(`/api/v1/strategies/${s.id}/performance`, { headers: authHeader });
            if (!pr.ok) return s as EnrichedStrategy;
            const perf = (await pr.json()) as StrategyPerformance;
            return { ...s, perf } as EnrichedStrategy;
          } catch {
            return s as EnrichedStrategy;
          }
        }),
      );
      setStrategies(enriched);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load strategies");
      setStrategies([]);
    } finally {
      setLoading(false);
    }
  }, [token, authHeader]);

  useEffect(() => {
    if (token) void refresh();
  }, [token, refresh]);

  const handleCreate = async (body: { name: string; strategy_type: string; description: string }) => {
    if (!token) return;
    setCreating(true);
    try {
      const res = await fetch("/api/v1/strategies", {
        method: "POST",
        headers: { ...authHeader, "Content-Type": "application/json" },
        body: JSON.stringify({
          name: body.name,
          strategy_type: body.strategy_type,
          description: body.description || null,
          parameters: {},
          risk_limits: {},
        }),
      });
      if (!res.ok) throw new Error(`Create failed (${res.status})`);
      setCreateOpen(false);
      await refresh();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to create strategy");
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (s: Strategy) => {
    if (!token) return;
    const action = s.is_enabled ? "disable" : "enable";
    setBusyId(s.id);
    try {
      const res = await fetch(`/api/v1/strategies/${s.id}/${action}`, {
        method: "POST",
        headers: authHeader,
      });
      if (!res.ok) throw new Error(`${action} failed (${res.status})`);
      await refresh();
    } catch (e) {
      alert(e instanceof Error ? e.message : `Failed to ${action}`);
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async (s: Strategy) => {
    if (!token) return;
    if (!confirm(`Delete strategy "${s.name}"? This cannot be undone.`)) return;
    setBusyId(s.id);
    try {
      const res = await fetch(`/api/v1/strategies/${s.id}`, { method: "DELETE", headers: authHeader });
      if (!res.ok && res.status !== 204) throw new Error(`Delete failed (${res.status})`);
      await refresh();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to delete strategy");
    } finally {
      setBusyId(null);
    }
  };

  // KPIs
  const kpis = useMemo(() => {
    const total = strategies.length;
    const active = strategies.filter((s) => s.is_enabled).length;
    const sharpeValues = strategies
      .map((s) => safeNum(s.perf?.sharpe_ratio))
      .filter((v): v is number => v !== null);
    const avgSharpe = sharpeValues.length ? sharpeValues.reduce((a, b) => a + b, 0) / sharpeValues.length : null;
    const totalTrades = strategies.reduce((sum, s) => sum + (s.perf?.total_trades ?? 0), 0);
    return { total, active, avgSharpe, totalTrades };
  }, [strategies]);

  return (
    <div style={{ padding: "24px 32px", maxWidth: 1600, margin: "0 auto" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-end",
          marginBottom: 20,
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: 1, textTransform: "uppercase", color: "#6b7280" }}>
            Research Platform
          </div>
          <h1 style={{ fontSize: 26, fontWeight: 700, margin: "4px 0 4px", color: "var(--color-text-primary)" }}>
            Strategies
          </h1>
          <div style={{ fontSize: 13, color: "#6b7280" }}>
            Manage trading strategies, review performance, and control live execution. Workflow:{" "}
            <span style={{ fontWeight: 600, color: "var(--color-text-primary)" }}>Strategies → Studio → Execution</span>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            type="button"
            onClick={() => void refresh()}
            disabled={loading || !token}
            style={{
              padding: "8px 14px",
              border: "1px solid var(--color-border)",
              background: "#fff",
              borderRadius: 6,
              fontSize: 13,
              fontWeight: 600,
              cursor: loading || !token ? "not-allowed" : "pointer",
              color: "#374151",
            }}
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            disabled={!token}
            style={{
              padding: "8px 14px",
              border: "none",
              background: "var(--color-blue-primary)",
              color: "#fff",
              borderRadius: 6,
              fontSize: 13,
              fontWeight: 600,
              cursor: !token ? "not-allowed" : "pointer",
            }}
          >
            + New strategy
          </button>
        </div>
      </div>

      {/* KPI Row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 12,
          marginBottom: 20,
        }}
      >
        <KpiCard label="Total strategies" value={String(kpis.total)} hint={`${kpis.active} active`} />
        <KpiCard
          label="Avg Sharpe (backtested)"
          value={kpis.avgSharpe === null ? "—" : fmtNum(kpis.avgSharpe, 2)}
          hint="From latest completed backtests"
          accent={
            kpis.avgSharpe === null
              ? undefined
              : kpis.avgSharpe >= 1
                ? "var(--color-positive)"
                : kpis.avgSharpe < 0
                  ? "var(--color-negative)"
                  : undefined
          }
        />
        <KpiCard
          label="Total trades"
          value={kpis.totalTrades.toLocaleString()}
          hint="Across all backtests"
        />
        <KpiCard
          label="Active now"
          value={String(kpis.active)}
          hint={kpis.total ? `${((kpis.active / kpis.total) * 100).toFixed(0)}% of portfolio` : "—"}
          accent={kpis.active > 0 ? "var(--color-positive)" : undefined}
        />
      </div>

      {/* Error / loading */}
      {status === "unauthenticated" && (
        <div
          style={{
            padding: 12,
            background: "rgba(217, 45, 32, 0.06)",
            border: "1px solid rgba(217, 45, 32, 0.25)",
            borderRadius: 6,
            color: "var(--color-negative)",
            fontSize: 13,
            marginBottom: 12,
          }}
        >
          Please sign in to manage strategies.
        </div>
      )}
      {error && (
        <div
          style={{
            padding: 12,
            background: "rgba(217, 45, 32, 0.06)",
            border: "1px solid rgba(217, 45, 32, 0.25)",
            borderRadius: 6,
            color: "var(--color-negative)",
            fontSize: 13,
            marginBottom: 12,
          }}
        >
          {error}
        </div>
      )}

      {/* Table */}
      <div
        style={{
          background: "#fff",
          border: "1px solid var(--color-border)",
          borderRadius: 8,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            padding: "14px 20px",
            borderBottom: "1px solid var(--color-border)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: "var(--color-text-primary)" }}>Strategy register</div>
            <div style={{ fontSize: 12, color: "#6b7280", marginTop: 2 }}>
              Enable, disable, and manage your strategy portfolio. Performance from latest completed backtest.
            </div>
          </div>
        </div>

        {loading ? (
          <div style={{ padding: 40, textAlign: "center", color: "#6b7280", fontSize: 13 }}>Loading strategies…</div>
        ) : strategies.length === 0 ? (
          <div style={{ padding: 48, textAlign: "center" }}>
            <div style={{ fontSize: 15, fontWeight: 600, color: "var(--color-text-primary)", marginBottom: 6 }}>
              No strategies yet
            </div>
            <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 16 }}>
              Create your first strategy to begin research and backtesting.
            </div>
            <button
              type="button"
              onClick={() => setCreateOpen(true)}
              disabled={!token}
              style={{
                padding: "10px 18px",
                border: "none",
                background: "var(--color-blue-primary)",
                color: "#fff",
                borderRadius: 6,
                fontSize: 13,
                fontWeight: 600,
                cursor: !token ? "not-allowed" : "pointer",
              }}
            >
              + Create your first strategy
            </button>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#f9fafb", borderBottom: "1px solid var(--color-border)" }}>
                  <th style={thStyle}>Strategy</th>
                  <th style={thStyle}>Type</th>
                  <th style={thStyle}>Status</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Total Return</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Sharpe</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Max DD</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Win Rate</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Trades</th>
                  <th style={thStyle}>Created</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {strategies.map((s) => {
                  const ret = safeNum(s.perf?.total_return_pct);
                  const dd = safeNum(s.perf?.max_drawdown_pct);
                  const busy = busyId === s.id;
                  return (
                    <tr
                      key={s.id}
                      style={{
                        borderBottom: "1px solid var(--color-border)",
                        opacity: busy ? 0.6 : 1,
                      }}
                    >
                      <td style={tdStyle}>
                        <div style={{ fontWeight: 600, color: "var(--color-text-primary)" }}>{s.name}</div>
                        {s.description && (
                          <div
                            style={{
                              fontSize: 12,
                              color: "#6b7280",
                              marginTop: 2,
                              maxWidth: 360,
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {s.description}
                          </div>
                        )}
                      </td>
                      <td style={tdStyle}>
                        <TypeBadge type={s.strategy_type} />
                      </td>
                      <td style={tdStyle}>
                        <StatusBadge enabled={s.is_enabled} />
                      </td>
                      <td
                        style={{
                          ...tdStyle,
                          textAlign: "right",
                          fontVariantNumeric: "tabular-nums",
                          fontWeight: 600,
                          color:
                            ret === null
                              ? "#9ca3af"
                              : ret > 0
                                ? "var(--color-positive)"
                                : ret < 0
                                  ? "var(--color-negative)"
                                  : "var(--color-text-primary)",
                        }}
                      >
                        {fmtPct(ret)}
                      </td>
                      <td style={{ ...tdStyle, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                        {fmtNum(s.perf?.sharpe_ratio)}
                      </td>
                      <td
                        style={{
                          ...tdStyle,
                          textAlign: "right",
                          fontVariantNumeric: "tabular-nums",
                          color: dd !== null && dd < 0 ? "var(--color-negative)" : undefined,
                        }}
                      >
                        {dd === null ? "—" : `${dd.toFixed(2)}%`}
                      </td>
                      <td style={{ ...tdStyle, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                        {s.perf?.win_rate == null ? "—" : `${safeNum(s.perf.win_rate)?.toFixed(1) ?? "—"}%`}
                      </td>
                      <td style={{ ...tdStyle, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                        {s.perf?.total_trades?.toLocaleString() ?? "—"}
                      </td>
                      <td style={{ ...tdStyle, color: "#6b7280" }}>{fmtDate(s.created_at)}</td>
                      <td style={{ ...tdStyle, textAlign: "right" }}>
                        <div style={{ display: "inline-flex", gap: 6, justifyContent: "flex-end" }}>
                          <Link
                            href={`/studio?strategy=${s.id}`}
                            style={{
                              padding: "5px 10px",
                              border: "1px solid var(--color-border)",
                              borderRadius: 4,
                              fontSize: 12,
                              fontWeight: 600,
                              color: "var(--color-blue-primary)",
                              background: "#fff",
                              textDecoration: "none",
                              whiteSpace: "nowrap",
                            }}
                          >
                            Backtest
                          </Link>
                          <button
                            type="button"
                            onClick={() => void handleToggle(s)}
                            disabled={busy || !token}
                            style={{
                              padding: "5px 10px",
                              border: `1px solid ${s.is_enabled ? "rgba(217, 119, 6, 0.4)" : "rgba(0, 135, 90, 0.4)"}`,
                              borderRadius: 4,
                              fontSize: 12,
                              fontWeight: 600,
                              color: s.is_enabled ? "#d97706" : "var(--color-positive)",
                              background: "#fff",
                              cursor: busy || !token ? "not-allowed" : "pointer",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {s.is_enabled ? "Disable" : "Enable"}
                          </button>
                          <button
                            type="button"
                            onClick={() => void handleDelete(s)}
                            disabled={busy || !token}
                            style={{
                              padding: "5px 10px",
                              border: "1px solid rgba(217, 45, 32, 0.4)",
                              borderRadius: 4,
                              fontSize: 12,
                              fontWeight: 600,
                              color: "var(--color-negative)",
                              background: "#fff",
                              cursor: busy || !token ? "not-allowed" : "pointer",
                            }}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Footer note */}
      <div style={{ marginTop: 16, fontSize: 12, color: "#6b7280" }}>
        Tip: Use <strong>Backtest</strong> to open a strategy in the Studio for parameter tuning, then promote it to{" "}
        <strong>Execution</strong> for paper or live trading.
      </div>

      <CreateModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreate={handleCreate}
        creating={creating}
      />

      <style jsx global>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}

// ---------- Styles ----------
const thStyle: React.CSSProperties = {
  padding: "10px 14px",
  textAlign: "left",
  fontSize: 11,
  fontWeight: 600,
  letterSpacing: 0.5,
  textTransform: "uppercase",
  color: "#6b7280",
  whiteSpace: "nowrap",
};

const tdStyle: React.CSSProperties = {
  padding: "12px 14px",
  verticalAlign: "middle",
};
