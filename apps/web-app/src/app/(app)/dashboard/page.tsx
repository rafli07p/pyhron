'use client';

import Link from 'next/link';
import {
  TrendingUp,
  TrendingDown,
  Building2,
  BarChart3,
  LineChart,
  Leaf,
  FileText,
  PieChart,
} from 'lucide-react';
import { MiniChart } from '@/design-system/charts/MiniChart';
import { generateSparkline, INDICES } from '@/mocks/terminal-data';

/* ═══ DATA INDEKS ═══ */
const INDEKS = INDICES.map((idx) => ({
  ...idx,
  time: '14:32',
  sparkline: generateSparkline(24, idx.value, idx.value * 0.003),
}));

/* ═══ ARTIKEL RISET ═══ */
const ARTIKEL_RISET = [
  {
    id: 1,
    judul: 'Terbaru: Harga Properti Komersial Indonesia',
    deskripsi:
      'Kami melaporkan tren terbaru indeks harga properti komersial untuk Indonesia. Mencakup indeks keseluruhan dan indeks untuk jenis properti utama termasuk industri, ritel, apartemen, dan perkantoran.',
    ikon: Building2,
    warna: '#2563eb',
  },
  {
    id: 2,
    judul: 'Integritas Kredit Karbon di Pasar Indonesia',
    deskripsi:
      'Integritas sangat penting dalam kepatuhan pasar karbon. Analisis proyek kredit karbon Indonesia mengungkapkan premi harga, variasi risiko tingkat proyek, dan bagaimana desain metodologi membentuk hasil.',
    ikon: Leaf,
    warna: '#059669',
  },
  {
    id: 3,
    judul: 'Kesenjangan Transparansi: Ruang Data Emiten',
    deskripsi:
      'Transparansi telah menjadi salah satu tantangan utama dalam hubungan antara investor dan emiten di pasar modal. Analisis ini mengidentifikasi di mana data masih kurang lengkap selama due diligence.',
    ikon: FileText,
    warna: '#7c3aed',
  },
  {
    id: 4,
    judul: 'Memposisikan Portofolio untuk Transisi Energi',
    deskripsi:
      'Apakah portofolio Anda sudah diposisikan lebih baik untuk menghadapi transisi energi? Kami memperkenalkan framework kuadran untuk menilai kesiapan dan risiko transisi portofolio.',
    ikon: PieChart,
    warna: '#dc2626',
  },
];

/* ═══ LINK DUKUNGAN ═══ */
const LINK_DUKUNGAN = [
  'Catatan Rilis',
  'Kirim Tiket Dukungan',
  'Lihat Tiket Dukungan',
  'Hubungi Kami',
  'Pusat Bantuan',
  'Status Platform',
];

/* ═══ LINK JELAJAHI ═══ */
const LINK_JELAJAHI = [
  { label: 'Dataset', href: '/data/catalog' },
  { label: 'API', href: '/data/api' },
  { label: 'Model', href: '/ml' },
  { label: 'Screener Saham', href: '/studio/screener' },
  { label: 'Paket Lengkap', href: '/strategies' },
  { label: 'Analitik Pasar Modal', href: '/markets' },
];

/* ═══ TERAKHIR DIKUNJUNGI ═══ */
const TERAKHIR_DIKUNJUNGI = [
  { kategori: 'Perusahaan', label: 'Komposisi Indeks', href: '/markets', ikon: Building2 },
  { kategori: 'Aset', label: 'Saham', href: '/markets', ikon: LineChart },
  { kategori: 'Perusahaan', label: 'Ringkasan', href: '/markets', ikon: Building2 },
];

/* ═══ KARTU FITUR ═══ */
const KARTU_FITUR = [
  {
    judul: 'Jelajahi Wawasan Pasar',
    deskripsi:
      'Hidupkan data indeks Anda dengan alat interaktif terbaru kami. Ajukan demo hari ini.',
    warna: 'from-blue-500 to-indigo-700',
    tombol: ['Selengkapnya', 'Tonton Demo Video'],
  },
  {
    judul: 'Otomatisasi Wawasan untuk Keputusan',
    deskripsi:
      'Rasakan AI Portfolio Insights dengan data warehousing modern, dashboard intuitif, dan GenAI untuk mempercepat analisis risiko dan keputusan yang lebih baik.',
    warna: 'from-emerald-500 to-teal-700',
    tombol: ['Baca Riset', 'Selengkapnya'],
  },
  {
    judul: 'Analisis Aset Geospasial',
    deskripsi:
      'Eksplorasi risiko fisik dan fundamental dengan solusi analisis multi-faktor kami, termasuk penghargaan PRI Award 2025 untuk Pengakuan Aksi Iklim.',
    warna: 'from-sky-500 to-cyan-700',
    tombol: ['Ajukan Demo'],
  },
];

export default function DashboardPage() {
  return (
    <div className="min-h-full bg-[#f8fafc]">
      {/* ═══ STRIP INDEKS ═══ */}
      <div className="border-b border-[#e2e8f0] bg-white">
        <div className="flex items-stretch overflow-x-auto">
          {INDEKS.map((idx) => {
            const positif = idx.changePct >= 0;
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
                        positif ? 'text-[#16a34a]' : 'text-[#dc2626]'
                      }`}
                    >
                      {positif ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                      {positif ? '+' : ''}{idx.changePct.toFixed(2)}%
                    </span>
                  </div>
                </div>
                <MiniChart data={idx.sparkline} width={80} height={28} positive={positif} />
              </div>
            );
          })}
        </div>
      </div>

      {/* ═══ KONTEN UTAMA ═══ */}
      <div className="flex flex-col lg:flex-row">

        {/* KIRI: Riset & Kartu Fitur */}
        <div className="min-w-0 flex-1">

          {/* Riset Pasar dan Wawasan */}
          <div className="p-6">
            <div className="rounded-lg border border-[#e2e8f0] bg-white">
              <div className="flex items-center justify-between border-b border-[#e2e8f0] px-5 py-3">
                <h2 className="text-[14px] font-semibold text-[#0f172a]">Riset Pasar dan Wawasan</h2>
                <Link href="/research" className="text-[12px] font-medium text-[#2563eb] hover:text-[#1d4ed8]">
                  Lihat Semua
                </Link>
              </div>
              <div className="grid grid-cols-1 gap-0 md:grid-cols-2">
                {ARTIKEL_RISET.map((artikel, i) => {
                  const Ikon = artikel.ikon;
                  const borderR = i % 2 === 0 ? 'md:border-r' : '';
                  const borderB = i < 2 ? 'border-b' : '';
                  return (
                    <Link
                      key={artikel.id}
                      href="/research"
                      className={`group flex gap-4 p-5 ${borderR} ${borderB} border-[#e2e8f0] transition-colors hover:bg-[#f8fafc]`}
                    >
                      <div
                        className="flex h-[60px] w-[80px] shrink-0 items-center justify-center rounded"
                        style={{ backgroundColor: artikel.warna + '14' }}
                      >
                        <Ikon className="h-7 w-7" style={{ color: artikel.warna }} />
                      </div>
                      <div className="min-w-0">
                        <h3 className="text-[13px] font-bold text-[#2563eb] group-hover:underline">
                          {artikel.judul}
                        </h3>
                        <p className="mt-1 text-[11px] leading-relaxed text-[#64748b] line-clamp-3">
                          {artikel.deskripsi}
                        </p>
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Kartu Fitur */}
          <div className="grid grid-cols-1 gap-4 px-6 pb-6 md:grid-cols-4">
            {KARTU_FITUR.map((kartu, i) => (
              <div
                key={i}
                className={`overflow-hidden rounded-lg bg-gradient-to-br ${kartu.warna} text-white`}
              >
                {/* Area gambar placeholder */}
                <div className="relative h-[120px] overflow-hidden">
                  <div className="absolute inset-0 bg-white/5" />
                  <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-black/40 to-transparent" />
                </div>
                {/* Konten */}
                <div className="p-4">
                  <h3 className="text-[13px] font-bold">{kartu.judul}</h3>
                  <p className="mt-1.5 text-[11px] leading-relaxed text-white/80">{kartu.deskripsi}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {kartu.tombol.map((t, j) => (
                      <Link
                        key={j}
                        href="/markets"
                        className="rounded border border-white/50 px-3 py-1 text-[10px] font-semibold text-white transition-colors hover:bg-white/20"
                      >
                        {t}
                      </Link>
                    ))}
                  </div>
                </div>
              </div>
            ))}

            {/* Video Tutorial & Acara Mendatang */}
            <div className="rounded-lg border border-[#e2e8f0] bg-white p-4">
              <h3 className="text-[13px] font-bold text-[#0f172a]">Video Tutorial</h3>
              <p className="mt-1 text-[11px] text-[#64748b]">
                Pelajari lebih lanjut tentang pengalaman Pyhron ONE terbaru.
              </p>
              <div className="mt-4 border-t border-[#e2e8f0] pt-3">
                <h4 className="text-[12px] font-bold text-[#0f172a]">Acara Mendatang</h4>
                <div className="mt-2 space-y-2">
                  <div>
                    <p className="text-[11px] font-medium text-[#2563eb]">15 Apr 2026 - Virtual</p>
                    <p className="text-[11px] text-[#475569]">Infrastruktur dan Pusat Data, Tren Kinerja</p>
                  </div>
                  <div>
                    <p className="text-[11px] font-medium text-[#2563eb]">22 Apr 2026 - Webinar</p>
                    <p className="text-[11px] text-[#475569]">Strategi Investasi IDX Kuartal 2 2026</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="border-t border-[#e2e8f0] px-6 py-4">
            <p className="text-center text-[10px] text-[#94a3b8]">
              &copy; 2026 Pyhron Inc. Hak Cipta Dilindungi. Tunduk pada{' '}
              <span className="cursor-pointer underline">Syarat Penggunaan</span> &amp;{' '}
              <span className="cursor-pointer underline">Disclaimer</span>.{' '}
              <span className="cursor-pointer underline">Kelola Cookie</span>.
            </p>
          </div>
        </div>

        {/* SIDEBAR KANAN */}
        <div className="w-full shrink-0 border-l border-[#e2e8f0] bg-white lg:w-[260px]">
          <div className="space-y-5 p-5">

            {/* Dukungan */}
            <div>
              <h3 className="mb-1.5 text-[12px] font-bold text-[#0f172a]">Dukungan</h3>
              {LINK_DUKUNGAN.map((label) => (
                <Link key={label} href="/settings" className="block py-[3px] text-[12px] text-[#2563eb] hover:underline">
                  {label}
                </Link>
              ))}
            </div>

            {/* Jelajahi */}
            <div>
              <h3 className="mb-1.5 text-[12px] font-bold text-[#0f172a]">Jelajahi</h3>
              {LINK_JELAJAHI.map((l) => (
                <Link key={l.label} href={l.href} className="block py-[3px] text-[12px] text-[#2563eb] hover:underline">
                  {l.label}
                </Link>
              ))}
            </div>

            {/* Terakhir Dikunjungi */}
            <div>
              <h3 className="mb-2 text-[12px] font-bold text-[#0f172a]">Terakhir Dikunjungi</h3>
              <div className="space-y-3">
                {TERAKHIR_DIKUNJUNGI.map((item, i) => {
                  const Ikon = item.ikon;
                  return (
                    <Link
                      key={i}
                      href={item.href}
                      className="group flex items-center gap-2.5 rounded transition-colors hover:bg-[#f1f5f9] p-1 -mx-1"
                    >
                      <Ikon className="h-4 w-4 shrink-0 text-[#94a3b8]" />
                      <div className="min-w-0 flex-1">
                        <span className="text-[11px] text-[#64748b]">
                          {item.kategori}{' '}
                          <span className="mx-0.5 text-[#cbd5e1]">&bull;</span>{' '}
                          <span className="text-[#0f172a]">{item.label}</span>
                        </span>
                      </div>
                      <span className="text-[10px] text-[#94a3b8]">Hari ini</span>
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
