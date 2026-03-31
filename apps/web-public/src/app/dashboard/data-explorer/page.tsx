import type { Metadata } from 'next';
import { DataExplorerView } from '@/components/dashboard/DataExplorerView';

export const metadata: Metadata = { title: 'Data Explorer' };

export default function DataExplorerPage() {
  return <DataExplorerView />;
}
