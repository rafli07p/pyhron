export const metadata = { title: 'Privacy Policy' };

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-20">
      <h1 className="text-3xl font-bold text-[var(--text-primary)]">Privacy Policy</h1>
      <p className="mt-2 text-sm text-[var(--text-tertiary)]">Last updated: March 2025</p>
      <div className="mt-8 space-y-4 text-sm leading-relaxed text-[var(--text-secondary)]">
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">Information We Collect</h2>
        <p>We collect information you provide directly: email, name, and usage data. We do not sell personal data to third parties.</p>
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">Data Security</h2>
        <p>We implement industry-standard security measures including encryption at rest and in transit, JWT-based authentication, and regular security audits.</p>
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">Data Retention</h2>
        <p>Account data is retained for the duration of your account. Trading and research data may be retained for regulatory compliance purposes.</p>
      </div>
    </div>
  );
}
