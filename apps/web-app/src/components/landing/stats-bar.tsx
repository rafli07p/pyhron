export function StatsBar() {
  const stats = [
    { value: 'IDR 2.4T+', label: 'Assets Analyzed' },
    { value: 'LQ45', label: '100% Coverage' },
    { value: '18', label: 'Alpha Factors' },
    { value: '<50ms', label: 'Execution Latency' },
  ];

  return (
    <section className="bg-[#0A1628] py-16">
      <div className="mx-auto grid max-w-6xl grid-cols-2 gap-8 px-6 md:grid-cols-4">
        {stats.map((stat) => (
          <div key={stat.label} className="text-center">
            <p className="font-mono text-3xl font-normal tabular-nums text-[#C9A84C] lg:text-4xl">
              {stat.value}
            </p>
            <p className="mt-2 text-xs font-medium uppercase tracking-wider text-white/60">
              {stat.label}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
