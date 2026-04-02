import { FinancialDisclaimer } from '@/components/common/FinancialDisclaimer';

export const metadata = { title: 'Investment Disclaimer' };

export default function DisclaimerPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-20">
      <h1 className="text-3xl font-bold text-[var(--text-primary)]">Investment Disclaimer</h1>
      <div className="mt-8 space-y-4 text-sm leading-relaxed text-[var(--text-secondary)]">
        <FinancialDisclaimer />
        <h2 className="mt-8 text-lg font-semibold text-[var(--text-primary)]">Additional Disclosures</h2>
        <p>All algorithmic trading strategies presented on this platform are for educational and research purposes. No guarantee of profit or avoidance of loss is implied.</p>
        <p>IDX market data is sourced from third-party providers and may be delayed. Real-time data availability depends on your subscription tier and data provider agreements.</p>
        <p>Users must comply with all applicable Indonesian regulations including but not limited to: IDX trading rules, OJK regulations, and Indonesian tax law (UU PPh) regarding capital gains and dividend taxation.</p>
      </div>
    </div>
  );
}
