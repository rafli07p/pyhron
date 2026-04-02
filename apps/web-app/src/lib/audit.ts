import { api } from './api-client';

interface AuditEvent {
  action: string;
  resource: string;
  resourceId?: string;
  metadata?: Record<string, unknown>;
  timestamp: string;
}

class AuditLogger {
  private queue: AuditEvent[] = [];
  private flushInterval = 10_000;
  private timer: ReturnType<typeof setInterval> | null = null;

  start() {
    if (typeof window !== 'undefined' && !this.timer) {
      this.timer = setInterval(() => this.flush(), this.flushInterval);
      window.addEventListener('beforeunload', () => this.flush());
    }
  }

  log(event: Omit<AuditEvent, 'timestamp'>) {
    this.queue.push({ ...event, timestamp: new Date().toISOString() });
    if (this.queue.length >= 20) this.flush();
  }

  private async flush() {
    if (this.queue.length === 0) return;
    const events = [...this.queue];
    this.queue = [];
    try {
      await api.post('/v1/audit/events', { events });
    } catch {
      if (this.queue.length < 100) {
        this.queue.unshift(...events);
      }
    }
  }
}

export const audit = new AuditLogger();
