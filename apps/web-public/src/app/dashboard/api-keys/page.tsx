import type { Metadata } from 'next';

export const metadata: Metadata = { title: 'API Keys' };

const mockKeys = [
  { id: 'key-001', name: 'Production', prefix: 'pk_live_...a3f2', created: '2025-12-01', lastUsed: '2026-03-28' },
  { id: 'key-002', name: 'Development', prefix: 'pk_test_...b7e1', created: '2026-01-15', lastUsed: '2026-03-27' },
];

export default function ApiKeysPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-medium text-text-primary">API Keys</h1>
        <button className="rounded-md bg-accent-500 px-4 py-2 text-sm font-medium text-primary-900 hover:bg-accent-600 transition-colors">
          Generate New Key
        </button>
      </div>
      <div className="rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-bg-secondary">
              <th className="px-4 py-3 text-left text-text-muted">Name</th>
              <th className="px-4 py-3 text-left text-text-muted">Key</th>
              <th className="px-4 py-3 text-left text-text-muted">Created</th>
              <th className="px-4 py-3 text-left text-text-muted">Last Used</th>
              <th className="px-4 py-3 text-right text-text-muted">Actions</th>
            </tr>
          </thead>
          <tbody>
            {mockKeys.map((key) => (
              <tr key={key.id} className="border-b border-border last:border-0">
                <td className="px-4 py-3 font-medium text-text-primary">{key.name}</td>
                <td className="px-4 py-3 font-mono text-text-secondary">{key.prefix}</td>
                <td className="px-4 py-3 text-text-secondary">{key.created}</td>
                <td className="px-4 py-3 text-text-secondary">{key.lastUsed}</td>
                <td className="px-4 py-3 text-right">
                  <button className="text-xs text-negative hover:text-negative/80">Revoke</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
