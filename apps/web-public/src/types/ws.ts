// Client -> Server
export interface WsAuth { type: 'AUTH'; token: string }
export interface WsSubscribe { type: 'SUBSCRIBE'; channel: string; key: string }
export interface WsUnsubscribe { type: 'UNSUBSCRIBE'; channel: string; key: string }
export interface WsPong { type: 'PONG'; timestamp: string }
export type WsClientMessage = WsAuth | WsSubscribe | WsUnsubscribe | WsPong;

// Server -> Client
export interface WsAuthOk { type: 'AUTH_OK'; user_id: string; username: string; role: string; server_time: string }
export interface WsAuthFail { type: 'AUTH_FAIL'; reason: string }
export interface WsSubscribed { type: 'SUBSCRIBED'; channel: string; key: string }
export interface WsHeartbeat { type: 'HEARTBEAT'; server_time: string; connection_id: string }
export interface WsError { type: 'ERROR'; code: string; message: string }

export interface WsQuoteUpdate {
  type: 'QUOTE_UPDATE';
  symbol: string; timestamp: string;
  open: string; high: string; low: string; close: string;
  volume: string; value_idr: string;
  change: string; change_pct: string; prev_close: string;
  bid: string; ask: string; bid_volume: string; ask_volume: string;
}

export interface WsOrderUpdate {
  type: 'ORDER_UPDATE';
  order_id: string; client_order_id: string; symbol: string;
  side: string; order_type: string; status: string;
  quantity_lots: number; filled_quantity_lots: number;
  limit_price: string; avg_fill_price: string; commission_idr: string;
  submitted_at: string; filled_at: string; updated_at: string;
}

export interface WsPositionUpdate {
  type: 'POSITION_UPDATE';
  symbol: string; quantity_lots: number;
  avg_cost_idr: string; last_price: string;
  unrealized_pnl_idr: string; unrealized_pnl_pct: string;
  realized_pnl_idr: string; updated_at: string;
}

export interface WsSignalUpdate {
  type: 'SIGNAL_UPDATE';
  strategy_id: string; symbol: string; signal_type: string;
  alpha_score: string; target_weight: string; target_lots: number;
  rank: number; universe_size: number; generated_at: string;
}

export interface WsMarketStatus {
  type: 'MARKET_STATUS';
  status: string; session: string;
  next_event: string; next_event_at: string;
  ihsg_last: string; ihsg_change_pct: string; server_time: string;
}

export type WsServerMessage =
  | WsAuthOk | WsAuthFail | WsSubscribed | WsHeartbeat | WsError
  | WsQuoteUpdate | WsOrderUpdate | WsPositionUpdate | WsSignalUpdate | WsMarketStatus;
