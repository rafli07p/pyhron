'use client';

import { useState, useEffect, useMemo } from 'react';
import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Button } from '@/design-system/primitives/Button';
import { Badge } from '@/design-system/primitives/Badge';
import { TierGate } from '@/components/common/TierGate';
import { useTierGate } from '@/hooks/useTierGate';
import { CandlestickChart, CandlestickChartSkeleton, type OHLCV } from '@/design-system/charts/CandlestickChart';
import { MOCK_IDX_STOCKS } from '@/mocks/generators/idx-stocks';
import { ChevronDown, ChevronRight, BarChart3, Layers, X, PanelLeftClose, PanelLeftOpen, Plus, Search } from 'lucide-react';

interface Overlay { id: string; type: string; label: string; period?: number; stddev?: number }
const TIMEFRAMES = ['1D', '1W', '1M'] as const;
const TECHNICAL_INDICATORS: Overlay[] = [
  { id: 'sma-20', type: 'sma', label: 'SMA(20)', period: 20 },
  { id: 'sma-50', type: 'sma', label: 'SMA(50)', period: 50 },
  { id: 'ema-20', type: 'ema', label: 'EMA(20)', period: 20 },
  { id: 'rsi-14', type: 'rsi', label: 'RSI(14)', period: 14 },
  { id: 'bb-20', type: 'bb', label: 'Bollinger Bands', period: 20, stddev: 2 },
  { id: 'macd', type: 'macd', label: 'MACD' },
  { id: 'atr-14', type: 'atr', label: 'ATR(14)', period: 14 },
];
const FUNDAMENTALS = ['P/E', 'P/B', 'ROE', 'Market Cap'];

// Indicator calculations
function computeSMA(closes: number[], period: number): number | null {
  if (closes.length < period) return null;
  const slice = closes.slice(-period);
  return slice.reduce((a, b) => a + b, 0) / period;
}

function computeRSI(closes: number[], period: number): number | null {
  if (closes.length < period + 1) return null;
  let gains = 0, losses = 0;
  for (let i = closes.length - period; i < closes.length; i++) {
    const diff = closes[i]! - closes[i - 1]!;
    if (diff > 0) gains += diff; else losses -= diff;
  }
  const rs = losses === 0 ? 100 : gains / losses;
  return 100 - (100 / (1 + rs));
}

function computeBollingerBands(closes: number[], period: number, stddev: number) {
  const sma = computeSMA(closes, period);
  if (sma === null) return null;
  const slice = closes.slice(-period);
  const variance = slice.reduce((sum, val) => sum + (val - sma) ** 2, 0) / period;
  const sd = Math.sqrt(variance) * stddev;
  return { upper: sma + sd, middle: sma, lower: sma - sd };
}

function CategorySection({ name, expanded, onToggle, children }: { name: string; expanded: boolean; onToggle: () => void; children: React.ReactNode }) {
  return (
    <div>
      <button onClick={onToggle} className="flex w-full items-center gap-1.5 rounded px-2 py-1.5 text-left text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--surface-3)]">
        {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        {name}
      </button>
      {expanded && <div className="ml-4 space-y-0.5">{children}</div>}
    </div>
  );
}

export default function WorkbenchPage() {
  const { hasAccess } = useTierGate('studio.workbench.create');
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>('BBCA');
  const [ohlcvData, setOhlcvData] = useState<OHLCV[]>([]);
  const [timeframe, setTimeframe] = useState<string>('1D');
  const [overlays, setOverlays] = useState<Overlay[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set(['Instruments']));
  const [showAddMenu, setShowAddMenu] = useState(false);

  useEffect(() => {
    if (!selectedSymbol) return;
    let cancelled = false;
    fetch(`/v1/market/ohlcv/${selectedSymbol}`)
      .then((r) => r.json())
      .then((json) => {
        if (cancelled) return;
        const bars: OHLCV[] = (json.data ?? json).map((b: { timestamp: string; open: number; high: number; low: number; close: number; volume: number }) => ({
          ...b, timestamp: Math.floor(new Date(b.timestamp).getTime() / 1000),
        }));
        setOhlcvData(bars);
      })
      .catch(() => { if (!cancelled) setOhlcvData([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [selectedSymbol]);

  const closes = useMemo(() => ohlcvData.map((d) => d.close), [ohlcvData]);
  const indicatorValues = useMemo(() => overlays.map((o) => {
    if ((o.type === 'sma' || o.type === 'ema') && o.period) return { ...o, value: computeSMA(closes, o.period) };
    if (o.type === 'rsi' && o.period) return { ...o, value: computeRSI(closes, o.period) };
    if (o.type === 'bb' && o.period && o.stddev) return { ...o, bands: computeBollingerBands(closes, o.period, o.stddev) };
    return { ...o, value: null };
  }), [overlays, closes]);

  const q = searchQuery.toLowerCase();
  const filteredStocks = useMemo(() => MOCK_IDX_STOCKS.filter((s) => s.symbol.toLowerCase().includes(q) || s.name.toLowerCase().includes(q)).slice(0, 10), [q]);
  const filteredIndicators = useMemo(() => TECHNICAL_INDICATORS.filter((i) => i.label.toLowerCase().includes(q)), [q]);
  const filteredFundamentals = useMemo(() => FUNDAMENTALS.filter((f) => f.toLowerCase().includes(q)), [q]);

  if (!hasAccess) {
    return (
      <div className="space-y-3">
        <PageHeader title="Workbench" description="Interactive charting and metric exploration" />
        <TierGate requiredTier="strategist" featureName="Workbench" />
      </div>
    );
  }

  const toggle = (name: string) => setExpanded((prev) => { const n = new Set(prev); if (n.has(name)) { n.delete(name); } else { n.add(name); } return n; });
  const addOverlay = (o: Overlay) => setOverlays((prev) => prev.some((x) => x.id === o.id) ? prev : [...prev, o]);
  const removeOverlay = (id: string) => setOverlays((prev) => prev.filter((o) => o.id !== id));
  const symbolInfo = MOCK_IDX_STOCKS.find((s) => s.symbol === selectedSymbol);
  const fmt = (n: number) => n.toLocaleString('id-ID', { maximumFractionDigits: 2 });
  const itemCls = (active: boolean) => `block w-full rounded px-2 py-1 text-left text-xs transition-colors ${active ? 'bg-[var(--accent-500)]/15 text-[var(--accent-500)] font-medium' : 'text-[var(--text-tertiary)] hover:bg-[var(--surface-3)] hover:text-[var(--text-primary)]'}`;

  return (
    <div className="space-y-4">
      <PageHeader title="Workbench" description="Interactive charting and metric exploration" />
      <div className={`grid gap-4 ${sidebarOpen ? 'lg:grid-cols-[240px_1fr]' : 'lg:grid-cols-1'}`}>
        {sidebarOpen && (
          <Card className="h-fit">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2"><Layers className="h-3.5 w-3.5" /> Metrics</CardTitle>
                <button onClick={() => setSidebarOpen(false)} className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)]"><PanelLeftClose className="h-4 w-4" /></button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="mb-3 relative">
                <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-[var(--text-tertiary)]" />
                <input className="flex h-8 w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-2)] pl-8 pr-3 text-xs text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-500)]" placeholder="Search metrics..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
              </div>
              <div className="space-y-1">
                <CategorySection name="Instruments" expanded={expanded.has('Instruments')} onToggle={() => toggle('Instruments')}>
                  {filteredStocks.map((s) => (
                    <button key={s.symbol} onClick={() => setSelectedSymbol(s.symbol)} className={itemCls(selectedSymbol === s.symbol)}>{s.symbol}</button>
                  ))}
                </CategorySection>
                <CategorySection name="Technical Indicators" expanded={expanded.has('Technical Indicators')} onToggle={() => toggle('Technical Indicators')}>
                  {filteredIndicators.map((ind) => (
                    <button key={ind.id} onClick={() => addOverlay(ind)} className={itemCls(overlays.some((o) => o.id === ind.id))}>{ind.label}</button>
                  ))}
                </CategorySection>
                <CategorySection name="Fundamentals" expanded={expanded.has('Fundamentals')} onToggle={() => toggle('Fundamentals')}>
                  {filteredFundamentals.map((f) => (
                    <div key={f} className="flex items-center justify-between rounded px-2 py-1 text-xs text-[var(--text-tertiary)] opacity-50 cursor-not-allowed">
                      <span>{f}</span>
                      <Badge variant="default" className="text-[10px] px-1.5 py-0">Coming soon</Badge>
                    </div>
                  ))}
                </CategorySection>
              </div>
            </CardContent>
          </Card>
        )}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {!sidebarOpen && <button onClick={() => setSidebarOpen(true)} className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)]"><PanelLeftOpen className="h-4 w-4" /></button>}
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="h-3.5 w-3.5" />
                    {selectedSymbol ?? 'Select Instrument'}
                    {symbolInfo && <span className="font-normal text-[var(--text-tertiary)]">— {symbolInfo.name}</span>}
                  </CardTitle>
                </div>
                <div className="flex gap-1">
                  {TIMEFRAMES.map((tf) => (
                    <button key={tf} onClick={() => setTimeframe(tf)} className={`rounded px-2 py-0.5 text-xs transition-colors ${timeframe === tf ? 'bg-[var(--accent-500)] text-white' : 'text-[var(--text-tertiary)] hover:bg-[var(--surface-3)] hover:text-[var(--text-primary)]'}`}>{tf}</button>
                  ))}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? <CandlestickChartSkeleton height={360} /> : <CandlestickChart data={ohlcvData} height={360} timeframe={timeframe} />}
              {overlays.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {overlays.map((o) => (
                    <Badge key={o.id} variant="accent" className="gap-1 pr-1">
                      {o.label}
                      <button onClick={() => removeOverlay(o.id)} className="ml-0.5 rounded-sm hover:bg-[var(--accent-500)]/20"><X className="h-3 w-3" /></button>
                    </Badge>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {indicatorValues.length > 0 && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {indicatorValues.map((iv) => (
                <Card key={iv.id} className="p-3">
                  <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--text-tertiary)]">{iv.label}</p>
                  {iv.type === 'bb' && 'bands' in iv && iv.bands ? (
                    <div className="mt-1 space-y-0.5 text-xs text-[var(--text-primary)]">
                      {(['upper', 'middle', 'lower'] as const).map((k) => (
                        <div key={k} className="flex justify-between"><span className="text-[var(--text-tertiary)] capitalize">{k}</span><span>{fmt(iv.bands![k])}</span></div>
                      ))}
                    </div>
                  ) : iv.type === 'rsi' && 'value' in iv && iv.value != null ? (
                    <p className={`mt-1 text-lg font-semibold ${iv.value > 70 ? 'text-[var(--negative)]' : iv.value < 30 ? 'text-[var(--positive)]' : 'text-[var(--text-primary)]'}`}>{fmt(iv.value)}</p>
                  ) : 'value' in iv && iv.value != null ? (
                    <p className="mt-1 text-lg font-semibold text-[var(--text-primary)]">{fmt(iv.value)}</p>
                  ) : (
                    <p className="mt-1 text-xs text-[var(--text-tertiary)]">N/A</p>
                  )}
                </Card>
              ))}
            </div>
          )}

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2"><Layers className="h-3.5 w-3.5" /> Active Transforms</CardTitle>
                <div className="relative">
                  <Button variant="outline" size="sm" onClick={() => setShowAddMenu((v) => !v)}><Plus className="h-3.5 w-3.5" /> Add Transform</Button>
                  {showAddMenu && (
                    <div className="absolute right-0 top-full z-10 mt-1 w-48 rounded-md border border-[var(--border-default)] bg-[var(--surface-1)] py-1 shadow-lg">
                      {TECHNICAL_INDICATORS.filter((i) => !overlays.some((o) => o.id === i.id)).map((ind) => (
                        <button key={ind.id} onClick={() => { addOverlay(ind); setShowAddMenu(false); }} className="block w-full px-3 py-1.5 text-left text-xs text-[var(--text-secondary)] hover:bg-[var(--surface-3)]">{ind.label}</button>
                      ))}
                      {TECHNICAL_INDICATORS.every((i) => overlays.some((o) => o.id === i.id)) && <p className="px-3 py-1.5 text-xs text-[var(--text-tertiary)]">All added</p>}
                    </div>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {overlays.length === 0 ? (
                <p className="text-xs text-[var(--text-tertiary)]">No active transforms. Add indicators from the sidebar or the button above.</p>
              ) : (
                <div className="space-y-1.5">
                  {overlays.map((o) => (
                    <div key={o.id} className="flex items-center justify-between rounded-md border border-[var(--border-default)] px-3 py-2 text-xs">
                      <div>
                        <span className="font-medium text-[var(--text-primary)]">{o.label}</span>
                        {o.period && <span className="ml-2 text-[var(--text-tertiary)]">period: {o.period}</span>}
                        {o.stddev && <span className="ml-2 text-[var(--text-tertiary)]">stddev: {o.stddev}</span>}
                      </div>
                      <button onClick={() => removeOverlay(o.id)} className="text-[var(--text-tertiary)] hover:text-[var(--negative)]"><X className="h-3.5 w-3.5" /></button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
