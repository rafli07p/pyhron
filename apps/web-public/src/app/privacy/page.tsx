import type { Metadata } from 'next';

export const metadata: Metadata = { title: 'Privacy Policy' };

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-16 md:py-24">
      <h1 className="font-display text-4xl text-text-primary">Privacy Policy</h1>
      <div className="mt-8 space-y-6 text-text-secondary text-sm leading-relaxed">
        <p>Last updated: March 2026</p>
        <h2 className="text-lg font-medium text-text-primary mt-8">1. Data We Collect</h2>
        <p>We collect account information (name, email), usage data (API calls, features used), and trading data (strategies, backtests, paper trades). We do not collect or store brokerage credentials.</p>
        <h2 className="text-lg font-medium text-text-primary mt-8">2. How We Use Data</h2>
        <p>Account data is used for authentication and service delivery. Usage data helps us improve the platform. Trading data is used to provide analytics and performance tracking. We do not sell personal data.</p>
        <h2 className="text-lg font-medium text-text-primary mt-8">3. Data Security</h2>
        <p>All data is encrypted in transit (TLS) and at rest. Access tokens expire after 1 hour. Passwords are hashed using bcrypt. Infrastructure is hosted in Singapore for low-latency access to IDX.</p>
        <h2 className="text-lg font-medium text-text-primary mt-8">4. Data Retention</h2>
        <p>Account data is retained while the account is active. Trading data is retained for the duration of the subscription. Upon account deletion, personal data is removed within 30 days.</p>
        <h2 className="text-lg font-medium text-text-primary mt-8">5. Contact</h2>
        <p>For privacy-related inquiries, contact privacy@pyhron.com.</p>
      </div>
    </div>
  );
}
