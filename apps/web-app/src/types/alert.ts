export type AlertCondition =
  | { type: 'price_above'; symbol: string; threshold: number }
  | { type: 'price_below'; symbol: string; threshold: number }
  | { type: 'price_change_pct'; symbol: string; threshold: number; window: '1d' | '1w' | '1m' }
  | { type: 'volume_spike'; symbol: string; multiplier: number }
  | {
      type: 'metric_threshold';
      metricId: string;
      symbol: string;
      operator: 'gt' | 'lt' | 'eq';
      value: number;
    }
  | { type: 'signal_generated'; symbol?: string; direction?: 'buy' | 'sell' }
  | { type: 'drawdown_exceeds'; threshold: number }
  | { type: 'var_exceeds'; threshold: number }
  | { type: 'strategy_error'; strategyId: string }
  | { type: 'order_filled'; orderId?: string }
  | { type: 'kill_switch_triggered' };

export interface Alert {
  id: string;
  name: string;
  condition: AlertCondition;
  channels: ('in_app' | 'email' | 'webhook' | 'telegram')[];
  webhookUrl?: string;
  status: 'active' | 'triggered' | 'paused' | 'expired';
  createdAt: string;
  triggeredAt?: string;
  expiresAt?: string;
  cooldown: number;
}

export interface UserNotification {
  id: string;
  type: 'alert' | 'order' | 'system' | 'signal';
  title: string;
  message: string;
  read: boolean;
  actionUrl?: string;
  createdAt: string;
}
