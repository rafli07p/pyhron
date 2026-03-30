'use client';

import { useState, useMemo } from 'react';
import Fuse from 'fuse.js';
import { ResearchCard } from './ResearchCard';
import { mockArticles } from '@/lib/mock/data/research';
import { Search } from 'lucide-react';

const categories = [
  { value: '', label: 'All Categories' },
  { value: 'quantitative-research', label: 'Quantitative Research' },
  { value: 'market-commentary', label: 'Market Commentary' },
  { value: 'factor-spotlight', label: 'Factor Spotlight' },
  { value: 'education', label: 'Education' },
  { value: 'macro', label: 'Macro' },
  { value: 'commodity', label: 'Commodity' },
  { value: 'alternative-data', label: 'Alternative Data' },
];

const ITEMS_PER_PAGE = 6;

export function ResearchHub() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  const fuse = useMemo(
    () => new Fuse(mockArticles, { keys: ['title', 'excerpt', 'tags'], threshold: 0.4 }),
    [],
  );

  const filtered = useMemo(() => {
    let results = searchQuery
      ? fuse.search(searchQuery).map((r) => r.item)
      : [...mockArticles];

    if (selectedCategory) {
      results = results.filter((a) => a.category === selectedCategory);
    }

    // Featured first
    results.sort((a, b) => (b.featured ? 1 : 0) - (a.featured ? 1 : 0));
    return results;
  }, [searchQuery, selectedCategory, fuse]);

  const totalPages = Math.ceil(filtered.length / ITEMS_PER_PAGE);
  const paginated = filtered.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

  return (
    <div>
      <div className="flex flex-col gap-4 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
            placeholder="Search research..."
            className="w-full rounded-md border border-border bg-bg-primary pl-9 pr-3 py-2 text-sm text-text-primary focus:border-accent-500 focus:outline-none"
          />
        </div>
        <select
          value={selectedCategory}
          onChange={(e) => { setSelectedCategory(e.target.value); setCurrentPage(1); }}
          className="rounded-md border border-border bg-bg-primary px-3 py-2 text-sm text-text-secondary focus:border-accent-500 focus:outline-none"
        >
          {categories.map((cat) => (
            <option key={cat.value} value={cat.value}>{cat.label}</option>
          ))}
        </select>
      </div>

      <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {paginated.map((article) => (
          <ResearchCard
            key={article.slug}
            title={article.title}
            slug={article.slug}
            excerpt={article.excerpt}
            category={article.category}
            date={article.date}
            readTime={article.readTime}
            coverImage={article.coverImage}
          />
        ))}
      </div>

      {filtered.length === 0 && (
        <p className="mt-12 text-center text-text-muted">No articles found.</p>
      )}

      {totalPages > 1 && (
        <div className="mt-8 flex items-center justify-center gap-2">
          {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
            <button
              key={page}
              onClick={() => setCurrentPage(page)}
              className={`rounded-md px-3 py-1 text-sm ${
                currentPage === page ? 'bg-accent-500 text-primary-900' : 'text-text-secondary hover:bg-bg-tertiary'
              }`}
            >
              {page}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
