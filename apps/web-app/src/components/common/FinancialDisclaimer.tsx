export function FinancialDisclaimer({ className }: { className?: string }) {
  return (
    <div className={className}>
      <p className="text-[10px] leading-relaxed text-[var(--text-tertiary)]">
        Disclaimer: Pyhron is a quantitative research and algorithmic trading platform. All market
        data is provided for informational purposes only and does not constitute investment advice,
        recommendation, or solicitation. Past performance is not indicative of future results.
        Trading in securities involves substantial risk of loss. Pyhron is NOT registered as a
        broker-dealer, investment adviser, or securities intermediary with the Indonesian Financial
        Services Authority (OJK) or the Indonesia Stock Exchange (IDX). Users are solely responsible
        for their trading decisions and compliance with applicable regulations including IDX trading
        rules, Indonesian tax law (UU PPh), and OJK guidelines. This platform operates in paper
        trading mode unless explicitly configured otherwise.
      </p>
    </div>
  );
}
