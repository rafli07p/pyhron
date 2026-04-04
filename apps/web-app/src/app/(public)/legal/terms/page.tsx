export const metadata = { title: 'Terms of Service' };

export default function TermsPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-20">
      <h1 className="text-3xl font-bold text-[var(--text-primary)]">Terms of Service</h1>
      <p className="mt-2 text-sm text-[var(--text-tertiary)]">Last updated: March 1, 2026</p>

      <div className="mt-8 space-y-4 text-sm leading-relaxed text-[var(--text-secondary)]">
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">1. Acceptance of Terms</h2>
        <p>By accessing or using Pyhron, you agree to be bound by these Terms of Service. If you do not agree to all of these terms, you must not use the platform. Your continued use constitutes acceptance of any future modifications.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">2. Eligibility</h2>
        <p>You must be at least 18 years old and a legal resident of Indonesia or a jurisdiction where use of this platform is not prohibited. By registering, you represent and warrant that you meet these eligibility requirements.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">3. Account Registration</h2>
        <p>You are responsible for maintaining the confidentiality of your account credentials and for all activity under your account. You agree to provide accurate, current, and complete information during registration and to update it as necessary.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">4. Platform Usage</h2>
        <p>Pyhron provides quantitative research tools, backtesting, and algorithmic trading functionality for the Indonesia Stock Exchange (IDX). You agree not to misuse the platform, attempt to reverse-engineer its systems, or use it for any unlawful purpose. Automated scraping or data extraction beyond the provided APIs is prohibited.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">5. Paper Trading</h2>
        <p>Paper trading features simulate market conditions but do not reflect actual execution, slippage, or liquidity constraints. Results from paper trading are hypothetical and should not be relied upon as indicative of real-world performance.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">6. Live Trading</h2>
        <p>Live trading involves real financial risk. Pyhron acts solely as a technology provider and does not execute trades on your behalf. You are fully responsible for all orders placed through broker integrations connected via the platform.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">7. Fees and Billing</h2>
        <p>Certain features require a paid subscription. Fees are billed in advance on a recurring basis. Refunds are handled in accordance with our refund policy. We reserve the right to modify pricing with 30 days&apos; prior notice.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">8. Intellectual Property</h2>
        <p>All content, software, algorithms, and designs on Pyhron are the intellectual property of Pyhron or its licensors. You retain ownership of strategies and research you create, but grant us a limited license to process and store them for service delivery.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">9. Limitation of Liability</h2>
        <p>To the maximum extent permitted by law, Pyhron shall not be liable for any indirect, incidental, or consequential damages arising from your use of the platform. Our total liability shall not exceed the fees you paid in the 12 months preceding the claim.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">10. Termination</h2>
        <p>We may suspend or terminate your account at our discretion if you violate these terms. You may close your account at any time. Upon termination, your right to use the platform ceases immediately, though certain provisions survive termination.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">11. Governing Law</h2>
        <p>These terms are governed by the laws of the Republic of Indonesia. Any disputes shall be resolved through the District Court of South Jakarta, unless otherwise required by applicable Indonesian consumer protection regulations.</p>

        <h2 className="text-lg font-semibold text-[var(--text-primary)]">12. Changes to Terms</h2>
        <p>We reserve the right to update these terms at any time. Material changes will be communicated via email or in-app notification at least 14 days before they take effect. Your continued use after changes constitutes acceptance.</p>
      </div>
    </div>
  );
}
