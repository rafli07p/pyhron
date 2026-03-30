import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Careers',
  description: 'Join the Pyhron team. Open positions in engineering, research, and product.',
};

const positions = [
  { title: 'Senior Quantitative Researcher', team: 'Research', location: 'Jakarta / Remote', type: 'Full-time' },
  { title: 'Full-Stack Engineer (Next.js/Python)', team: 'Engineering', location: 'Jakarta / Remote', type: 'Full-time' },
  { title: 'Data Engineer', team: 'Engineering', location: 'Jakarta', type: 'Full-time' },
  { title: 'Product Designer', team: 'Product', location: 'Jakarta / Remote', type: 'Full-time' },
  { title: 'DevOps Engineer', team: 'Engineering', location: 'Jakarta / Remote', type: 'Full-time' },
];

export default function CareersPage() {
  return (
    <div className="mx-auto max-w-content px-6 py-16 md:py-24">
      <h1 className="font-display text-4xl text-text-primary md:text-5xl">Careers</h1>
      <p className="mt-4 max-w-2xl text-text-secondary">
        We are building quantitative analytics infrastructure for Indonesian capital markets. Join us if you want to work at the intersection of finance, data, and technology.
      </p>

      <section className="mt-12">
        <h2 className="text-xl font-medium text-text-primary">Open Positions</h2>
        <div className="mt-6 space-y-3">
          {positions.map((pos) => (
            <div
              key={pos.title}
              className="flex flex-col gap-2 rounded-lg border border-border bg-bg-secondary p-4 sm:flex-row sm:items-center sm:justify-between"
            >
              <div>
                <h3 className="font-medium text-text-primary">{pos.title}</h3>
                <p className="text-sm text-text-secondary">{pos.team} &middot; {pos.location}</p>
              </div>
              <div className="flex items-center gap-3">
                <span className="rounded bg-bg-tertiary px-2 py-0.5 text-xs text-text-muted">{pos.type}</span>
                <a href="mailto:careers@pyhron.com" className="text-sm font-medium text-accent-500 hover:text-accent-600">
                  Apply
                </a>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-16">
        <h2 className="text-xl font-medium text-text-primary">Why Pyhron</h2>
        <div className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {[
            { title: 'Hard Problems', desc: 'Factor modeling, real-time systems, and market microstructure for Indonesian equities.' },
            { title: 'Small Team', desc: 'Direct impact on product and architecture decisions. No bureaucracy.' },
            { title: 'Remote-Friendly', desc: 'Work from anywhere in Indonesia. Jakarta office available.' },
          ].map((item) => (
            <div key={item.title} className="rounded-lg border border-border p-5">
              <h3 className="font-medium text-text-primary">{item.title}</h3>
              <p className="mt-2 text-sm text-text-secondary">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
