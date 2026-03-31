import type { Metadata } from 'next';
import { StrategiesList } from '@/components/dashboard/StrategiesList';

export const metadata: Metadata = { title: 'Strategies' };

export default function StrategiesPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-medium text-text-primary">Strategies</h1>
      <StrategiesList />
    </div>
  );
}
