import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardContent } from '@/design-system/primitives/Card';
import { Skeleton } from '@/design-system/primitives/Skeleton';

export const metadata = { title: 'Workbench Preset' };

export default function WorkbenchPresetPage({ params }: { params: { id: string } }) {
  return (
    <div className="space-y-3">
      <PageHeader
        title="Loading preset..."
        description={`Preset ID: ${params.id}`}
      />

      <Card>
        <CardContent className="p-4">
          <div className="space-y-3">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-80 w-full" />
            <div className="flex gap-2">
              <Skeleton className="h-8 w-16" />
              <Skeleton className="h-8 w-16" />
              <Skeleton className="h-8 w-16" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
