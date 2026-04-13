'use client';

import Link from 'next/link';
import { useSession } from 'next-auth/react';
import {
  TrendingUp,
  TrendingDown,
  FileText,
  ExternalLink,
  BarChart3,
  Cpu,
  Globe2,
  PlayCircle,
  Calendar,
  Building2,
  PieChart,
  LineChart,
} from 'lucide-react';
import { MiniChart } from '@/design-system/charts/MiniChart';
import { generateSparkline, INDICES } from '@/mocks/terminal-data';

// ═══ INDEX TICKER DATA ═══
const INDEX_TICKERS = INDICES.map((idx, i) => ({
  ...idx,
  time: '14:32',
  sparkline: generateSparkline(24, idx.value, idx.value * 0.003),
}));

// ═══ RESEARCH ARTICLES ═══
const RESEARCH_ARTICLES = [
  {
    id: 1,
    title: 'Outlook Terbaru Sektor Perbankan Indonesia',
    description:
      'Kami menganalisis tren terbaru pada sektor perbankan Indonesia. Meliputi profitabilitas, kualitas aset, dan proyeksi pertumbuhan kredit untuk bank-bank utama termasuk BBCA, BMRI, BBRI, dan BBNI.',
    icon: Building2,
    color: '#2563eb',
  },
  {
    id: 2,
    title: 'Analisis Transisi Energi & Saham ESG di IDX',
    description:
      'Integritas kredit karbon dan investasi ESG menjadi perhatian pasar. Analisis MSCI ESG Rating terhadap emiten IDX menunjukkan tren perbaikan tata kelola dan komitmen net-zero.',
    icon: Globe2,
    color: '#059669',
  },
  {
    id: 3,
    title: 'Transparansi Data: Laporan Keuangan Emiten',
    description:
      'Transparansi data telah menjadi salah satu tantangan utama dalam hubungan investor di pasar modal Indonesia. Analisis ini mengidentifikasi di mana data masih kurang lengkap.',
    icon: FileText,
    color: '#7c3aed',
  },
  {
    id: 4,
    title: 'Strategi Portofolio untuk Pasar Emerging Market',
    description:
      'Apakah portofolio Anda sudah diposisikan untuk menghadapi dinamika pasar emerging? Kami memperkenalkan framework kuadran untuk menilai kesiapan dan eksposur risiko portofolio.',
    icon: PieChart,
    color: '#dc2626',
  },
];

// ═══ SUPPORT LINKS ═══
const SUPPORT_LINKS = [
  { label: 'Catatan Rilis', href: '/settings' },
  { label: 'Kirim Tiket Dukungan', href: '/settings' },
  { label: 'Lihat Tiket Dukungan', href: '/settings' },
  { label: 'Hubungi Kami', href: '/settings' },
  { label: 'Pusat Bantuan', href: '/settings' },
  { label: 'Status Platform', href: '/settings' },
];

// ═══ DISCOVER LINKS ═══
const DISCOVER_LINKS = [
  { label: 'Dataset', href: '/data/catalog' },
  { label: 'APIs', href: '/data/api' },
  { label: 'Model Kuantitatif', href: '/ml' },
  { label: 'Screener Saham', href: '/studio/screener' },
  { label: 'Strategi Trading', href: '/strategies' },
  { label: 'Data Pasar Real-time', href: '/markets' },
];

// ═══ RECENTLY VISITED ═══
const RECENTLY_VISITED = [
  { type: 'Companies', label: 'BBCA - Bank Central Asia', href: '/markets/BBCA', icon: Building2, time: 'Hari ini' },
  { type: 'Assets', label: 'Saham LQ45', href: '/markets', icon: LineChart, time: 'Hari ini' },
  { type: 'Companies', label: 'Ringkasan Pasar', href: '/markets', icon: BarChart3, time: 'Hari ini' },
];

// ═══ FEATURE CARDS ═══
const FEATURE_CARDS = [
  {
    title: 'Jelajahi Data Pasar IDX',
    description:
      'Akses data indeks dan saham Indonesia secara real-time dengan alat interaktif kami. Request demo hari ini.',
    gradient: 'from-blue-600 to-blue-800',
    buttons: [
      { label: 'Selengkapnya', href: '/markets', variant: 'outline' as const },
      { label: 'Tonton Demo', href: '/markets', variant: 'outline' as const },
    ],
  },
  {
    title: 'Otomatisasi Analisis dengan AI',
    description:
      'Rasakan AI Portfolio Insights dengan data warehousing modern, dashboard intuitif, dan GenAI untuk analisis risiko dan pengambilan keputusan lebih cepat.',
    gradient: 'from-emerald-600 to-emerald-800',
    buttons: [
      { label: 'Baca Riset', href: '/research', variant: 'outline' as const },
      { label: 'Selengkapnya', href: '/research', variant: 'outline' as const },
    ],
  },
  {
    title: 'Analisis Sektor & Fundamental',
    description:
      'Eksplorasi risiko fisik dan fundamental emiten dengan solusi analisis multi-faktor kami, termasuk analisis sektor dan eksposur portofolio.',
    gradient: 'from-violet-600 to-violet-800',
    buttons: [{ label: 'Coba Sekarang', href: '/studio/screener', variant: 'outline' as const }],
  },
];

// ═══ UPCOMING EVENTS ═══
const UPCOMING_EVENTS = [
  { date: '15 Apr 2026', title: 'Webinar: Strategi Investasi IDX Q2 2026' },
  { date: '22 Apr 2026', title: 'Workshop: Backtesting dengan Pyhron' },
];

export default function DashboardPage() {
  const { data: session } = useSession();

  return (
    <div className="min-h-full bg-[#f8fafc]">
      {/* ═══ INDEX TICKER STRIP ═══ */}
      <div className="border-b border-[#e2e8f0] bg-white">
        <div className="flex items-stretch gap-0 overflow-x-auto">
          {INDEX_TICKERS.map((idx, i) => {
            const isPositive = idx.changePct >= 0;
            return (
              <div
                key={idx.symbol}
                className={`flex min-w-[180px] flex-1 items-center gap-3 border-r border-[#e2e8f0] px-4 py-3 last:border-r-0`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-semibold text-[#1e293b] truncate">
                      {idx.symbol}
                    </span>
                    <span className="text-[10px] text-[#94a3b8]">{idx.time}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[13px] font-semibold tabular-nums text-[#0f172a]">
                      {idx.value.toLocaleString('id-ID', { minimumFractionDigits: 2 })}
                    </span>
                    <span
                      className={`flex items-center gap-0.5 text-[11px] font-medium tabular-nums ${
                        isPositive ? 'text-[#16a34a]' : 'text-[#dc2626]'
                      }`}
                    >
                      {isPositive ? (
                        <TrendingUp className="h-3 w-3" />
                      ) : (
                        <TrendingDown className="h-3 w-3" />
                      )}
                      {isPositive ? '+' : ''}
                      {idx.changePct.toFixed(2)}%
                    </span>
                  </div>
                </div>
                <MiniChart
                  data={idx.sparkline}
                  width={80}
                  height={28}
                  positive={isPositive}
                />
              </div>
            );
          })}
        </div>
      </div>

      {/* ═══ MAIN CONTENT ═══ */}
      <div className="flex flex-col lg:flex-row">
        {/* LEFT: Research & Feature Cards */}
        <div className="flex-1 min-w-0">
          {/* Market Research and Insights */}
          <div className="p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-[15px] font-semibold text-[#0f172a]">
                Riset Pasar dan Wawasan
              </h2>
              <Link
                href="/research"
                className="text-[12px] font-medium text-[#2563eb] hover:text-[#1d4ed8] transition-colors"
              >
                Lihat Semua
              </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {RESEARCH_ARTICLES.map((article) => {
                const Icon = article.icon;
                return (
                  <Link
                    key={article.id}
                    href="/research"
                    className="group flex gap-4 rounded-lg border border-[#e2e8f0] bg-white p-4 transition-all hover:shadow-md hover:border-[#cbd5e1]"
                  >
                    <div
                      className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg"
                      style={{ backgroundColor: article.color + '12' }}
                    >
                      <Icon className="h-6 w-6" style={{ color: article.color }} />
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-[13px] font-semibold text-[#0f172a] group-hover:text-[#2563eb] transition-colors line-clamp-1">
                        {article.title}
                      </h3>
                      <p className="mt-1 text-[12px] leading-relaxed text-[#64748b] line-clamp-3">
                        {article.description}
                      </p>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Feature Cards */}
          <div className="px-6 pb-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {FEATURE_CARDS.map((card, i) => (
                <div
                  key={i}
                  className={`relative overflow-hidden rounded-xl bg-gradient-to-br ${card.gradient} p-5 text-white`}
                >
                  <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZGVmcz48cGF0dGVybiBpZD0iZyIgd2lkdGg9IjQwIiBoZWlnaHQ9IjQwIiBwYXR0ZXJuVW5pdHM9InVzZXJTcGFjZU9uVXNlIj48cGF0aCBkPSJNIDQwIDAgTCAwIDAgMCA0MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJyZ2JhKDI1NSwyNTUsMjU1LDAuMDUpIiBzdHJva2Utd2lkdGg9IjEiLz48L3BhdHRlcm4+PC9kZWZzPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9InVybCgjZykiLz48L3N2Zz4=')] opacity-50" />
                  <div className="relative">
                    <h3 className="text-[14px] font-bold">{card.title}</h3>
                    <p className="mt-2 text-[12px] leading-relaxed text-white/80">
                      {card.description}
                    </p>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {card.buttons.map((btn, j) => (
                        <Link
                          key={j}
                          href={btn.href}
                          className="rounded-full border border-white/40 bg-white/10 px-4 py-1.5 text-[11px] font-semibold text-white backdrop-blur-sm transition-all hover:bg-white/20 hover:border-white/60"
                        >
                          {btn.label}
                        </Link>
                      ))}
                    </div>
                  </div>
                </div>
              ))}

              {/* Video Tutorials + Upcoming Events Card */}
              <div className="rounded-xl border border-[#e2e8f0] bg-white p-5 md:col-span-3 lg:col-span-1">
                <div className="mb-4">
                  <h3 className="flex items-center gap-2 text-[14px] font-bold text-[#0f172a]">
                    <PlayCircle className="h-4 w-4 text-[#2563eb]" />
                    Video Tutorial
                  </h3>
                  <p className="mt-1 text-[12px] text-[#64748b]">
                    Pelajari cara menggunakan Pyhron ONE untuk analisis pasar Indonesia.
                  </p>
                </div>
                <div className="border-t border-[#e2e8f0] pt-3">
                  <h4 className="flex items-center gap-2 text-[13px] font-semibold text-[#0f172a]">
                    <Calendar className="h-3.5 w-3.5 text-[#2563eb]" />
                    Acara Mendatang
                  </h4>
                  <div className="mt-2 space-y-2">
                    {UPCOMING_EVENTS.map((event, i) => (
                      <div key={i} className="flex items-start gap-2">
                        <span className="shrink-0 text-[11px] font-medium text-[#2563eb]">
                          {event.date}
                        </span>
                        <span className="text-[11px] text-[#475569] leading-snug">
                          {event.title}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="border-t border-[#e2e8f0] px-6 py-4">
            <p className="text-[10px] text-[#94a3b8] text-center">
              &copy; 2026 Pyhron. Hak Cipta Dilindungi. Tunduk pada{' '}
              <span className="underline cursor-pointer">Syarat Penggunaan</span> &{' '}
              <span className="underline cursor-pointer">Disclaimer</span>.{' '}
              <span className="underline cursor-pointer">Kelola Cookie</span>.
            </p>
          </div>
        </div>

        {/* RIGHT SIDEBAR */}
        <div className="w-full border-l border-[#e2e8f0] bg-white lg:w-[280px] shrink-0">
          <div className="p-5 space-y-6">
            {/* Support */}
            <div>
              <h3 className="text-[12px] font-bold text-[#0f172a] mb-2">Dukungan</h3>
              <div className="space-y-0">
                {SUPPORT_LINKS.map((link) => (
                  <Link
                    key={link.label}
                    href={link.href}
                    className="flex items-center gap-1.5 py-1.5 text-[12px] text-[#2563eb] hover:text-[#1d4ed8] transition-colors"
                  >
                    {link.label}
                    <ExternalLink className="h-2.5 w-2.5 opacity-0 group-hover:opacity-100" />
                  </Link>
                ))}
              </div>
            </div>

            {/* Discover */}
            <div>
              <h3 className="text-[12px] font-bold text-[#0f172a] mb-2">Jelajahi</h3>
              <div className="space-y-0">
                {DISCOVER_LINKS.map((link) => (
                  <Link
                    key={link.label}
                    href={link.href}
                    className="flex items-center gap-1.5 py-1.5 text-[12px] text-[#2563eb] hover:text-[#1d4ed8] transition-colors"
                  >
                    {link.label}
                  </Link>
                ))}
              </div>
            </div>

            {/* Recently Visited */}
            <div>
              <h3 className="text-[12px] font-bold text-[#0f172a] mb-3">
                Terakhir Dikunjungi
              </h3>
              <div className="space-y-3">
                {RECENTLY_VISITED.map((item, i) => {
                  const Icon = item.icon;
                  return (
                    <Link
                      key={i}
                      href={item.href}
                      className="group flex items-start gap-3 rounded-md p-1.5 -mx-1.5 transition-colors hover:bg-[#f1f5f9]"
                    >
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[#f1f5f9] group-hover:bg-[#e2e8f0]">
                        <Icon className="h-4 w-4 text-[#64748b]" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] font-semibold text-[#64748b]">
                            {item.type}
                          </span>
                          <span className="text-[10px] text-[#94a3b8]">{item.time}</span>
                        </div>
                        <p className="text-[12px] text-[#0f172a] truncate">{item.label}</p>
                      </div>
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
