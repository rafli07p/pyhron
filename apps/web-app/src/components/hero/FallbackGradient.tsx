'use client';

/**
 * White-dominant hero background with cycling ribbon animations.
 *
 * Renders three distinct ribbon "scenes" (A, B, C) stacked on top of each
 * other. Each ribbon has its own shape and internal SVG <animate> motion, and
 * a CSS keyframe on its wrapper cycles the three of them in/out over a 30s
 * loop so the background never looks like the same repeating animation:
 *
 *   ribbon A visible  0% → 30%
 *   ribbon B visible 33% → 63%
 *   ribbon C visible 66% → 96%
 *
 * The cycle restarts at 100%. All three share the same container so the
 * composition reads as one continuous flowing piece — only the underlying
 * ribbon geometry changes.
 */
export function FallbackGradient({ isStatic = false }: { isStatic?: boolean }) {
  return (
    <div className="absolute inset-0 overflow-hidden bg-white" aria-hidden="true">
      {/* Subtle radial tint — keeps it dominantly white but adds depth. */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(37,99,235,0.08),transparent_55%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,rgba(139,92,246,0.06),transparent_55%)]" />

      {/* ── Ribbon A ───────────────────────────────────────────────── */}
      <div className={`absolute inset-0 ${isStatic ? '' : 'hero-ribbon-cycle hero-ribbon-a'}`}>
        <svg
          className="absolute inset-0 h-full w-full"
          viewBox="0 0 1440 900"
          preserveAspectRatio="xMidYMid slice"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <linearGradient id="ribbonA-1" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#2563eb" stopOpacity="0.22" />
              <stop offset="50%" stopColor="#3b82f6" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#6366f1" stopOpacity="0.22" />
            </linearGradient>
            <linearGradient id="ribbonA-2" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity="0" />
              <stop offset="50%" stopColor="#06b6d4" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path fill="url(#ribbonA-1)">
            {!isStatic && (
              <animate
                attributeName="d"
                dur="14s"
                repeatCount="indefinite"
                values="
                  M0,520 C200,420 420,620 640,500 C860,380 1080,580 1280,460 C1380,400 1440,440 1440,440 L1440,900 L0,900 Z;
                  M0,480 C220,360 440,580 660,460 C880,340 1100,540 1300,420 C1390,370 1440,410 1440,410 L1440,900 L0,900 Z;
                  M0,540 C200,440 420,640 640,520 C860,400 1080,600 1280,480 C1380,420 1440,460 1440,460 L1440,900 L0,900 Z;
                  M0,520 C200,420 420,620 640,500 C860,380 1080,580 1280,460 C1380,400 1440,440 1440,440 L1440,900 L0,900 Z
                "
              />
            )}
          </path>
          <path fill="none" stroke="url(#ribbonA-2)" strokeWidth="2.5">
            {!isStatic && (
              <animate
                attributeName="d"
                dur="10s"
                repeatCount="indefinite"
                values="
                  M0,500 C240,400 480,600 720,480 C960,360 1200,560 1440,440;
                  M0,460 C240,360 480,560 720,440 C960,320 1200,520 1440,400;
                  M0,540 C240,440 480,640 720,520 C960,400 1200,600 1440,480;
                  M0,500 C240,400 480,600 720,480 C960,360 1200,560 1440,440
                "
              />
            )}
          </path>
        </svg>
      </div>

      {/* ── Ribbon B ───────────────────────────────────────────────── */}
      <div className={`absolute inset-0 ${isStatic ? 'opacity-0' : 'hero-ribbon-cycle hero-ribbon-b'}`}>
        <svg
          className="absolute inset-0 h-full w-full"
          viewBox="0 0 1440 900"
          preserveAspectRatio="xMidYMid slice"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <linearGradient id="ribbonB-1" x1="0" y1="0" x2="1" y2="0.6">
              <stop offset="0%" stopColor="#7c3aed" stopOpacity="0.10" />
              <stop offset="50%" stopColor="#2563eb" stopOpacity="0.32" />
              <stop offset="100%" stopColor="#0ea5e9" stopOpacity="0.10" />
            </linearGradient>
            <linearGradient id="ribbonB-2" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#a78bfa" stopOpacity="0" />
              <stop offset="50%" stopColor="#a78bfa" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#a78bfa" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path fill="url(#ribbonB-1)">
            {!isStatic && (
              <animate
                attributeName="d"
                dur="18s"
                repeatCount="indefinite"
                values="
                  M0,380 C180,500 360,280 560,420 C760,560 960,300 1160,440 C1320,550 1440,420 1440,420 L1440,900 L0,900 Z;
                  M0,420 C200,540 400,320 600,460 C800,600 1000,340 1200,480 C1340,580 1440,460 1440,460 L1440,900 L0,900 Z;
                  M0,360 C180,480 360,260 560,400 C760,540 960,280 1160,420 C1320,530 1440,400 1440,400 L1440,900 L0,900 Z;
                  M0,380 C180,500 360,280 560,420 C760,560 960,300 1160,440 C1320,550 1440,420 1440,420 L1440,900 L0,900 Z
                "
              />
            )}
          </path>
          <path fill="none" stroke="url(#ribbonB-2)" strokeWidth="3">
            {!isStatic && (
              <animate
                attributeName="d"
                dur="12s"
                repeatCount="indefinite"
                values="
                  M0,360 C240,500 480,260 720,400 C960,540 1200,280 1440,420;
                  M0,400 C240,540 480,300 720,440 C960,580 1200,320 1440,460;
                  M0,340 C240,480 480,240 720,380 C960,520 1200,260 1440,400;
                  M0,360 C240,500 480,260 720,400 C960,540 1200,280 1440,420
                "
              />
            )}
          </path>
        </svg>
      </div>

      {/* ── Ribbon C ───────────────────────────────────────────────── */}
      <div className={`absolute inset-0 ${isStatic ? 'opacity-0' : 'hero-ribbon-cycle hero-ribbon-c'}`}>
        <svg
          className="absolute inset-0 h-full w-full"
          viewBox="0 0 1440 900"
          preserveAspectRatio="xMidYMid slice"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <linearGradient id="ribbonC-1" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.18" />
              <stop offset="50%" stopColor="#3b82f6" stopOpacity="0.36" />
              <stop offset="100%" stopColor="#6366f1" stopOpacity="0.18" />
            </linearGradient>
          </defs>
          <path fill="url(#ribbonC-1)">
            {!isStatic && (
              <animate
                attributeName="d"
                dur="16s"
                repeatCount="indefinite"
                values="
                  M0,260 C120,360 280,180 480,320 C680,460 880,260 1080,380 C1260,480 1440,340 1440,340 L1440,640 C1260,520 1080,700 880,580 C680,460 480,660 280,540 C120,440 0,560 0,560 Z;
                  M0,280 C120,380 280,200 480,340 C680,480 880,280 1080,400 C1260,500 1440,360 1440,360 L1440,660 C1260,540 1080,720 880,600 C680,480 480,680 280,560 C120,460 0,580 0,580 Z;
                  M0,240 C120,340 280,160 480,300 C680,440 880,240 1080,360 C1260,460 1440,320 1440,320 L1440,620 C1260,500 1080,680 880,560 C680,440 480,640 280,520 C120,420 0,540 0,540 Z;
                  M0,260 C120,360 280,180 480,320 C680,460 880,260 1080,380 C1260,480 1440,340 1440,340 L1440,640 C1260,520 1080,700 880,580 C680,460 480,660 280,540 C120,440 0,560 0,560 Z
                "
              />
            )}
          </path>
        </svg>
      </div>

      {/* Keyframes for the 30s cycle. Each ribbon is visible for ~10s with a
          2s crossfade overlap, producing a smooth hand-off rather than a
          hard cut. */}
      <style>{`
        @keyframes hero-ribbon-cycle-a {
          0%, 26% { opacity: 1; transform: translateX(0); }
          33%, 66% { opacity: 0; transform: translateX(-3%); }
          73%, 100% { opacity: 1; transform: translateX(0); }
        }
        @keyframes hero-ribbon-cycle-b {
          0%, 26% { opacity: 0; transform: translateX(3%); }
          33%, 60% { opacity: 1; transform: translateX(0); }
          66%, 100% { opacity: 0; transform: translateX(-3%); }
        }
        @keyframes hero-ribbon-cycle-c {
          0%, 60% { opacity: 0; transform: translateX(3%); }
          66%, 93% { opacity: 1; transform: translateX(0); }
          100% { opacity: 0; transform: translateX(0); }
        }
        .hero-ribbon-cycle {
          will-change: opacity, transform;
          transition: none;
        }
        .hero-ribbon-a { animation: hero-ribbon-cycle-a 30s ease-in-out infinite; }
        .hero-ribbon-b { animation: hero-ribbon-cycle-b 30s ease-in-out infinite; }
        .hero-ribbon-c { animation: hero-ribbon-cycle-c 30s ease-in-out infinite; }

        @media (prefers-reduced-motion: reduce) {
          .hero-ribbon-a,
          .hero-ribbon-b,
          .hero-ribbon-c {
            animation: none;
            opacity: 1;
          }
          .hero-ribbon-b,
          .hero-ribbon-c {
            opacity: 0;
          }
        }
      `}</style>
    </div>
  );
}
