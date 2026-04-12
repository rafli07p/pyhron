import Link from 'next/link';
import { ArrowRight, Play } from 'lucide-react';
import { AnimatedRibbon } from './animated-ribbon';

export function Hero() {
  return (
    <section className="relative flex min-h-screen items-center overflow-hidden bg-[#F8F7F4]">
      <AnimatedRibbon />

      {/* Content overlay */}
      <div className="relative z-10 mx-auto w-full max-w-7xl px-6 py-32 lg:px-12">
        <div className="max-w-2xl">
          {/* Label */}
          <p className="text-xs font-medium uppercase tracking-[0.2em] text-[#6B7280]">
            Institutional Quantitative Research
          </p>

          {/* Headline */}
          <h1 className="mt-6 text-[clamp(2.5rem,6vw,5.5rem)] font-normal leading-[1.05] tracking-tight text-[#0A1628]">
            Where Indonesian
            <br />
            Markets Meet
            <br />
            <span className="text-[#C9A84C]">Institutional</span>
            {' '}Intelligence
          </h1>

          {/* Divider */}
          <div className="mt-8 h-[2px] w-10 bg-[#C9A84C]" />

          {/* CTAs */}
          <div className="mt-8 flex items-center gap-4">
            <Link
              href="/register"
              className="inline-flex items-center gap-2 bg-[#0A1628] px-7 py-3.5 text-sm font-medium text-white transition-colors hover:bg-[#0F2040]"
            >
              Request Access
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/research-and-insights"
              className="inline-flex items-center gap-2 border border-[#0A1628] px-7 py-3.5 text-sm font-medium text-[#0A1628] transition-colors hover:bg-[#0A1628]/5"
            >
              View Research
            </Link>
          </div>
        </div>
      </div>

      {/* Circular CTA — KKR style */}
      <div className="absolute right-[8%] top-1/2 z-10 hidden -translate-y-1/2 lg:block">
        <Link
          href="/about"
          className="group flex h-40 w-40 flex-col items-center justify-center rounded-full bg-[#0A1628] text-white transition-transform hover:scale-105"
        >
          <Play className="mb-2 h-5 w-5 opacity-80 transition-opacity group-hover:opacity-100" />
          <span className="text-[10px] font-medium uppercase tracking-[0.15em] opacity-80">
            See How
          </span>
          <span className="text-[10px] font-medium uppercase tracking-[0.15em] opacity-80">
            It Works
          </span>
        </Link>
      </div>
    </section>
  );
}
