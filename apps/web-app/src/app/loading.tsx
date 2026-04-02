import { Skeleton } from '@/design-system/primitives/Skeleton';

export default function Loading() {
  return (
    <div className="flex h-screen items-center justify-center bg-[var(--surface-0)]">
      <div className="space-y-4 text-center">
        <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-[var(--accent-500)] border-t-transparent" />
        <Skeleton className="mx-auto h-4 w-24" />
      </div>
    </div>
  );
}
