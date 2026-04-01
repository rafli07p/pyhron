import { ResearchCardSkeleton } from '@/components/shared/Skeletons';
export default function Loading() {
  return (
    <div className="mx-auto max-w-content px-6 py-16">
      <div className="h-10 w-64 rounded animate-shimmer" />
      <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {[1,2,3,4,5,6].map(i => <ResearchCardSkeleton key={i} />)}
      </div>
    </div>
  );
}
