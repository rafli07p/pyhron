'use client';

import { useCompanyStore } from '@/stores/company';

export default function OwnershipPage() {
  const { selectedSymbol } = useCompanyStore();
  return (
    <div style={{ padding: '20px 24px' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 8 }}>
        Ownership Structure
      </h1>
      <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 20 }}>
        {selectedSymbol} — Institutional, insider, and public ownership breakdown.
      </p>
      <div style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 8, padding: '40px 24px', textAlign: 'center' }}>
        <p style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>
          Ownership data requires ingestion pipeline. Available in next release.
        </p>
      </div>
    </div>
  );
}
