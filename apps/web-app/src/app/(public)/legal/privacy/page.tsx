export const metadata = { title: 'Privacy Policy' };

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-20">
      <h1 className="text-3xl font-bold text-[var(--text-primary)]">Privacy Policy</h1>
      <p className="mt-2 text-sm text-[var(--text-tertiary)]">Last updated: March 1, 2026</p>
      <p className="mt-4 text-sm text-[var(--text-secondary)]">
        This policy is issued in compliance with Indonesian Law No. 27 of 2022 on Personal Data Protection (UU PDP).
      </p>

      <div className="mt-8 space-y-4 text-sm leading-relaxed text-[var(--text-secondary)]">
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">1. Information We Collect</h2>
        <p>We collect personal data you provide during registration (name, email, phone number), identity verification documents, and financial profile information. We also automatically collect device data, IP addresses, browser type, and usage analytics.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">2. How We Use Your Data</h2>
        <p>Your data is used to provide and improve our services, authenticate your identity, personalize your experience, and comply with legal obligations. We process data based on your explicit consent and our legitimate interests as a service provider.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">3. Data Sharing</h2>
        <p>We do not sell your personal data. We may share data with broker partners you connect, infrastructure providers, and government authorities when required by Indonesian law. All third parties are bound by data processing agreements.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">4. Cross-Border Transfers</h2>
        <p>Some data may be processed on servers outside Indonesia for infrastructure purposes. In such cases, we ensure the receiving jurisdiction provides equivalent data protection as required by UU PDP, and we implement appropriate safeguards including encryption and contractual protections.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">5. Data Retention</h2>
        <p>Account data is retained for the duration of your account and for five years after closure to comply with Indonesian financial record-keeping requirements. Anonymized analytics data may be retained indefinitely.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">6. Your Rights Under UU PDP</h2>
        <p>You have the right to access, correct, delete, and port your personal data. You may withdraw consent at any time and request restriction of processing. To exercise these rights, contact our Data Protection Officer at privacy@pyhron.com.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">7. Cookie Policy</h2>
        <p>We use essential cookies for authentication and session management, and optional analytics cookies to improve the platform. You can manage cookie preferences through your browser settings. Disabling essential cookies may affect platform functionality.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">8. Security</h2>
        <p>We implement industry-standard security measures including AES-256 encryption at rest, TLS 1.3 in transit, multi-factor authentication, and regular penetration testing. Despite these measures, no system is completely secure and we cannot guarantee absolute security.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">9. Changes to This Policy</h2>
        <p>We will notify you of material changes via email or in-app notification at least 14 days before they take effect. Continued use after the effective date constitutes acceptance of the updated policy.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">10. Contact</h2>
        <p>For privacy-related inquiries, contact our Data Protection Officer at privacy@pyhron.com or write to our registered office in Jakarta. We will respond to all requests within 30 days as required by UU PDP.</p>
      </div>
    </div>
  );
}
