import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';
import { Newspaper, Search, BarChart3 } from 'lucide-react';
import { newsApi } from '../../api/endpoints';
import type { NewsArticle, SentimentSummary } from '../../types';
import PageHeader from '../../components/common/PageHeader';
import Badge from '../../components/common/Badge';
import LoadingSpinner from '../../components/common/LoadingSpinner';

function sentimentVariant(label: string): 'success' | 'danger' | 'neutral' {
  if (label === 'bullish') return 'success';
  if (label === 'bearish') return 'danger';
  return 'neutral';
}

function SentimentBar({ value }: { value: number }) {
  // value from -1 to 1, map to 0-100%
  const pct = ((value + 1) / 2) * 100;
  const color =
    value > 0.15 ? 'bg-emerald-500' : value < -0.15 ? 'bg-red-500' : 'bg-slate-500';

  return (
    <div className="w-full h-2 rounded-full bg-slate-700">
      <div
        className={`h-full rounded-full ${color}`}
        style={{ width: `${Math.max(5, pct)}%` }}
      />
    </div>
  );
}

export default function NewsPage() {
  const [symbolFilter, setSymbolFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [sentimentFilter, setSentimentFilter] = useState('');
  const [dateStart, setDateStart] = useState('');
  const [dateEnd, setDateEnd] = useState('');
  const [sentimentSymbols, setSentimentSymbols] = useState('');

  const { data: articles, isLoading } = useQuery({
    queryKey: ['news', symbolFilter, categoryFilter, sentimentFilter, dateStart, dateEnd],
    queryFn: () =>
      newsApi
        .list({
          symbol: symbolFilter || undefined,
          category: categoryFilter || undefined,
          sentiment: sentimentFilter || undefined,
          start: dateStart || undefined,
          end: dateEnd || undefined,
          limit: 50,
        })
        .then((r) => r.data),
  });

  const symbolList = sentimentSymbols
    .split(',')
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean);

  const sentimentQueries = symbolList.map((symbol) => ({
    queryKey: ['sentiment', symbol],
    queryFn: () => newsApi.sentiment(symbol).then((r) => r.data),
    enabled: symbol.length > 0,
  }));

  // Use individual queries for each symbol
  const sentimentResults = sentimentQueries.map((opts) =>
    // eslint-disable-next-line react-hooks/rules-of-hooks
    useQuery(opts),
  );

  return (
    <div>
      <PageHeader title="News & Sentiment" subtitle="Market news with AI sentiment analysis">
        <Newspaper className="h-5 w-5 text-slate-400" />
      </PageHeader>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Symbol (e.g. BBCA)"
            value={symbolFilter}
            onChange={(e) => setSymbolFilter(e.target.value.toUpperCase())}
            className="pl-9 pr-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 w-44"
          />
        </div>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500"
        >
          <option value="">All Categories</option>
          <option value="market">Market</option>
          <option value="corporate">Corporate</option>
          <option value="economy">Economy</option>
          <option value="regulation">Regulation</option>
          <option value="commodities">Commodities</option>
        </select>
        <select
          value={sentimentFilter}
          onChange={(e) => setSentimentFilter(e.target.value)}
          className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500"
        >
          <option value="">All Sentiment</option>
          <option value="bullish">Bullish</option>
          <option value="neutral">Neutral</option>
          <option value="bearish">Bearish</option>
        </select>
        <input
          type="date"
          value={dateStart}
          onChange={(e) => setDateStart(e.target.value)}
          className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500"
        />
        <input
          type="date"
          value={dateEnd}
          onChange={(e) => setDateEnd(e.target.value)}
          className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500"
        />
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: News Articles */}
        <div className="lg:col-span-2 space-y-4">
          {isLoading ? (
            <div className="flex justify-center py-16">
              <LoadingSpinner label="Loading news..." />
            </div>
          ) : !articles || articles.length === 0 ? (
            <div className="text-center py-16 text-slate-500">No articles found.</div>
          ) : (
            articles.map((article: NewsArticle) => (
              <a
                key={article.id}
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block p-4 bg-slate-800/50 border border-slate-700 rounded-lg hover:border-slate-600 transition-colors"
              >
                <div className="flex items-start justify-between gap-3 mb-2">
                  <h3 className="text-sm font-semibold text-slate-100 leading-snug">
                    {article.title}
                  </h3>
                  <Badge variant={sentimentVariant(article.sentiment_label)}>
                    {article.sentiment_label}
                  </Badge>
                </div>
                <p className="text-xs text-slate-400 mb-2">
                  {article.source} &middot;{' '}
                  {formatDistanceToNow(new Date(article.published_at), { addSuffix: true })}
                </p>
                <p className="text-sm text-slate-400 line-clamp-2 mb-3">
                  {article.summary}
                </p>
                {article.symbols.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {article.symbols.map((sym) => (
                      <span
                        key={sym}
                        className="px-2 py-0.5 rounded bg-blue-500/15 text-blue-400 text-xs font-medium border border-blue-500/30"
                      >
                        {sym}
                      </span>
                    ))}
                  </div>
                )}
              </a>
            ))
          )}
        </div>

        {/* Right: Sentiment Summary */}
        <div>
          <div className="p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 className="h-4 w-4 text-blue-400" />
              <h3 className="text-sm font-semibold text-slate-100">Sentiment Summary</h3>
            </div>
            <input
              type="text"
              placeholder="BBCA, BBRI, TLKM"
              value={sentimentSymbols}
              onChange={(e) => setSentimentSymbols(e.target.value.toUpperCase())}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 mb-4"
            />

            {symbolList.length === 0 && (
              <p className="text-xs text-slate-500 text-center py-4">
                Enter comma-separated symbols above
              </p>
            )}

            <div className="space-y-4">
              {symbolList.map((symbol, idx) => {
                const query = sentimentResults[idx];
                if (!query) return null;
                if (query.isLoading) {
                  return (
                    <div key={symbol} className="py-2">
                      <LoadingSpinner size="sm" />
                    </div>
                  );
                }
                const data: SentimentSummary | undefined = query.data;
                if (!data) return null;

                return (
                  <div
                    key={symbol}
                    className="p-3 bg-slate-900/50 border border-slate-700/50 rounded-lg"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold text-slate-100">{symbol}</span>
                      <Badge variant={sentimentVariant(data.sentiment_label)}>
                        {data.sentiment_label}
                      </Badge>
                    </div>
                    <p className="text-xs text-slate-500 mb-2">
                      {data.article_count} articles
                    </p>
                    <SentimentBar value={data.avg_sentiment} />
                    <div className="flex items-center justify-between mt-2 text-xs">
                      <span className="text-emerald-400">
                        {data.bullish_count} bullish
                      </span>
                      <span className="text-slate-400">
                        {data.neutral_count} neutral
                      </span>
                      <span className="text-red-400">
                        {data.bearish_count} bearish
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
