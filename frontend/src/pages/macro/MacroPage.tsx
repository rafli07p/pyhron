import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { TrendingUp, Calendar, X } from 'lucide-react';
import { macroApi } from '../../api/endpoints';
import type { MacroIndicator, PolicyEvent } from '../../types';
import PageHeader from '../../components/common/PageHeader';
import Badge from '../../components/common/Badge';
import LoadingSpinner from '../../components/common/LoadingSpinner';

const CATEGORIES = ['All', 'Growth', 'Inflation', 'Monetary', 'Trade'] as const;

function categoryForIndicator(code: string): string {
  const lower = code.toLowerCase();
  if (lower.includes('gdp') || lower.includes('growth') || lower.includes('pmi'))
    return 'Growth';
  if (lower.includes('cpi') || lower.includes('inflation') || lower.includes('price'))
    return 'Inflation';
  if (lower.includes('rate') || lower.includes('bi') || lower.includes('m2') || lower.includes('money'))
    return 'Monetary';
  if (lower.includes('trade') || lower.includes('export') || lower.includes('import') || lower.includes('bop') || lower.includes('current'))
    return 'Trade';
  return 'Growth';
}

function formatNumber(val: number): string {
  if (Math.abs(val) >= 1_000_000_000_000) return (val / 1_000_000_000_000).toFixed(1) + 'T';
  if (Math.abs(val) >= 1_000_000_000) return (val / 1_000_000_000).toFixed(1) + 'B';
  if (Math.abs(val) >= 1_000_000) return (val / 1_000_000).toFixed(1) + 'M';
  if (Math.abs(val) >= 1_000) return (val / 1_000).toFixed(1) + 'K';
  return val.toFixed(2);
}

function eventTypeBadgeVariant(type: string): 'info' | 'warning' | 'success' | 'danger' | 'neutral' {
  const lower = type.toLowerCase();
  if (lower.includes('rate') || lower.includes('monetary')) return 'info';
  if (lower.includes('inflation') || lower.includes('cpi')) return 'warning';
  if (lower.includes('gdp') || lower.includes('growth')) return 'success';
  if (lower.includes('trade') || lower.includes('deficit')) return 'danger';
  return 'neutral';
}

export default function MacroPage() {
  const [activeCategory, setActiveCategory] = useState<string>('All');
  const [selectedIndicator, setSelectedIndicator] = useState<string | null>(null);

  const { data: indicators, isLoading: loadingIndicators } = useQuery({
    queryKey: ['macro-indicators'],
    queryFn: () => macroApi.indicators().then((r) => r.data),
  });

  const { data: history, isLoading: loadingHistory } = useQuery({
    queryKey: ['macro-history', selectedIndicator],
    queryFn: () => macroApi.indicatorHistory(selectedIndicator!, { limit: 60 }).then((r) => r.data),
    enabled: !!selectedIndicator,
  });

  const { data: yieldCurve, isLoading: loadingYield } = useQuery({
    queryKey: ['macro-yield-curve'],
    queryFn: () => macroApi.yieldCurve().then((r) => r.data),
  });

  const { data: policyEvents, isLoading: loadingPolicy } = useQuery({
    queryKey: ['macro-policy-events'],
    queryFn: () => macroApi.policyEvents({ limit: 20 }).then((r) => r.data),
  });

  const filteredIndicators = indicators?.filter(
    (ind: MacroIndicator) =>
      activeCategory === 'All' || categoryForIndicator(ind.code) === activeCategory,
  );

  const selectedName = indicators?.find((i: MacroIndicator) => i.code === selectedIndicator)?.name;

  return (
    <div>
      <PageHeader title="Indonesia Macro Dashboard" subtitle="Key economic indicators and policy events">
        <TrendingUp className="h-5 w-5 text-slate-400" />
      </PageHeader>

      {/* Category tabs */}
      <div className="flex items-center gap-1 mb-6 bg-slate-800/50 p-1 rounded-lg w-fit">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeCategory === cat
                ? 'bg-blue-500/20 text-blue-400'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Indicators grid */}
      {loadingIndicators ? (
        <div className="flex justify-center py-16">
          <LoadingSpinner label="Loading indicators..." />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-8">
          {filteredIndicators?.map((ind: MacroIndicator) => (
            <button
              key={ind.code}
              onClick={() =>
                setSelectedIndicator(selectedIndicator === ind.code ? null : ind.code)
              }
              className={`p-4 text-left rounded-lg border transition-colors ${
                selectedIndicator === ind.code
                  ? 'bg-blue-500/10 border-blue-500/40'
                  : 'bg-slate-800/50 border-slate-700 hover:border-slate-600'
              }`}
            >
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">
                {ind.name}
              </p>
              <p className="text-xl font-bold text-slate-100">
                {formatNumber(ind.latest_value)}{' '}
                <span className="text-xs font-normal text-slate-500">{ind.unit}</span>
              </p>
              <p className="text-xs text-slate-500 mt-1">
                {ind.period} &middot; {ind.source}
              </p>
            </button>
          ))}
        </div>
      )}

      {/* Indicator History Chart */}
      {selectedIndicator && (
        <div className="mb-8 p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-slate-100">
              {selectedName} - Historical Data
            </h3>
            <button
              onClick={() => setSelectedIndicator(null)}
              className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-slate-200"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          {loadingHistory ? (
            <div className="flex justify-center py-12">
              <LoadingSpinner size="sm" />
            </div>
          ) : history && history.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={history}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11, fill: '#94a3b8' }}
                  tickFormatter={(d: string) => format(new Date(d), 'MMM yy')}
                />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    fontSize: 12,
                  }}
                  labelFormatter={(d: any) => format(new Date(d), 'MMM yyyy')}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-slate-500 text-center py-8">No history data available.</p>
          )}
        </div>
      )}

      {/* Yield Curve */}
      <div className="mb-8 p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
        <h3 className="text-sm font-semibold text-slate-100 mb-4">Yield Curve</h3>
        {loadingYield ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="sm" />
          </div>
        ) : yieldCurve && yieldCurve.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={yieldCurve}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey="tenor"
                tick={{ fontSize: 11, fill: '#94a3b8' }}
              />
              <YAxis
                tick={{ fontSize: 11, fill: '#94a3b8' }}
                tickFormatter={(v: number) => `${v.toFixed(1)}%`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '8px',
                  fontSize: 12,
                }}
                formatter={(value: any) => [`${Number(value).toFixed(2)}%`, 'Yield']}
              />
              <Line
                type="monotone"
                dataKey="yield_pct"
                stroke="#10b981"
                strokeWidth={2}
                dot={{ r: 4, fill: '#10b981' }}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-slate-500 text-center py-8">No yield curve data.</p>
        )}
      </div>

      {/* Policy Calendar */}
      <div className="p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
        <div className="flex items-center gap-2 mb-4">
          <Calendar className="h-4 w-4 text-blue-400" />
          <h3 className="text-sm font-semibold text-slate-100">Policy Calendar</h3>
        </div>
        {loadingPolicy ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="sm" />
          </div>
        ) : !policyEvents || policyEvents.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-8">No upcoming events.</p>
        ) : (
          <div className="space-y-3">
            {policyEvents.map((event: PolicyEvent, idx: number) => (
              <div
                key={idx}
                className="flex items-start gap-4 p-3 bg-slate-900/50 border border-slate-700/50 rounded-lg"
              >
                <div className="text-center min-w-[52px]">
                  <p className="text-lg font-bold text-slate-100">
                    {format(new Date(event.event_date), 'd')}
                  </p>
                  <p className="text-xs text-slate-500">
                    {format(new Date(event.event_date), 'MMM yy')}
                  </p>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant={eventTypeBadgeVariant(event.event_type)}>
                      {event.event_type}
                    </Badge>
                  </div>
                  <p className="text-sm font-medium text-slate-200 mb-1">{event.title}</p>
                  <p className="text-xs text-slate-400 line-clamp-2">{event.description}</p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                    {event.previous_value != null && (
                      <span>Previous: <span className="text-slate-300">{event.previous_value}</span></span>
                    )}
                    {event.consensus != null && (
                      <span>Consensus: <span className="text-blue-400">{event.consensus}</span></span>
                    )}
                    {event.actual != null && (
                      <span>Actual: <span className="text-emerald-400 font-medium">{event.actual}</span></span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
