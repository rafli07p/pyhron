import type { Metadata } from 'next';

export const metadata: Metadata = { title: 'Settings' };

export default function SettingsPage() {
  return (
    <div className="max-w-2xl space-y-8">
      <h1 className="text-2xl font-medium text-text-primary">Settings</h1>

      <section className="rounded-lg border border-border bg-bg-secondary p-6 space-y-4">
        <h2 className="text-lg font-medium text-text-primary">Profile</h2>
        <div>
          <label className="block text-sm text-text-secondary mb-1">Full Name</label>
          <input type="text" defaultValue="Demo User" className="w-full rounded-md border border-border bg-bg-primary px-3 py-2 text-sm focus:border-accent-500 focus:outline-none" />
        </div>
        <div>
          <label className="block text-sm text-text-secondary mb-1">Email</label>
          <input type="email" defaultValue="demo@pyhron.com" disabled className="w-full rounded-md border border-border bg-bg-tertiary px-3 py-2 text-sm text-text-muted" />
        </div>
        <button className="rounded-md bg-accent-500 px-4 py-2 text-sm font-medium text-primary-900 hover:bg-accent-600 transition-colors">
          Save Changes
        </button>
      </section>

      <section className="rounded-lg border border-border bg-bg-secondary p-6 space-y-4">
        <h2 className="text-lg font-medium text-text-primary">Notifications</h2>
        <div className="space-y-3">
          {[
            { label: 'Trade execution alerts', defaultChecked: true },
            { label: 'Daily P&L summary', defaultChecked: true },
            { label: 'Strategy signal alerts', defaultChecked: false },
            { label: 'Risk limit warnings', defaultChecked: true },
          ].map((pref) => (
            <label key={pref.label} className="flex items-center gap-3 text-sm text-text-secondary">
              <input type="checkbox" defaultChecked={pref.defaultChecked} className="rounded" />
              {pref.label}
            </label>
          ))}
        </div>
      </section>
    </div>
  );
}
