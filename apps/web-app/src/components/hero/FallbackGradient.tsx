'use client';

/**
 * CSS-only animated gradient fallback for:
 * - Devices without WebGL
 * - prefers-reduced-motion (static mode)
 * - Mobile < 640px
 */
export function FallbackGradient({ isStatic = false }: { isStatic?: boolean }) {
  return (
    <div className="absolute inset-0 overflow-hidden" aria-hidden="true">
      {/* Blob 1 — blue */}
      <div
        className={`absolute left-[-10%] top-[10%] h-[60vh] w-[60vh] rounded-full bg-[#2563eb] opacity-20 blur-[120px] ${
          isStatic ? '' : 'animate-[drift1_20s_ease-in-out_infinite]'
        }`}
      />
      {/* Blob 2 — cyan */}
      <div
        className={`absolute right-[-5%] top-[30%] h-[50vh] w-[50vh] rounded-full bg-[#06b6d4] opacity-15 blur-[100px] ${
          isStatic ? '' : 'animate-[drift2_16s_ease-in-out_infinite]'
        }`}
      />
      {/* Blob 3 — violet */}
      <div
        className={`absolute bottom-[10%] left-[20%] h-[40vh] w-[40vh] rounded-full bg-[#8b5cf6] opacity-10 blur-[80px] ${
          isStatic ? '' : 'animate-[drift3_24s_ease-in-out_infinite]'
        }`}
      />

      <style jsx>{`
        @keyframes drift1 {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(8vw, -5vh) scale(1.1); }
          66% { transform: translate(-5vw, 8vh) scale(0.95); }
        }
        @keyframes drift2 {
          0%, 100% { transform: translate(0, 0) scale(1); }
          50% { transform: translate(-10vw, 6vh) scale(1.08); }
        }
        @keyframes drift3 {
          0%, 100% { transform: translate(0, 0) scale(1); }
          40% { transform: translate(6vw, -4vh) scale(1.05); }
          80% { transform: translate(-3vw, 5vh) scale(0.97); }
        }
      `}</style>
    </div>
  );
}
