type MessageHandler = (data: WsMessage) => void;

interface WsMessage {
  channel: string;
  type: string;
  data: unknown;
  timestamp: number;
  sequence: number;
}

interface WsConfig {
  maxReconnectAttempts: number;
  baseDelay: number;
  maxDelay: number;
  heartbeatInterval: number;
  heartbeatTimeout: number;
}

const DEFAULT_CONFIG: WsConfig = {
  maxReconnectAttempts: 15,
  baseDelay: 1000,
  maxDelay: 30_000,
  heartbeatInterval: 25_000,
  heartbeatTimeout: 10_000,
};

export class SecureWebSocket {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private pongTimer: ReturnType<typeof setTimeout> | null = null;
  private handlers = new Map<string, Set<MessageHandler>>();
  private lastSequence = new Map<string, number>();
  private state: 'connecting' | 'open' | 'reconnecting' | 'closed' = 'closed';
  private config: WsConfig;

  onStateChange?: (state: typeof this.state) => void;
  onLatency?: (ms: number) => void;

  constructor(config: Partial<WsConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  connect(token: string) {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.state = 'connecting';
    this.onStateChange?.(this.state);

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL!;
    this.ws = new WebSocket(`${wsUrl}/ws`, [`bearer-${token}`]);

    this.ws.onopen = () => {
      this.state = 'open';
      this.reconnectAttempts = 0;
      this.onStateChange?.(this.state);
      this.startHeartbeat();

      for (const channel of this.handlers.keys()) {
        this.send({ type: 'subscribe', channel });
      }
    };

    this.ws.onmessage = (event) => {
      const msg: WsMessage = JSON.parse(event.data);

      if (msg.type === 'pong') {
        if (this.pongTimer) clearTimeout(this.pongTimer);
        this.onLatency?.(Date.now() - msg.timestamp);
        return;
      }

      const lastSeq = this.lastSequence.get(msg.channel) ?? -1;
      if (msg.sequence > lastSeq + 1 && lastSeq >= 0) {
        // Sequence gap detected
      }
      this.lastSequence.set(msg.channel, msg.sequence);

      const channelHandlers = this.handlers.get(msg.channel);
      channelHandlers?.forEach((handler) => handler(msg));
    };

    this.ws.onclose = (event) => {
      this.stopHeartbeat();
      if (event.code === 4001) {
        this.state = 'closed';
        this.onStateChange?.(this.state);
        return;
      }
      this.reconnectWithBackoff(token);
    };

    this.ws.onerror = () => {};
  }

  subscribe(channel: string, handler: MessageHandler) {
    if (!this.handlers.has(channel)) {
      this.handlers.set(channel, new Set());
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send({ type: 'subscribe', channel });
      }
    }
    this.handlers.get(channel)!.add(handler);

    return () => {
      const set = this.handlers.get(channel);
      set?.delete(handler);
      if (set?.size === 0) {
        this.handlers.delete(channel);
        this.send({ type: 'unsubscribe', channel });
      }
    };
  }

  disconnect() {
    this.state = 'closed';
    this.stopHeartbeat();
    this.ws?.close(1000, 'Client disconnect');
    this.ws = null;
    this.handlers.clear();
    this.lastSequence.clear();
    this.onStateChange?.(this.state);
  }

  getState() {
    return this.state;
  }

  private send(data: Record<string, unknown>) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  private reconnectWithBackoff(token: string, minDelay?: number) {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      this.state = 'closed';
      this.onStateChange?.(this.state);
      return;
    }

    this.state = 'reconnecting';
    this.onStateChange?.(this.state);

    const delay = Math.min(
      Math.max(this.config.baseDelay * Math.pow(2, this.reconnectAttempts), minDelay ?? 0),
      this.config.maxDelay,
    ) + Math.random() * 1000;

    this.reconnectAttempts++;
    setTimeout(() => this.connect(token), delay);
  }

  private startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping', timestamp: Date.now() });
        this.pongTimer = setTimeout(() => {
          this.ws?.close(4000, 'Heartbeat timeout');
        }, this.config.heartbeatTimeout);
      }
    }, this.config.heartbeatInterval);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
    if (this.pongTimer) clearTimeout(this.pongTimer);
    this.heartbeatTimer = null;
    this.pongTimer = null;
  }
}
