'use client';

export function ShareButtons() {
  return (
    <div className="flex gap-2">
      <button className="rounded-md border border-border px-3 py-1 text-xs text-text-secondary hover:bg-bg-tertiary">
        LinkedIn
      </button>
      <button className="rounded-md border border-border px-3 py-1 text-xs text-text-secondary hover:bg-bg-tertiary">
        X
      </button>
      <button
        className="rounded-md border border-border px-3 py-1 text-xs text-text-secondary hover:bg-bg-tertiary"
        onClick={() => navigator.clipboard?.writeText(window.location.href)}
      >
        Copy Link
      </button>
    </div>
  );
}
