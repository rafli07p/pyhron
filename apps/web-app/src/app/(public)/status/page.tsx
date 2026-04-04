'use client';

import { useState, type FormEvent } from 'react';

const services = [
  { name: 'API Gateway', status: 'Operational', metric: '45ms', color: 'bg-emerald-500' },
  { name: 'WebSocket Feed', status: 'Operational', metric: 'Connected', color: 'bg-emerald-500' },
  { name: 'Market Data', status: 'Operational', metric: '2s ago', color: 'bg-emerald-500' },
  { name: 'Backtesting Engine', status: 'Operational', metric: '0 jobs', color: 'bg-emerald-500' },
  { name: 'ML Pipeline', status: 'Operational', metric: '1h ago', color: 'bg-emerald-500' },
  { name: 'Database', status: 'Operational', metric: '12/100 connections', color: 'bg-emerald-500' },
];

export default function StatusPage() {
  const [email, setEmail] = useState('');
  const [subscribed, setSubscribed] = useState(false);

  function handleSubscribe(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubscribed(true);
  }

  return (
    <div className="py-20">
      <div className="mx-auto max-w-3xl px-6">
        {/* Header */}
        <h1 className="text-3xl font-bold text-[var(--text-primary)]">System Status</h1>
        <div className="mt-4 flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
          <p className="text-sm font-medium text-emerald-400">All systems operational</p>
        </div>

        {/* Services */}
        <div className="mt-10 overflow-hidden rounded-xl border border-[var(--border-default)]">
          {services.map((service, i) => (
            <div
              key={service.name}
              className={`flex items-center justify-between bg-[var(--surface-1)] px-6 py-4 ${
                i < services.length - 1 ? 'border-b border-[var(--border-default)]' : ''
              }`}
            >
              <div className="flex items-center gap-3">
                <span className={`h-2 w-2 rounded-full ${service.color}`} />
                <span className="text-sm font-medium text-[var(--text-primary)]">{service.name}</span>
              </div>
              <div className="flex items-center gap-4">
                <span className="font-mono text-xs text-[var(--text-tertiary)]">{service.metric}</span>
                <span className="text-xs text-[var(--text-secondary)]">{service.status}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Incident History */}
        <div className="mt-16">
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">Incident History</h2>
          <div className="mt-6 rounded-xl border border-[var(--border-default)] bg-[var(--surface-1)] px-6 py-10 text-center">
            <p className="text-sm text-[var(--text-tertiary)]">No recent incidents</p>
          </div>
        </div>

        {/* Subscribe */}
        <div className="mt-16">
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">Subscribe to status updates</h2>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">
            Get notified when there are changes to system status.
          </p>
          {subscribed ? (
            <div className="mt-4 rounded-lg border border-[var(--border-default)] bg-[var(--surface-1)] px-4 py-3">
              <p className="text-sm text-[var(--text-primary)]">Subscribed. You&apos;ll receive status updates at your email.</p>
            </div>
          ) : (
            <form onSubmit={handleSubscribe} className="mt-4 flex gap-3">
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="flex h-9 flex-1 rounded-md border border-white/[0.08] bg-[#0f0f12] px-3 py-1 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-500)]"
              />
              <button
                type="submit"
                className="inline-flex h-9 items-center rounded-md bg-[var(--accent-500)] px-4 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-600)]"
              >
                Subscribe
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
