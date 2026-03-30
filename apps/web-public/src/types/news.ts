export interface NewsArticle {
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

export interface SentimentSummary {
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

export interface SentimentSummaryResponse {
  summaries: SentimentSummary[];
  total_articles_analyzed: number;
}
