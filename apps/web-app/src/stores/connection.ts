import { create } from 'zustand';

interface ConnectionState {
  api: 'online' | 'degraded' | 'offline';
  ws: 'connected' | 'reconnecting' | 'disconnected';
  lastApiSuccess: number | null;
  lastWsMessage: number | null;
  dataAge: Record<string, number>;
  setApiStatus: (status: ConnectionState['api']) => void;
  setWsStatus: (status: ConnectionState['ws']) => void;
  recordApiSuccess: () => void;
  recordWsMessage: () => void;
  recordDataUpdate: (key: string) => void;
}

export const useConnectionStore = create<ConnectionState>((set) => ({
  api: 'online',
  ws: 'disconnected',
  lastApiSuccess: null,
  lastWsMessage: null,
  dataAge: {},
  setApiStatus: (api) => set({ api }),
  setWsStatus: (ws) => set({ ws }),
  recordApiSuccess: () => set({ lastApiSuccess: Date.now(), api: 'online' }),
  recordWsMessage: () => set({ lastWsMessage: Date.now() }),
  recordDataUpdate: (key) =>
    set((s) => ({ dataAge: { ...s.dataAge, [key]: Date.now() } })),
}));
