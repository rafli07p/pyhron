export interface WsMessage {
  channel: string;
  type: string;
  data: unknown;
  timestamp: number;
  sequence: number;
}

export interface Quote {
  symbol: string;
  bid: number;
  ask: number;
  last: number;
  volume: number;
  change: number;
  changePercent: number;
  high: number;
  low: number;
}

export interface OrderStatusUpdate {
  orderId: string;
  status: string;
  filledQuantity: number;
  avgFillPrice: number | null;
  commission: number;
  tax: number;
  updatedAt: string;
}

export interface SystemAlert {
  severity: 'info' | 'warning' | 'critical';
  title: string;
  message: string;
  action?: { label: string; url: string };
  dismissible: boolean;
}

export interface UserNotification {
  id: string;
  title: string;
  message: string;
  type: 'order' | 'signal' | 'strategy' | 'system';
  read: boolean;
  createdAt: string;
}
