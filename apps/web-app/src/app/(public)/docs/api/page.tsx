import Link from 'next/link';

export const metadata = { title: 'API Documentation' };

const features = [
  { title: 'REST API Endpoints', desc: 'Market data, indexes, fundamentals, and analytics endpoints with JSON responses and WebSocket streams.' },
  { title: 'Authentication & API Keys', desc: 'OAuth2 and API key authentication with scoped permissions and team-level access controls.' },
  { title: 'Rate Limits & Quotas', desc: 'Tiered rate limits by plan, burst allowances, and real-time usage monitoring via response headers.' },
];

export default function ApiDocsPage() {
  return (
    <div className="bg-white">
      <section className="border-b border-black/[0.06] py-16">
        <div className="mx-auto max-w-6xl px-6">
          <h1 className="text-3xl font-bold text-black">API Documentation</h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-black/50">REST API endpoints, authentication, rate limits, and integration guides for the Pyhron platform.</p>
        </div>
      </section>
      <section className="py-16">
        <div className="mx-auto max-w-6xl px-6">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {features.map((f) => (
              <div key={f.title} className="rounded-xl border border-black/[0.08] p-6">
                <h3 className="text-base font-semibold text-black">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-black/50">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
      <section className="border-t border-black/[0.06] py-16">
        <div className="mx-auto max-w-6xl px-6 text-center">
          <h2 className="text-2xl font-bold text-black">Ready to get started?</h2>
          <p className="mt-2 text-sm text-black/50">Contact our team to learn more.</p>
          <Link href="/contact" className="mt-6 inline-flex h-10 items-center rounded-full bg-[#2563eb] px-8 text-sm font-medium text-white hover:bg-[#1d4ed8]">Get in touch</Link>
        </div>
      </section>
    </div>
  );
}
