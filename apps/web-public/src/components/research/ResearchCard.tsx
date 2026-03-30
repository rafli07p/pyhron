import Link from 'next/link';
import { formatDate } from '@/lib/utils/format';

interface ResearchCardProps {
  title: string;
  slug: string;
  excerpt: string;
  category: string;
  date: string;
  readTime: number;
  coverImage: string;
}

const categoryLabels: Record<string, string> = {
  'quantitative-research': 'Quantitative Research',
  'market-commentary': 'Market Commentary',
  'factor-spotlight': 'Factor Spotlight',
  'education': 'Education',
  'macro': 'Macro',
  'commodity': 'Commodity',
  'alternative-data': 'Alternative Data',
};

export function ResearchCard({ title, slug, excerpt, category, date, readTime, coverImage }: ResearchCardProps) {
  return (
    <Link
      href={`/research/${slug}`}
      className="group block max-w-[380px] overflow-hidden rounded-lg border border-border bg-bg-primary transition-all hover:-translate-y-1 hover:border-accent-500 hover:shadow-md"
    >
      <div className="relative aspect-video bg-bg-tertiary">
        <div className="absolute inset-0 flex items-center justify-center text-sm text-text-muted">
          {title.substring(0, 30)}...
        </div>
        <span className="absolute left-3 top-3 rounded bg-accent-500/90 px-2 py-0.5 text-xs font-medium text-primary-900">
          {categoryLabels[category] || category}
        </span>
      </div>
      <div className="p-4">
        <h3 className="text-sm font-medium text-text-primary line-clamp-2 group-hover:text-accent-500 transition-colors">
          {title}
        </h3>
        <p className="mt-2 text-xs text-text-secondary line-clamp-2">{excerpt}</p>
        <div className="mt-3 flex items-center justify-between text-xs text-text-muted">
          <span>{formatDate(date)}</span>
          <span>{readTime} min read</span>
        </div>
      </div>
    </Link>
  );
}
