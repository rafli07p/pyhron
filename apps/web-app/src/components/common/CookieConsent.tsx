'use client';

import { useState, useSyncExternalStore } from 'react';

const CONSENT_KEY = 'pyhron_consent';

function getConsent(): 'all' | 'essential' | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(CONSENT_KEY) as 'all' | 'essential' | null;
}

function subscribeConsent(cb: () => void) {
  window.addEventListener('storage', cb);
  return () => window.removeEventListener('storage', cb);
}

function getConsentSnapshot() {
  return getConsent();
}

function getConsentServer() {
  return null;
}

export function useCookieConsent() {
  return useSyncExternalStore(subscribeConsent, getConsentSnapshot, getConsentServer);
}

export function CookieConsent() {
  const consent = useCookieConsent();
  const [dismissed, setDismissed] = useState(false);

  if (dismissed || consent !== null) return null;

  function accept(level: 'all' | 'essential') {
    localStorage.setItem(CONSENT_KEY, level);
    setDismissed(true);
    window.dispatchEvent(new Event('storage'));
  }

  return (
    <div className="fixed inset-x-0 bottom-0 z-[60] border-t border-[var(--border-default)] bg-[var(--surface-2)] p-4 shadow-lg">
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-4 sm:flex-row">
        <p className="flex-1 text-xs text-[var(--text-secondary)]">
          Kami menggunakan cookie untuk meningkatkan pengalaman Anda.{' '}
          <a href="/legal/privacy" className="underline hover:text-[var(--text-primary)]">
            Lihat kebijakan privasi kami
          </a>
          .
        </p>
        <div className="flex gap-2">
          <button
            onClick={() => accept('essential')}
            className="rounded border border-[var(--border-default)] px-4 py-2 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-3)]"
          >
            Hanya yang Diperlukan
          </button>
          <button
            onClick={() => accept('all')}
            className="rounded bg-[var(--accent-500)] px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-[var(--accent-600)]"
          >
            Terima Semua
          </button>
        </div>
      </div>
    </div>
  );
}
