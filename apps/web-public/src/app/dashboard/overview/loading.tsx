import { MetricCardSkeleton, ChartSkeleton } from '@/components/shared/Skeletons';
export default function Loading() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        {[1,2,3,4].map(i => <MetricCardSkeleton key={i} />)}
      </div>
      <ChartSkeleton height={300} />
    </div>
  );
}
