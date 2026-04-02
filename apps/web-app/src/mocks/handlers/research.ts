import { http, HttpResponse } from 'msw';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const researchHandlers = [
  // ML signals
  http.get(`${API_BASE}/api/v1/ml/signals`, () => {
    return HttpResponse.json({
      signals: [
        { symbol: 'BBCA', direction: 'long', confidence: 0.87, model: 'gradient_boost_v3', generated_at: '2026-04-02T06:30:00Z', features: ['rsi_divergence', 'volume_breakout', 'earnings_surprise'] },
        { symbol: 'BMRI', direction: 'long', confidence: 0.74, model: 'gradient_boost_v3', generated_at: '2026-04-02T06:30:00Z', features: ['sector_momentum', 'foreign_flow'] },
        { symbol: 'TLKM', direction: 'short', confidence: 0.68, model: 'lstm_seq_v2', generated_at: '2026-04-02T06:30:00Z', features: ['mean_reversion', 'overbought_rsi'] },
        { symbol: 'ADRO', direction: 'long', confidence: 0.81, model: 'gradient_boost_v3', generated_at: '2026-04-02T06:30:00Z', features: ['commodity_correlation', 'volume_spike'] },
        { symbol: 'GOTO', direction: 'short', confidence: 0.62, model: 'lstm_seq_v2', generated_at: '2026-04-02T06:30:00Z', features: ['support_breakdown', 'insider_selling'] },
      ],
      model_version: '3.2.1',
      generated_at: '2026-04-02T06:30:00Z',
    });
  }),

  // Market regime
  http.get(`${API_BASE}/api/v1/ml/regime`, () => {
    return HttpResponse.json({
      regime: 'bullish',
      confidence: 0.72,
      secondary_regime: 'low_volatility',
      secondary_confidence: 0.65,
      indicators: {
        trend_strength: 0.68,
        volatility_percentile: 32,
        breadth_ratio: 0.61,
        foreign_flow_signal: 'positive',
      },
      model: 'hmm_regime_v2',
      as_of: '2026-04-02T06:00:00Z',
    });
  }),

  // ML models
  http.get(`${API_BASE}/api/v1/ml/models`, () => {
    return HttpResponse.json({
      models: [
        {
          id: 'model-001',
          name: 'gradient_boost_v3',
          type: 'gradient_boosting',
          description: 'XGBoost model for daily alpha signal generation',
          features_count: 48,
          training_period: '2020-01-01 to 2025-12-31',
          accuracy: 0.63,
          sharpe_backtest: 1.92,
          status: 'production',
          last_trained: '2026-03-28T04:00:00Z',
        },
        {
          id: 'model-002',
          name: 'lstm_seq_v2',
          type: 'lstm',
          description: 'LSTM sequence model for short-term price direction',
          features_count: 24,
          training_period: '2021-01-01 to 2025-12-31',
          accuracy: 0.58,
          sharpe_backtest: 1.45,
          status: 'production',
          last_trained: '2026-03-25T04:00:00Z',
        },
        {
          id: 'model-003',
          name: 'hmm_regime_v2',
          type: 'hidden_markov',
          description: 'Hidden Markov Model for market regime detection',
          features_count: 12,
          training_period: '2018-01-01 to 2025-12-31',
          accuracy: 0.71,
          sharpe_backtest: null,
          status: 'production',
          last_trained: '2026-03-30T04:00:00Z',
        },
      ],
    });
  }),
];
