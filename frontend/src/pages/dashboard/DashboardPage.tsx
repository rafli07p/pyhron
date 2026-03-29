import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import {
  BarChart3,
  TrendingUp,
  Activity,
  DollarSign,
  ArrowUpRight,
  ArrowDownRight,
  Filter,
  LineChart,
  Zap,
  ExternalLink,
} from 'lucide-react';

import PageHeader from '../../components/common/PageHeader';
import StatCard from '../../components/common/StatCard';
import Badge from '../../components/common/Badge';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import { marketApi, screenerApi, newsApi } from '../../api/endpoints';
import type { OHLCVBar, ScreenerResult, NewsArticle } from '../../types';

function formatNumber(value: number): string {
  if (value >= 1_000_000_000_000) return (value / 1_000_000_000_000).toFixed(2) + 'T';
  if (value >= 1_000_000_000) return (value / 1_000_000_000).toFixed(2) + 'B';
  if (value >= 1_000_000) return (value / 1_000_000).toFixed(2) + 'M';
  if (value >= 1_000) return (value / 1_000).toFixed(2) + 'K';
  return value.toFixed(2);
}

function formatPrice(value: number): string {
  return value.toLocaleString('id-ID', { maximumFractionDigits: 2 });
}

function sentimentVariant(label: string): 'success' | 'danger' | 'warning' | 'neutral' {
  if (label === 'bullish') return 'success';
  if (label === 'bearish') return 'danger';
  if (label === 'neutral') return 'warning';
  return 'neutral';
}

export default function DashboardPage() {
  const navigate = useNavigate();

  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ['market-overview'],
    queryFn: () => marketApi.overview().then((r) => r.data),
  });

  const { data: ohlcvData, isLoading: chartLoading } = useQuery({
    queryKey: ['ihsg-ohlcv', '1d', 30],
    queryFn: () =>
      marketApi.ohlcv('IHSG', { interval: '1d', limit: 30 }).then((r) => r.data),
  });

  const { data: moversData, isLoading: moversLoading } = useQuery({
    queryKey: ['top-movers'],
    queryFn: () =>
      screenerApi
        .screen({ sort_by: 'change_pct', sort_dir: 'desc', limit: 5 })
        .then((r) => r.data),
  });

  const { data: newsData, isLoading: newsLoading } = useQuery({
    queryKey: ['recent-news'],
    queryFn: () => newsApi.list({ limit: 3 }).then((r) => r.data),
  });

  const chartData = (ohlcvData ?? []).map((bar: OHLCVBar) => ({
    date: new Date(bar.timestamp).toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
    }),
    close: bar.close,
  }));

  const topMovers: ScreenerResult[] = moversData?.results ?? [];
  const news: NewsArticle[] = newsData ?? [];

  if (overviewLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingSpinner label="Loading dashboard..." size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Dashboard" subtitle="Market overview and portfolio summary" />

      {/* Stat Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="IHSG Value"
          value={overview ? formatPrice(overview.last_value) : '--'}
          icon={BarChart3}
        />
        <StatCard
          title="Daily Change"
          value={overview ? `${overview.change >= 0 ? '+' : ''}${overview.change.toFixed(2)}` : '--'}
          change={overview?.change_pct}
          changeLabel="today"
          icon={TrendingUp}
        />
        <StatCard
          title="Total Volume"
          value={overview ? formatNumber(overview.volume) : '--'}
          icon={Activity}
        />
        <StatCard
          title="Value Traded"
          value={overview ? `Rp ${formatNumber(overview.value_traded)}` : '--'}
          icon={DollarSign}
        />
      </div>

      {/* Two-column: Chart + Top Movers */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* IHSG Chart */}
        <div className="lg:col-span-2 rounded-xl border border-slate-700 bg-slate-800 p-5">
          <h3 className="text-base font-semibold text-slate-100 mb-4">
            IHSG Performance (30 Days)
          </h3>
          {chartLoading ? (
            <div className="flex items-center justify-center h-64">
              <LoadingSpinner label="Loading chart..." />
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
                <defs>
                  <linearGradient id="ihsgGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  axisLine={{ stroke: '#475569' }}
                  tickLine={false}
                />
                <YAxis
                  domain={['auto', 'auto']}
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  axisLine={{ stroke: '#475569' }}
                  tickLine={false}
                  tickFormatter={(v: number) => formatPrice(v)}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #475569',
                    borderRadius: '0.5rem',
                    color: '#f1f5f9',
                    fontSize: 13,
                  }}
                  formatter={(value) => [formatPrice(Number(value)), 'Close']}
                />
                <Area
                  type="monotone"
                  dataKey="close"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  fill="url(#ihsgGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Top Movers */}
        <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
          <h3 className="text-base font-semibold text-slate-100 mb-4">Top Movers</h3>
          {moversLoading ? (
            <div className="flex items-center justify-center h-64">
              <LoadingSpinner label="Loading movers..." />
            </div>
          ) : (
            <div className="space-y-3">
              {topMovers.map((stock) => (
                <div
                  key={stock.symbol}
                  onClick={() => navigate(`/stocks/${stock.symbol}`)}
                  className="flex items-center justify-between p-3 rounded-lg bg-slate-900/50 hover:bg-slate-700/50 cursor-pointer transition-colors"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-100 truncate">
                      {stock.symbol}
                    </p>
                    <p className="text-xs text-slate-500 truncate">{stock.name}</p>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    {stock.change_pct >= 0 ? (
                      <ArrowUpRight className="h-4 w-4 text-emerald-400" />
                    ) : (
                      <ArrowDownRight className="h-4 w-4 text-red-400" />
                    )}
                    <span
                      className={`text-sm font-semibold ${
                        stock.change_pct >= 0 ? 'text-emerald-400' : 'text-red-400'
                      }`}
                    >
                      {stock.change_pct >= 0 ? '+' : ''}
                      {stock.change_pct.toFixed(2)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Bottom Row: News + Quick Links */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent News */}
        <div className="lg:col-span-2 rounded-xl border border-slate-700 bg-slate-800 p-5">
          <h3 className="text-base font-semibold text-slate-100 mb-4">Recent News</h3>
          {newsLoading ? (
            <div className="flex items-center justify-center h-40">
              <LoadingSpinner label="Loading news..." />
            </div>
          ) : news.length === 0 ? (
            <p className="text-sm text-slate-500">No recent news available.</p>
          ) : (
            <div className="space-y-4">
              {news.map((article) => (
                <div
                  key={article.id}
                  className="p-4 rounded-lg bg-slate-900/50 border border-slate-700/50"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <a
                        href={article.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm font-semibold text-slate-100 hover:text-blue-400 transition-colors line-clamp-2"
                      >
                        {article.title}
                        <ExternalLink className="inline h-3 w-3 ml-1.5 opacity-50" />
                      </a>
                      <div className="flex items-center gap-3 mt-2">
                        <span className="text-xs text-slate-500">{article.source}</span>
                        <Badge variant={sentimentVariant(article.sentiment_label)}>
                          {article.sentiment_label}
                        </Badge>
                        <span className="text-xs text-slate-600">
                          {formatDistanceToNow(new Date(article.published_at), {
                            addSuffix: true,
                          })}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Quick Links */}
        <div className="rounded-xl border border-slate-700 bg-slate-800 p-5">
          <h3 className="text-base font-semibold text-slate-100 mb-4">Quick Links</h3>
          <div className="space-y-3">
            <button
              onClick={() => navigate('/screener')}
              className="w-full flex items-center gap-3 p-3 rounded-lg bg-slate-900/50 hover:bg-slate-700/50 transition-colors text-left"
            >
              <div className="p-2 rounded-lg bg-blue-500/15">
                <Filter className="h-4 w-4 text-blue-400" />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-100">Screener</p>
                <p className="text-xs text-slate-500">Filter and find stocks</p>
              </div>
            </button>
            <button
              onClick={() => navigate('/trading')}
              className="w-full flex items-center gap-3 p-3 rounded-lg bg-slate-900/50 hover:bg-slate-700/50 transition-colors text-left"
            >
              <div className="p-2 rounded-lg bg-emerald-500/15">
                <LineChart className="h-4 w-4 text-emerald-400" />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-100">Trading</p>
                <p className="text-xs text-slate-500">Execute orders</p>
              </div>
            </button>
            <button
              onClick={() => navigate('/strategies')}
              className="w-full flex items-center gap-3 p-3 rounded-lg bg-slate-900/50 hover:bg-slate-700/50 transition-colors text-left"
            >
              <div className="p-2 rounded-lg bg-amber-500/15">
                <Zap className="h-4 w-4 text-amber-400" />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-100">Strategies</p>
                <p className="text-xs text-slate-500">Manage trading strategies</p>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
