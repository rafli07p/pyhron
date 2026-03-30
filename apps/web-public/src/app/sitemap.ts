import type { MetadataRoute } from 'next';
import { mockArticles } from '@/lib/mock/data/research';

export default function sitemap(): MetadataRoute.Sitemap {
  const articles = mockArticles.map((article) => ({
    url: `https://pyhron.com/research/${article.slug}`,
    lastModified: new Date(article.date),
    changeFrequency: 'weekly' as const,
    priority: 0.7,
  }));

  return [
    { url: 'https://pyhron.com', lastModified: new Date(), changeFrequency: 'daily', priority: 1.0 },
    { url: 'https://pyhron.com/research', lastModified: new Date(), changeFrequency: 'daily', priority: 0.9 },
    { url: 'https://pyhron.com/data/indices', lastModified: new Date(), priority: 0.8 },
    { url: 'https://pyhron.com/data/screener', lastModified: new Date(), priority: 0.8 },
    { url: 'https://pyhron.com/pricing', lastModified: new Date(), priority: 0.6 },
    { url: 'https://pyhron.com/about', lastModified: new Date(), priority: 0.5 },
    { url: 'https://pyhron.com/contact', lastModified: new Date(), priority: 0.4 },
    { url: 'https://pyhron.com/careers', lastModified: new Date(), priority: 0.4 },
    { url: 'https://pyhron.com/developers/api', lastModified: new Date(), priority: 0.7 },
    ...articles,
  ];
}
