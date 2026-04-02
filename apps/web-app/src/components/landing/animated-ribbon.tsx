'use client';

export function AnimatedRibbon() {
  return (
    <svg
      viewBox="0 0 1440 600"
      xmlns="http://www.w3.org/2000/svg"
      className="absolute inset-0 h-full w-full"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
    >
      {/* Primary gold ribbon */}
      <path fill="#C9A84C" opacity="0.85">
        <animate
          attributeName="d"
          dur="8s"
          repeatCount="indefinite"
          values="
            M0,200 C360,100 720,300 1080,180 C1260,130 1380,170 1440,150 L1440,380 C1380,400 1260,360 1080,410 C720,530 360,330 0,430 Z;
            M0,260 C360,160 720,360 1080,240 C1260,190 1380,230 1440,210 L1440,440 C1380,460 1260,420 1080,470 C720,590 360,390 0,490 Z;
            M0,200 C360,100 720,300 1080,180 C1260,130 1380,170 1440,150 L1440,380 C1380,400 1260,360 1080,410 C720,530 360,330 0,430 Z
          "
        />
      </path>

      {/* Secondary navy ribbon — deeper, slower */}
      <path fill="#0A1628" opacity="0.12">
        <animate
          attributeName="d"
          dur="12s"
          repeatCount="indefinite"
          values="
            M0,280 C300,180 600,380 900,260 C1100,200 1300,280 1440,240 L1440,480 C1300,520 1100,440 900,500 C600,620 300,420 0,520 Z;
            M0,320 C300,220 600,420 900,300 C1100,240 1300,320 1440,280 L1440,520 C1300,560 1100,480 900,540 C600,660 300,460 0,560 Z;
            M0,280 C300,180 600,380 900,260 C1100,200 1300,280 1440,240 L1440,480 C1300,520 1100,440 900,500 C600,620 300,420 0,520 Z
          "
        />
      </path>

      {/* Tertiary light gold — ethereal layer */}
      <path fill="#E8C97A" opacity="0.35">
        <animate
          attributeName="d"
          dur="10s"
          repeatCount="indefinite"
          values="
            M0,160 C480,60 960,260 1440,120 L1440,340 C960,480 480,280 0,380 Z;
            M0,200 C480,100 960,300 1440,160 L1440,380 C960,520 480,320 0,420 Z;
            M0,160 C480,60 960,260 1440,120 L1440,340 C960,480 480,280 0,380 Z
          "
        />
      </path>

      {/* Accent thin line — gold strand */}
      <path
        stroke="#C9A84C"
        strokeWidth="1.5"
        fill="none"
        opacity="0.5"
      >
        <animate
          attributeName="d"
          dur="14s"
          repeatCount="indefinite"
          values="
            M0,300 C360,200 720,400 1080,280 C1260,230 1380,270 1440,250;
            M0,340 C360,240 720,440 1080,320 C1260,270 1380,310 1440,290;
            M0,300 C360,200 720,400 1080,280 C1260,230 1380,270 1440,250
          "
        />
      </path>
    </svg>
  );
}
