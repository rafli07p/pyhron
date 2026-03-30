export function DataTableSkeleton({ rows = 8 }: { rows?: number }) {
  return (
    <div className="w-full overflow-hidden rounded-lg border border-border">
      <div className="flex gap-4 border-b border-border bg-bg-secondary px-4 py-3">
        {[120, 80, 100, 80, 80, 80].map((w, i) => (
          <div key={i} className="h-4 rounded bg-bg-tertiary" style={{ width: w }} />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className={`flex gap-4 px-4 py-2.5 ${i % 2 === 0 ? 'bg-bg-primary' : 'bg-bg-secondary/50'}`}
        >
          {[120, 80, 100, 80, 80, 80].map((w, j) => (
            <div key={j} className="h-3.5 rounded animate-shimmer" style={{ width: w }} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function ChartSkeleton({ height = 400 }: { height?: number }) {
  return (
    <div
      className="w-full rounded-lg border border-border bg-bg-secondary overflow-hidden"
      style={{ height }}
    >
      <div className="flex items-end justify-between h-full p-6">
        <div className="flex flex-col justify-between h-full py-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-3 w-12 rounded bg-bg-tertiary" />
          ))}
        </div>
        <div className="flex-1 ml-4 h-full animate-shimmer rounded" />
      </div>
    </div>
  );
}

export function ResearchCardSkeleton() {
  return (
    <div className="w-full max-w-[380px] rounded-lg border border-border overflow-hidden">
      <div className="aspect-video animate-shimmer" />
      <div className="p-4 space-y-3">
        <div className="h-4 w-3/4 rounded animate-shimmer" />
        <div className="h-3 w-full rounded animate-shimmer" />
        <div className="h-3 w-2/3 rounded animate-shimmer" />
      </div>
    </div>
  );
}

export function MetricCardSkeleton() {
  return (
    <div className="rounded-lg border border-border bg-bg-secondary p-4">
      <div className="h-3 w-20 rounded animate-shimmer mb-2" />
      <div className="h-8 w-32 rounded animate-shimmer" />
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div className="mx-auto max-w-content px-6 py-12 space-y-8">
      <div className="h-10 w-64 rounded animate-shimmer" />
      <div className="h-4 w-96 rounded animate-shimmer" />
      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <MetricCardSkeleton key={i} />
        ))}
      </div>
      <ChartSkeleton />
    </div>
  );
}
