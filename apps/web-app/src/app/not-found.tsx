import Link from 'next/link';
import { Button } from '@/design-system/primitives/Button';

export default function NotFound() {
  return (
    <div className="flex h-screen flex-col items-center justify-center gap-4 bg-[var(--surface-0)]">
      <h1 className="text-6xl font-bold text-[var(--text-tertiary)]">404</h1>
      <p className="text-sm text-[var(--text-secondary)]">Page not found</p>
      <Button asChild variant="outline">
        <Link href="/dashboard">Back to Dashboard</Link>
      </Button>
    </div>
  );
}
