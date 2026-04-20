'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { ExternalLink, Filter, Minus, RefreshCw, TrendingDown, TrendingUp } from 'lucide-react';

interface NewsArticle {
  id: string;
  title: string;
  source: string;
  url: string;
  published_at: string;
  summary: string | null;
  sentiment_score: number | null;
  sentiment_label: string | null;
  symbols: string[];
  categories: string[];
}

interface SentimentSummary {
  symbol: string;
  article_count: number;
  avg_sentiment: number;
  sentiment_label: string;
  bullish_count: number;
  neutral_count: number;
  bearish_count: number;
  period_start: string;
  period_end: string;
}

interface SentimentSummaryResponse {
  summaries: SentimentSummary[];
  total_articles_analyzed: number;
}

function SentimentBadge({ label, score }: { label: string | null; score: number | null }) {
  if (!label) return <span style={{ color: 'var(--color-text-muted)', fontSize: 11 }}>—</span>;
  const map: Record<string, { bg: string; color: string; Icon: typeof TrendingUp }> = {
    bullish: { bg: '#e3f5ed', color: '#00875A', Icon: TrendingUp },
    bearish: { bg: '#fdecea', color: '#D92D20', Icon: TrendingDown },
    neutral: { bg: '#f3f4f6', color: '#6b7280', Icon: Minus },
  };
  const s = map[label] ?? map.neutral!;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
      background: s.bg, color: s.color,
    }}>
      <s.Icon size={11} />
      {label.charAt(0).toUpperCase() + label.slice(1)}
      {score !== null && ` (${score >= 0 ? '+' : ''}${score.toFixed(2)})`}
    </span>
  );
}

function SentimentBar({ bullish, neutral, bearish, total }: {
  bullish: number; neutral: number; bearish: number; total: number;
}) {
  if (total === 0) return null;
  const bPct = (bullish / total) * 100;
  const nPct = (neutral / total) * 100;
  const rPct = (bearish / total) * 100;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', height: 8, borderRadius: 4, overflow: 'hidden', gap: 1 }}>
        {bPct > 0 && <div style={{ width: `${bPct}%`, background: '#00875A' }} />}
        {nPct > 0 && <div style={{ width: `${nPct}%`, background: '#9ca3af' }} />}
        {rPct > 0 && <div style={{ width: `${rPct}%`, background: '#D92D20' }} />}
      </div>
      <div style={{ display: 'flex', gap: 12, fontSize: 10, color: 'var(--color-text-muted)' }}>
        <span style={{ color: '#00875A' }}>▲ {bullish} Bullish</span>
        <span>● {neutral} Neutral</span>
        <span style={{ color: '#D92D20' }}>▼ {bearish} Bearish</span>
      </div>
    </div>
  );
}

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('id-ID', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

const SYMBOLS = ['BBCA', 'BBRI', 'BMRI', 'TLKM', 'ASII', 'UNVR', 'GOTO'];
const SENTIMENT_FILTERS = ['all', 'bullish', 'neutral', 'bearish'] as const;

export default function ResearchPage() {
  const { data: session } = useSession();
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [sentimentData, setSentimentData] = useState<SentimentSummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [sentimentLoading, setSentimentLoading] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState<string>('');
  const [sentimentFilter, setSentimentFilter] = useState<string>('all');
  const [refreshing, setRefreshing] = useState(false);

  const authHeader = useCallback((): Record<string, string> => {
    const token = (session as { accessToken?: string } | null)?.accessToken;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [session]);

  const fetchNews = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    const params = new URLSearchParams({ limit: '30' });
    if (selectedSymbol) params.set('symbol', selectedSymbol);
    if (sentimentFilter !== 'all') params.set('sentiment', sentimentFilter);
    try {
      const res = await fetch(`/api/v1/news/?${params}`, { headers: authHeader() });
      if (res.ok) setArticles(await res.json());
    } catch {
      /* noop */
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [selectedSymbol, sentimentFilter, authHeader]);

  const fetchSentiment = useCallback(async () => {
    setSentimentLoading(true);
    const params = new URLSearchParams({
      symbols: SYMBOLS.slice(0, 5).join(','),
      // EODHD coverage for .JK tickers is sparse; 180d window surfaces enough articles.
      days: '180',
    });
    try {
      const res = await fetch(`/api/v1/news/sentiment-summary?${params}`, { headers: authHeader() });
      if (res.ok) setSentimentData(await res.json());
    } catch {
      /* noop */
    } finally {
      setSentimentLoading(false);
    }
  }, [authHeader]);

  useEffect(() => {
    if (!session) return;
    void fetchNews();
    void fetchSentiment();
  }, [session, fetchNews, fetchSentiment]);

  return (
    <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 2 }}>
            Market Research & News
          </h1>
          <p style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
            IDX news with NLP sentiment analysis. Source: EODHD Financial Data.
          </p>
        </div>
        <button
          type="button"
          onClick={() => { void fetchNews(true); void fetchSentiment(); }}
          disabled={refreshing}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '6px 14px', borderRadius: 6, fontSize: 12, fontWeight: 600,
            background: 'var(--color-blue-primary)', color: 'white',
            border: 'none', cursor: 'pointer', opacity: refreshing ? 0.7 : 1,
          }}
        >
          <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Sentiment summary cards */}
      {!sentimentLoading && sentimentData && sentimentData.summaries.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <p style={{
            fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
            letterSpacing: '0.08em', color: 'var(--color-text-muted)',
          }}>
            180-Day Sentiment Summary — {sentimentData.total_articles_analyzed} articles analyzed
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8 }}>
            {sentimentData.summaries.map(s => (
              <button
                key={s.symbol}
                type="button"
                onClick={() => setSelectedSymbol(s.symbol === selectedSymbol ? '' : s.symbol)}
                style={{
                  textAlign: 'left',
                  background: '#fff',
                  border: '1px solid',
                  borderColor: s.symbol === selectedSymbol ? 'var(--color-blue-primary)' : 'var(--color-border)',
                  borderRadius: 8, padding: '12px 14px', cursor: 'pointer',
                  boxShadow: s.symbol === selectedSymbol ? '0 0 0 2px rgba(0,87,168,0.15)' : 'none',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span style={{
                    fontSize: 13, fontWeight: 700, color: 'var(--color-blue-primary)',
                    fontFamily: 'monospace',
                  }}>
                    {s.symbol}
                  </span>
                  <SentimentBadge label={s.sentiment_label} score={s.avg_sentiment} />
                </div>
                <SentimentBar
                  bullish={s.bullish_count}
                  neutral={s.neutral_count}
                  bearish={s.bearish_count}
                  total={s.article_count}
                />
                <p style={{ fontSize: 10, color: 'var(--color-text-muted)', marginTop: 6 }}>
                  {s.article_count} articles
                </p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Filter bar */}
      <div style={{
        background: '#fff', border: '1px solid var(--color-border)',
        borderRadius: 8, padding: '10px 14px',
        display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Filter size={13} style={{ color: 'var(--color-text-muted)' }} />
          <span style={{
            fontSize: 11, fontWeight: 600, textTransform: 'uppercase',
            letterSpacing: '0.06em', color: 'var(--color-text-muted)',
          }}>
            Filters
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>Symbol</span>
          <select
            value={selectedSymbol}
            onChange={e => setSelectedSymbol(e.target.value)}
            style={{
              fontSize: 12, padding: '3px 8px', borderRadius: 4,
              border: '1px solid var(--color-border)',
              background: 'var(--color-bg-card)', color: 'var(--color-text-primary)',
            }}
          >
            <option value="">All</option>
            {SYMBOLS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>Sentiment</span>
          <div style={{ display: 'flex', gap: 4 }}>
            {SENTIMENT_FILTERS.map(f => (
              <button
                key={f}
                type="button"
                onClick={() => setSentimentFilter(f)}
                style={{
                  padding: '3px 10px', fontSize: 11, borderRadius: 4,
                  border: '1px solid var(--color-border)',
                  background: sentimentFilter === f ? 'var(--color-blue-primary)' : 'white',
                  color: sentimentFilter === f ? 'white' : 'var(--color-text-secondary)',
                  cursor: 'pointer', fontWeight: sentimentFilter === f ? 600 : 400,
                  textTransform: 'capitalize',
                }}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--color-text-muted)' }}>
          {articles.length} articles
        </span>
      </div>

      {/* News articles */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {loading ? (
          <div style={{
            padding: 60, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13,
            background: '#fff', border: '1px solid var(--color-border)', borderRadius: 8,
          }}>
            Loading news from EODHD…
          </div>
        ) : articles.length === 0 ? (
          <div style={{
            padding: 40, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13,
            background: '#fff', border: '1px solid var(--color-border)', borderRadius: 8,
          }}>
            No articles found for the selected filters.
          </div>
        ) : articles.map(a => (
          <div
            key={a.id}
            style={{
              background: '#fff', border: '1px solid var(--color-border)',
              borderRadius: 8, padding: '14px 16px',
              display: 'flex', flexDirection: 'column', gap: 8,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
              <a
                href={a.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  fontSize: 14, fontWeight: 600, color: 'var(--color-blue-primary)',
                  textDecoration: 'none', lineHeight: 1.4, flex: 1,
                }}
                onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
                onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
              >
                {a.title}
              </a>
              <a
                href={a.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: 'var(--color-text-muted)', flexShrink: 0, marginTop: 2 }}
                aria-label="Open article"
              >
                <ExternalLink size={14} />
              </a>
            </div>

            {a.summary && (
              <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.6, margin: 0 }}>
                {a.summary}…
              </p>
            )}

            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                {a.source}
              </span>
              <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                {fmtDate(a.published_at)}
              </span>
              <SentimentBadge label={a.sentiment_label} score={a.sentiment_score} />
              {a.symbols.length > 0 && (
                <div style={{ display: 'flex', gap: 4 }}>
                  {a.symbols.slice(0, 4).map(sym => (
                    <button
                      key={sym}
                      type="button"
                      onClick={() => setSelectedSymbol(sym === selectedSymbol ? '' : sym)}
                      style={{
                        fontSize: 10, padding: '1px 6px', borderRadius: 3,
                        background: 'rgba(0,87,168,0.08)', color: 'var(--color-blue-primary)',
                        fontWeight: 600, fontFamily: 'monospace',
                        border: 'none', cursor: 'pointer',
                      }}
                    >
                      {sym}
                    </button>
                  ))}
                </div>
              )}
              {a.categories.length > 0 && (
                <div style={{ display: 'flex', gap: 4 }}>
                  {a.categories.slice(0, 2).map(cat => (
                    <span key={cat} style={{
                      fontSize: 10, padding: '1px 6px', borderRadius: 3,
                      background: '#f3f4f6', color: 'var(--color-text-muted)',
                    }}>
                      {cat}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
