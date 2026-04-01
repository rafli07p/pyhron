import { DataTableSkeleton } from '@/components/shared/Skeletons';
export default function Loading() {
  return (
    <div className="mx-auto max-w-content px-6 py-16 space-y-8">
      <div className="h-10 w-64 rounded animate-shimmer" />
      <DataTableSkeleton rows={10} />
    </div>
  );
}
