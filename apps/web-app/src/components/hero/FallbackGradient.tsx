'use client';

/**
 * CSS-only animated background — sharp flowing waves, NOT blurry blobs.
 * Inspired by KKR.com's flowing ribbon aesthetic.
 */
export function FallbackGradient({ isStatic = false }: { isStatic?: boolean }) {
  return (
    <div className="absolute inset-0 overflow-hidden bg-[#0a0e1a]" aria-hidden="true">
      {/* Base gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#0a1628] via-[#0f1d35] to-[#0a0e1a]" />

      {/* Flowing wave layers — sharp, NOT blurry */}
      <svg className="absolute inset-0 h-full w-full" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
        {/* Wave 1 — primary blue, large, slow */}
        <path fill="url(#wave1grad)" opacity="0.6">
          {!isStatic && (
            <animate
              attributeName="d"
              dur="12s"
              repeatCount="indefinite"
              values="
                M0,400 C200,300 400,500 600,350 C800,200 1000,450 1200,300 C1350,200 1440,350 1440,350 L1440,900 L0,900 Z;
                M0,450 C200,350 400,550 600,400 C800,250 1000,500 1200,350 C1350,250 1440,400 1440,400 L1440,900 L0,900 Z;
                M0,380 C200,280 400,480 600,330 C800,180 1000,430 1200,280 C1350,180 1440,330 1440,330 L1440,900 L0,900 Z;
                M0,400 C200,300 400,500 600,350 C800,200 1000,450 1200,300 C1350,200 1440,350 1440,350 L1440,900 L0,900 Z
              "
            />
          )}
          {isStatic && <set attributeName="d" to="M0,400 C200,300 400,500 600,350 C800,200 1000,450 1200,300 C1350,200 1440,350 1440,350 L1440,900 L0,900 Z" />}
        </path>

        {/* Wave 2 — violet accent, medium */}
        <path fill="url(#wave2grad)" opacity="0.35">
          {!isStatic && (
            <animate
              attributeName="d"
              dur="16s"
              repeatCount="indefinite"
              values="
                M0,500 C300,400 600,600 900,450 C1100,350 1300,500 1440,450 L1440,900 L0,900 Z;
                M0,550 C300,450 600,650 900,500 C1100,400 1300,550 1440,500 L1440,900 L0,900 Z;
                M0,480 C300,380 600,580 900,430 C1100,330 1300,480 1440,430 L1440,900 L0,900 Z;
                M0,500 C300,400 600,600 900,450 C1100,350 1300,500 1440,450 L1440,900 L0,900 Z
              "
            />
          )}
          {isStatic && <set attributeName="d" to="M0,500 C300,400 600,600 900,450 C1100,350 1300,500 1440,450 L1440,900 L0,900 Z" />}
        </path>

        {/* Wave 3 — cyan highlight, fast thin */}
        <path fill="none" stroke="url(#linegrad)" strokeWidth="2" opacity="0.4">
          {!isStatic && (
            <animate
              attributeName="d"
              dur="10s"
              repeatCount="indefinite"
              values="
                M0,420 C240,320 480,520 720,370 C960,220 1200,470 1440,370;
                M0,460 C240,360 480,560 720,410 C960,260 1200,510 1440,410;
                M0,400 C240,300 480,500 720,350 C960,200 1200,450 1440,350;
                M0,420 C240,320 480,520 720,370 C960,220 1200,470 1440,370
              "
            />
          )}
          {isStatic && <set attributeName="d" to="M0,420 C240,320 480,520 720,370 C960,220 1200,470 1440,370" />}
        </path>

        {/* Gradients */}
        <defs>
          <linearGradient id="wave1grad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#2563eb" />
            <stop offset="50%" stopColor="#3b82f6" />
            <stop offset="100%" stopColor="#6366f1" />
          </linearGradient>
          <linearGradient id="wave2grad" x1="0" y1="0" x2="1" y2="0.5">
            <stop offset="0%" stopColor="#7c3aed" />
            <stop offset="100%" stopColor="#2563eb" />
          </linearGradient>
          <linearGradient id="linegrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#60a5fa" stopOpacity="0" />
            <stop offset="30%" stopColor="#60a5fa" />
            <stop offset="70%" stopColor="#818cf8" />
            <stop offset="100%" stopColor="#818cf8" stopOpacity="0" />
          </linearGradient>
        </defs>
      </svg>

      {/* Subtle noise texture overlay for depth */}
      <div className="absolute inset-0 opacity-[0.03]" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=%270 0 256 256%27 xmlns=%27http://www.w3.org/2000/svg%27%3E%3Cfilter id=%27n%27%3E%3CfeTurbulence type=%27fractalNoise%27 baseFrequency=%270.9%27/%3E%3C/filter%3E%3Crect width=%27100%25%27 height=%27100%25%27 filter=%27url(%23n)%27/%3E%3C/svg%3E")' }} />
    </div>
  );
}
