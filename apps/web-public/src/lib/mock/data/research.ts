export interface MockArticleMeta {
  title: string;
  slug: string;
  author: { name: string; role: string; avatar: string };
  date: string;
  category: string;
  tags: string[];
  readTime: number;
  featured: boolean;
  excerpt: string;
  coverImage: string;
}

export const mockArticles: MockArticleMeta[] = [
  {
    title: 'Fama-French Five-Factor Decomposition of IHSG Returns (2015-2025)',
    slug: 'fama-french-five-factor-ihsg',
    author: { name: 'Pyhron Research', role: 'Research Team', avatar: '/images/authors/team.jpg' },
    date: '2026-03-15T00:00:00Z',
    category: 'quantitative-research',
    tags: ['factor-models', 'IHSG', 'fama-french'],
    readTime: 12,
    featured: true,
    excerpt: 'Decomposing IHSG returns through the Fama-French five-factor lens reveals persistent value and profitability premia in Indonesian equities.',
    coverImage: '/images/research/fama-french.jpg',
  },
  {
    title: 'Pairs Trading on Indonesian Banking Sector via Johansen Cointegration',
    slug: 'pairs-trading-banking-cointegration',
    author: { name: 'Rafli Perdana', role: 'Quantitative Strategy', avatar: '/images/authors/rafli.jpg' },
    date: '2026-03-08T00:00:00Z',
    category: 'quantitative-research',
    tags: ['pairs-trading', 'cointegration', 'banking'],
    readTime: 15,
    featured: false,
    excerpt: 'Johansen cointegration tests on BBCA-BBRI and BMRI-BBNI pairs yield statistically significant mean-reversion signals with Sharpe ratios above 1.5.',
    coverImage: '/images/research/pairs-trading.jpg',
  },
  {
    title: 'CPO Price Transmission to Plantation Stocks: A Granger Causality Study',
    slug: 'cpo-price-transmission-granger',
    author: { name: 'Pyhron Research', role: 'Research Team', avatar: '/images/authors/team.jpg' },
    date: '2026-02-28T00:00:00Z',
    category: 'commodity',
    tags: ['CPO', 'commodity-equity', 'granger-causality'],
    readTime: 10,
    featured: false,
    excerpt: 'CPO futures prices Granger-cause AALI and LSIP returns with a 2-3 day lag, offering a predictive signal for plantation sector positioning.',
    coverImage: '/images/research/cpo-transmission.jpg',
  },
  {
    title: 'Constructing a Momentum Factor Index for IDX LQ45',
    slug: 'momentum-factor-index-lq45',
    author: { name: 'Rafli Perdana', role: 'Quantitative Strategy', avatar: '/images/authors/rafli.jpg' },
    date: '2026-02-20T00:00:00Z',
    category: 'factor-spotlight',
    tags: ['momentum', 'LQ45', 'factor-index'],
    readTime: 8,
    featured: true,
    excerpt: 'A 12-1 month momentum strategy on LQ45 constituents generates 4.2% annual alpha over the equal-weight benchmark after transaction costs.',
    coverImage: '/images/research/momentum-index.jpg',
  },
  {
    title: 'BI Rate Decisions and IDX Sector Rotation: An Event Study',
    slug: 'bi-rate-sector-rotation',
    author: { name: 'Pyhron Research', role: 'Research Team', avatar: '/images/authors/team.jpg' },
    date: '2026-02-10T00:00:00Z',
    category: 'macro',
    tags: ['BI-rate', 'sector-rotation', 'event-study'],
    readTime: 11,
    featured: false,
    excerpt: 'Rate cuts shift capital from banking to property and consumer sectors within 5 trading days, with financials underperforming by 1.8% on average.',
    coverImage: '/images/research/bi-rate-rotation.jpg',
  },
  {
    title: 'Algorithmic Trading on IDX: T+2, Lot Sizes, and Market Microstructure',
    slug: 'algorithmic-trading-idx-microstructure',
    author: { name: 'Rafli Perdana', role: 'Quantitative Strategy', avatar: '/images/authors/rafli.jpg' },
    date: '2026-01-25T00:00:00Z',
    category: 'education',
    tags: ['algorithmic-trading', 'microstructure', 'IDX'],
    readTime: 14,
    featured: false,
    excerpt: 'IDX operates T+2 settlement with 100-share lots and price tick sizes varying by price band. Understanding these constraints is critical for algo design.',
    coverImage: '/images/research/algo-trading.jpg',
  },
  {
    title: 'IDX Market Commentary, March 2026',
    slug: 'idx-commentary-march-2026',
    author: { name: 'Pyhron Research', role: 'Research Team', avatar: '/images/authors/team.jpg' },
    date: '2026-03-28T00:00:00Z',
    category: 'market-commentary',
    tags: ['market-commentary', 'IHSG', 'monthly-review'],
    readTime: 6,
    featured: false,
    excerpt: 'IHSG gained 2.8% in March, led by banking (+4.1%) and mining (+3.5%). Foreign net buying reached Rp 8.2T, highest since October 2025.',
    coverImage: '/images/research/commentary-march.jpg',
  },
];
