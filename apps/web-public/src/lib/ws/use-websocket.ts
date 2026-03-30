'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import type { WsServerMessage } from '@/types/ws';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';
const RECONNECT_DELAY = 3000;

export function usePyhronWebSocket(
  channels: { channel: string; key: string }[],
  onMessage: (msg: WsServerMessage) => void,
) {
  const { data: session } = useSession();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const connect = useCallback(() => {
    if (!session?.accessToken) return;
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'AUTH', token: session.accessToken }));
    };

    ws.onmessage = (event) => {
      const msg: WsServerMessage = JSON.parse(event.data);
      if (msg.type === 'AUTH_OK') {
        channels.forEach(({ channel, key }) => {
          ws.send(JSON.stringify({ type: 'SUBSCRIBE', channel, key }));
        });
      } else if (msg.type === 'HEARTBEAT') {
        ws.send(JSON.stringify({ type: 'PONG', timestamp: new Date().toISOString() }));
      } else {
        onMessage(msg);
      }
    };

    ws.onclose = () => {
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY);
    };
  }, [session?.accessToken, channels, onMessage]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return wsRef;
}
