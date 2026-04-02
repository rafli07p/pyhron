import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardContent } from '@/design-system/primitives/Card';
import {
  BookOpen,
  Search,
  Database,
  GitBranch,
  Code2,
} from 'lucide-react';
import Link from 'next/link';

const QUICK_LINKS = [
  {
    href: '/data/catalog',
    icon: BookOpen,
    name: 'Metric Catalog',
    description: 'Browse 144 metrics across price, fundamentals, technicals, and ML signals.',
  },
  {
    href: '/data/explorer',
    icon: Search,
    name: 'Data Explorer',
    description: 'Query and explore datasets with a SQL-like interface.',
  },
  {
    href: '/data/api',
    icon: Code2,
    name: 'Data API',
    description: 'Manage API keys and view endpoint documentation.',
  },
  {
    href: '#',
    icon: Database,
    name: 'Data Sources',
    description: 'IDX, Bloomberg, Reuters, and alternative data feeds.',
  },
  {
    href: '#',
    icon: GitBranch,
    name: 'Pipelines',
    description: 'Data ingestion and transformation pipeline status.',
  },
];

export const metadata = { title: 'Data' };

export default function DataPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Data"
        description="Explore, query, and manage market data"
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {QUICK_LINKS.map((link) => (
          <Link key={link.name} href={link.href}>
            <Card className="h-full transition-colors hover:bg-[var(--surface-2)]">
              <CardContent className="flex items-start gap-4 p-4">
                <div className="rounded-md bg-[var(--accent-50)] p-2">
                  <link.icon className="h-5 w-5 text-[var(--accent-500)]" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-[var(--text-primary)]">{link.name}</p>
                  <p className="mt-1 text-xs text-[var(--text-tertiary)]">{link.description}</p>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
