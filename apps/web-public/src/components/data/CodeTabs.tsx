'use client';
import { useState } from 'react';

interface CodeTabsProps {
  examples: { label: string; code: string }[];
}

export function CodeTabs({ examples }: CodeTabsProps) {
  const [active, setActive] = useState(0);
  return (
    <div>
      <div className="flex gap-1 border-b border-border">
        {examples.map((ex, i) => (
          <button
            key={ex.label}
            onClick={() => setActive(i)}
            className={`px-3 py-1.5 text-xs font-medium transition-colors ${
              active === i ? 'border-b-2 border-accent-500 text-accent-500' : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            {ex.label}
          </button>
        ))}
      </div>
      <pre className="mt-0 overflow-x-auto rounded-b-lg bg-bg-tertiary p-4 font-mono text-sm text-text-secondary">
        {examples[active].code}
      </pre>
    </div>
  );
}
