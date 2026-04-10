import { PageHeader } from '@/design-system/layout/PageHeader';
import { Button } from '@/design-system/primitives/Button';
import { Card, CardContent } from '@/design-system/primitives/Card';
import { Skeleton } from '@/design-system/primitives/Skeleton';
import { Pencil } from 'lucide-react';
import Link from 'next/link';

export const metadata = { title: 'Dashboard' };

export default async function DashboardViewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div className="space-y-3">
      <PageHeader
        title={`Dashboard: ${id}`}
        description="Viewing saved dashboard"
        actions={
          <Link href={`/studio/dashboards/${id}/edit`}>
            <Button variant="outline" size="sm">
              <Pencil className="h-3.5 w-3.5" />
              Edit
            </Button>
          </Link>
        }
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="p-4">
              <Skeleton className="mb-2 h-4 w-24" />
              <Skeleton className="h-32 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
