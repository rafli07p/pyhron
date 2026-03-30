const logos = [
  { initials: 'MF', name: 'Mandiri Invest' },
  { initials: 'BS', name: 'BCA Sekuritas' },
  { initials: 'DS', name: 'Danareksa' },
  { initials: 'TS', name: 'Trimegah' },
  { initials: 'MS', name: 'Mirae Asset' },
  { initials: 'SS', name: 'Sinarmas' },
  { initials: 'CS', name: 'CGS-CIMB' },
  { initials: 'FS', name: 'FundStar' },
];

export function TrustBar() {
  return (
    <section className="border-y border-border bg-bg-secondary py-12">
      <div className="mx-auto max-w-content px-6">
        <p className="text-center text-sm text-text-muted mb-8">
          Trusted by institutional and retail investors across Indonesia
        </p>
        <div className="flex flex-wrap items-center justify-center gap-8 md:gap-12">
          {logos.map((logo) => (
            <div
              key={logo.initials}
              className="flex h-12 w-24 items-center justify-center rounded bg-bg-tertiary text-sm font-medium text-text-muted grayscale transition-all hover:grayscale-0 hover:text-accent-500"
              title={logo.name}
            >
              {logo.initials}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
