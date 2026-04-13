'use client';

import Link from 'next/link';
import {
  TrendingUp,
  TrendingDown,
  Building2,
  LineChart,
  Leaf,
  FileText,
  PieChart,
} from 'lucide-react';
import { MiniChart } from '@/design-system/charts/MiniChart';
import { generateSparkline, INDICES } from '@/mocks/terminal-data';

/* ═══ INDEX DATA ═══ */
const INDEX_TICKERS = INDICES.map((idx) => ({
  ...idx,
  time: '14:32',
  sparkline: generateSparkline(24, idx.value, idx.value * 0.003),
}));

/* ═══ RESEARCH ARTICLES ═══ */
const RESEARCH_ARTICLES = [
  {
    id: 1,
    title: 'Latest on Indonesian Commercial-Property Pricing',
    description:
      'We report the latest trends in the commercial property price index for Indonesia. We cover the all-property index and indexes for the major property types including industrial, retail, apartment and office.',
    icon: Building2,
    color: '#2563eb',
  },
  {
    id: 2,
    title: 'Carbon-Credit Integrity in the Indonesian Market',
    description:
      'Integrity matters in compliance markets. Our analysis of Indonesian carbon credit projects reveals pricing premiums, project-level risk variation and how methodology design shapes outcomes.',
    icon: Leaf,
    color: '#059669',
  },
  {
    id: 3,
    title: 'The Transparency Gap: Issuer Data Rooms',
    description:
      'Transparency has become one of the defining challenges in the relationship between investors and issuers in capital markets. This analysis identifies where the data falls short during due diligence.',
    icon: FileText,
    color: '#7c3aed',
  },
  {
    id: 4,
    title: 'Positioning Portfolios for the Energy Transition',
    description:
      'Do funds perform better positioned for the energy transition outperform? We introduce a forward-looking quadrant framework to assess transition risk and readiness — and their portfolio implications.',
    icon: PieChart,
    color: '#dc2626',
  },
];

/* ═══ SUPPORT LINKS ═══ */
const SUPPORT_LINKS = [
  'Release Notes',
  'Submit a Support Ticket',
  'View Support Tickets',
  'Contact Us',
  'Support Site',
  'Platform Status',
];

/* ═══ DISCOVER LINKS ═══ */
const DISCOVER_LINKS = [
  { label: 'Datasets', href: '/data/catalog' },
  { label: 'APIs', href: '/data/api' },
  { label: 'Models', href: '/ml' },
  { label: 'Stock Screener', href: '/studio/screener' },
  { label: 'Total Plan', href: '/strategies' },
  { label: 'Capital Market Analytics', href: '/markets' },
];

/* ═══ RECENTLY VISITED ═══ */
const RECENTLY_VISITED = [
  { category: 'Companies', label: 'Index Composition Viewer', href: '/markets', icon: Building2 },
  { category: 'Assets', label: 'Equities', href: '/markets', icon: LineChart },
  { category: 'Companies', label: 'Overview', href: '/markets', icon: Building2 },
];

/* ═══ FEATURE CARDS ═══ */
const FEATURE_CARDS = [
  {
    title: 'Explore Market Insights',
    description:
      'Bring your index data to life with our latest interactive tool. Request a demo today.',
    gradient: 'from-blue-500 to-indigo-700',
    buttons: ['Learn More', 'Watch Demo Video'],
  },
  {
    title: 'Automate Insights to Drive Decisions',
    description:
      'Experience AI Portfolio Insights with modern data warehousing, intuitive dashboards, and GenAI to speed up risk analysis and empower better decisions.',
    gradient: 'from-emerald-500 to-teal-700',
    buttons: ['Read Research', 'Learn More'],
  },
  {
    title: 'GeoSpatial Asset Intelligence',
    description:
      'Explore physical and nature risks with our multi-award-winning solution, including PRI Award 2025 for Recognition for Action — Climate Award.',
    gradient: 'from-sky-500 to-cyan-700',
    buttons: ['Book a Demo'],
  },
];

export default function DashboardPage() {
  return (
    <div className="min-h-full bg-[#f8fafc]">
      {/* ═══ INDEX TICKER STRIP ═══ */}
      <div className="border-b border-[#e2e8f0] bg-white">
        <div className="flex items-stretch overflow-x-auto">
          {INDEX_TICKERS.map((idx) => {
            const positive = idx.changePct >= 0;
            return (
              <div
                key={idx.symbol}
                className="flex min-w-[180px] flex-1 items-center gap-3 border-r border-[#e2e8f0] px-4 py-3 last:border-r-0"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-[11px] font-bold uppercase text-[#1e293b]">
                      {idx.name}
                    </span>
                    <span className="text-[10px] text-[#94a3b8]">{idx.time}</span>
                  </div>
                  <div className="mt-0.5 flex items-center gap-2">
                    <span className="text-[13px] font-semibold tabular-nums text-[#0f172a]">
                      {idx.value.toLocaleString('id-ID', { minimumFractionDigits: 2 })}
                    </span>
                    <span
                      className={`flex items-center gap-0.5 text-[11px] font-medium tabular-nums ${
                        positive ? 'text-[#16a34a]' : 'text-[#dc2626]'
                      }`}
                    >
                      {positive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                      {positive ? '+' : ''}{idx.changePct.toFixed(2)}%
                    </span>
                  </div>
                </div>
                <MiniChart data={idx.sparkline} width={80} height={28} positive={positive} />
              </div>
            );
          })}
        </div>
      </div>

      {/* ═══ MAIN CONTENT ═══ */}
      <div className="flex flex-col lg:flex-row">

        {/* LEFT: Research & Feature Cards */}
        <div className="min-w-0 flex-1">

          {/* Market Research and Insights */}
          <div className="p-6">
            <div className="rounded-lg border border-[#e2e8f0] bg-white">
              <div className="flex items-center justify-between border-b border-[#e2e8f0] px-5 py-3">
                <h2 className="text-[14px] font-semibold text-[#0f172a]">Market Research and Insights</h2>
                <Link href="/research" className="text-[12px] font-medium text-[#2563eb] hover:text-[#1d4ed8]">
                  View All
                </Link>
              </div>
              <div className="grid grid-cols-1 gap-0 md:grid-cols-2">
                {RESEARCH_ARTICLES.map((article, i) => {
                  const Icon = article.icon;
                  const borderR = i % 2 === 0 ? 'md:border-r' : '';
                  const borderB = i < 2 ? 'border-b' : '';
                  return (
                    <Link
                      key={article.id}
                      href="/research"
                      className={`group flex gap-4 p-5 ${borderR} ${borderB} border-[#e2e8f0] transition-colors hover:bg-[#f8fafc]`}
                    >
                      <div
                        className="flex h-[60px] w-[80px] shrink-0 items-center justify-center rounded"
                        style={{ backgroundColor: article.color + '14' }}
                      >
                        <Icon className="h-7 w-7" style={{ color: article.color }} />
                      </div>
                      <div className="min-w-0">
                        <h3 className="text-[13px] font-bold text-[#2563eb] group-hover:underline">
                          {article.title}
                        </h3>
                        <p className="mt-1 text-[11px] leading-relaxed text-[#64748b] line-clamp-3">
                          {article.description}
                        </p>
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Feature Cards */}
          <div className="grid grid-cols-1 gap-4 px-6 pb-6 md:grid-cols-4">
            {FEATURE_CARDS.map((card, i) => (
              <div
                key={i}
                className={`overflow-hidden rounded-lg bg-gradient-to-br ${card.gradient} text-white`}
              >
                {/* Image placeholder area */}
                <div className="relative h-[120px] overflow-hidden">
                  <div className="absolute inset-0 bg-white/5" />
                  <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-black/40 to-transparent" />
                </div>
                {/* Content */}
                <div className="p-4">
                  <h3 className="text-[13px] font-bold">{card.title}</h3>
                  <p className="mt-1.5 text-[11px] leading-relaxed text-white/80">{card.description}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {card.buttons.map((btn, j) => (
                      <Link
                        key={j}
                        href="/markets"
                        className="rounded border border-white/50 px-3 py-1 text-[10px] font-semibold text-white transition-colors hover:bg-white/20"
                      >
                        {btn}
                      </Link>
                    ))}
                  </div>
                </div>
              </div>
            ))}

            {/* Video Tutorials & Upcoming Events */}
            <div className="rounded-lg border border-[#e2e8f0] bg-white p-4">
              <h3 className="text-[13px] font-bold text-[#0f172a]">Video Tutorials</h3>
              <p className="mt-1 text-[11px] text-[#64748b]">
                Learn more about the new Pyhron ONE experience.
              </p>
              <div className="mt-4 border-t border-[#e2e8f0] pt-3">
                <h4 className="text-[12px] font-bold text-[#0f172a]">Upcoming Events</h4>
                <div className="mt-2 space-y-2">
                  <div>
                    <p className="text-[11px] font-medium text-[#2563eb]">Apr 15, 2026 - Virtual Event</p>
                    <p className="text-[11px] text-[#475569]">Infrastructure and Data Centers, Performance Trends</p>
                  </div>
                  <div>
                    <p className="text-[11px] font-medium text-[#2563eb]">Apr 22, 2026 - Webinar</p>
                    <p className="text-[11px] text-[#475569]">IDX Investment Strategy Q2 2026</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="border-t border-[#e2e8f0] px-6 py-4">
            <p className="text-center text-[10px] text-[#94a3b8]">
              &copy; 2026 Pyhron Inc. All Rights Reserved. Subject to{' '}
              <span className="cursor-pointer underline">Terms of Use</span> &amp;{' '}
              <span className="cursor-pointer underline">Disclaimer</span>.{' '}
              <span className="cursor-pointer underline">Manage Cookies</span>.
            </p>
          </div>
        </div>

        {/* RIGHT SIDEBAR */}
        <div className="w-full shrink-0 border-l border-[#e2e8f0] bg-white lg:w-[260px]">
          <div className="space-y-5 p-5">

            {/* Support */}
            <div>
              <h3 className="mb-1.5 text-[12px] font-bold text-[#0f172a]">Support</h3>
              {SUPPORT_LINKS.map((label) => (
                <Link key={label} href="/settings" className="block py-[3px] text-[12px] text-[#2563eb] hover:underline">
                  {label}
                </Link>
              ))}
            </div>

            {/* Discover */}
            <div>
              <h3 className="mb-1.5 text-[12px] font-bold text-[#0f172a]">Discover</h3>
              {DISCOVER_LINKS.map((l) => (
                <Link key={l.label} href={l.href} className="block py-[3px] text-[12px] text-[#2563eb] hover:underline">
                  {l.label}
                </Link>
              ))}
            </div>

            {/* Recently Visited */}
            <div>
              <h3 className="mb-2 text-[12px] font-bold text-[#0f172a]">Recently Visited</h3>
              <div className="space-y-3">
                {RECENTLY_VISITED.map((item, i) => {
                  const Icon = item.icon;
                  return (
                    <Link
                      key={i}
                      href={item.href}
                      className="group -mx-1 flex items-center gap-2.5 rounded p-1 transition-colors hover:bg-[#f1f5f9]"
                    >
                      <Icon className="h-4 w-4 shrink-0 text-[#94a3b8]" />
                      <div className="min-w-0 flex-1">
                        <span className="text-[11px] text-[#64748b]">
                          {item.category}{' '}
                          <span className="mx-0.5 text-[#cbd5e1]">&bull;</span>{' '}
                          <span className="text-[#0f172a]">{item.label}</span>
                        </span>
                      </div>
                      <span className="text-[10px] text-[#94a3b8]">Today</span>
                    </Link>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
