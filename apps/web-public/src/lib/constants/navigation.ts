export interface NavItem {
  label: string;
  href: string;
  description?: string;
}

export interface MegaMenuSection {
  title: string;
  items: NavItem[];
}

export interface NavLink {
  label: string;
  href?: string;
  megaMenu?: MegaMenuSection[];
}

export const mainNav: NavLink[] = [
  {
    label: 'Solutions',
    megaMenu: [
      {
        title: 'Quantitative Analytics',
        items: [
          { label: 'Factor Models', href: '/solutions/factor-models', description: 'Multi-factor decomposition for IDX equities' },
          { label: 'Risk Analytics', href: '/solutions/risk-analytics', description: 'VaR, stress testing, and portfolio risk' },
          { label: 'Portfolio Optimizer', href: '/solutions/portfolio-optimizer', description: 'Mean-variance and Black-Litterman optimization' },
          { label: 'AI Insights', href: '/solutions/ai-insights', description: 'ML-driven alpha signals and anomaly detection' },
        ],
      },
      {
        title: 'Algorithmic Trading',
        items: [
          { label: 'Strategy Marketplace', href: '/solutions/strategy-marketplace', description: 'Pre-built quantitative strategies' },
          { label: 'Backtesting Engine', href: '/solutions/backtesting-engine', description: 'Event-driven backtesting with IDX market structure' },
          { label: 'Execution Algos', href: '/solutions/execution-algos', description: 'TWAP, VWAP, and adaptive execution' },
          { label: 'Live Terminal', href: '/solutions/live-terminal', description: 'Real-time trading terminal' },
        ],
      },
      {
        title: 'Index Products',
        items: [
          { label: 'IDX Composite', href: '/data/indices', description: 'IHSG and sector indices' },
          { label: 'Factor Indices', href: '/solutions/factor-indices', description: 'Value, momentum, quality, low-vol' },
          { label: 'Sector Indices', href: '/solutions/sector-indices', description: 'IDX sector performance tracking' },
          { label: 'Custom Builder', href: '/solutions/custom-builder', description: 'Build custom index baskets' },
        ],
      },
      {
        title: 'Market Intelligence',
        items: [
          { label: 'Macro', href: '/solutions/macro-intelligence', description: 'BI rate, GDP, CPI, yield curves' },
          { label: 'Commodity', href: '/solutions/commodity-intelligence', description: 'CPO, coal, nickel, tin prices' },
          { label: 'Fixed Income', href: '/solutions/fixed-income', description: 'Government and corporate bonds' },
          { label: 'Governance', href: '/solutions/governance', description: 'Corporate governance flags and audits' },
        ],
      },
      {
        title: 'Developer Tools',
        items: [
          { label: 'API Docs', href: '/developers/api', description: 'RESTful API reference' },
          { label: 'Python SDK', href: '/developers/api', description: 'pip install pyhron' },
          { label: 'Jupyter Integration', href: '/developers/api', description: 'Notebook-first workflows' },
        ],
      },
    ],
  },
  {
    label: 'Research',
    megaMenu: [
      {
        title: 'Research & Insights',
        items: [
          { label: 'Latest', href: '/research', description: 'Most recent publications' },
          { label: 'Commentary', href: '/research?category=market-commentary', description: 'Market commentary and analysis' },
          { label: 'Papers', href: '/research?category=quantitative-research', description: 'Quantitative research papers' },
          { label: 'Factor Spotlight', href: '/research?category=factor-spotlight', description: 'Deep dives into factor performance' },
        ],
      },
      {
        title: 'Thematic',
        items: [
          { label: 'Microstructure', href: '/research?category=education', description: 'IDX market microstructure' },
          { label: 'Commodity-Equity', href: '/research?category=commodity', description: 'Commodity-equity linkages' },
          { label: 'Macro/ASEAN', href: '/research?category=macro', description: 'Macro and ASEAN analysis' },
          { label: 'Alt Data', href: '/research?category=alternative-data', description: 'Alternative data research' },
        ],
      },
      {
        title: 'Education',
        items: [
          { label: 'Academy', href: '/research?category=education', description: 'Learn quantitative finance' },
          { label: 'Python Tutorials', href: '/research?category=education', description: 'Python for quant finance' },
          { label: 'Webinars', href: '/research?category=education', description: 'Live and recorded sessions' },
        ],
      },
      {
        title: 'Publications',
        items: [
          { label: 'Quarterly Review', href: '/research', description: 'Quarterly market review' },
          { label: 'Annual Outlook', href: '/research', description: 'Annual market outlook' },
          { label: 'White Papers', href: '/research', description: 'In-depth research papers' },
        ],
      },
    ],
  },
  {
    label: 'Data',
    megaMenu: [
      {
        title: 'Index Data',
        items: [
          { label: 'Dashboard', href: '/data/indices', description: 'Index performance dashboard' },
          { label: 'Constituents', href: '/data/indices', description: 'Index constituent data' },
          { label: 'Historical CSV', href: '/data/indices', description: 'Download historical data' },
          { label: 'Factsheets PDF', href: '/data/indices', description: 'Index factsheet downloads' },
        ],
      },
      {
        title: 'Market Data',
        items: [
          { label: 'Screener', href: '/data/screener', description: 'Stock screener with 50+ filters' },
          { label: 'Heatmaps', href: '/data/screener', description: 'Sector and market heatmaps' },
          { label: 'Correlations', href: '/data/screener', description: 'Cross-asset correlations' },
          { label: 'Liquidity', href: '/data/screener', description: 'Liquidity analysis' },
        ],
      },
      {
        title: 'Alt Data',
        items: [
          { label: 'Sentiment', href: '/data/screener', description: 'News sentiment analysis' },
          { label: 'Impact', href: '/data/screener', description: 'Commodity-equity impact' },
          { label: 'Climate', href: '/data/screener', description: 'Climate risk data' },
        ],
      },
      {
        title: 'Downloads',
        items: [
          { label: 'Catalog', href: '/data/indices', description: 'Data catalog' },
          { label: 'API Ref', href: '/developers/api', description: 'API documentation' },
          { label: 'Samples', href: '/data/indices', description: 'Sample datasets' },
        ],
      },
    ],
  },
  {
    label: 'Clients',
    href: '/about',
  },
  {
    label: 'About',
    href: '/about',
  },
];

export const footerNav = {
  solutions: [
    { label: 'Factor Models', href: '/solutions/factor-models' },
    { label: 'Backtesting', href: '/solutions/backtesting-engine' },
    { label: 'Live Trading', href: '/solutions/live-terminal' },
    { label: 'Screener', href: '/data/screener' },
    { label: 'API', href: '/developers/api' },
  ],
  research: [
    { label: 'Latest Research', href: '/research' },
    { label: 'Market Commentary', href: '/research?category=market-commentary' },
    { label: 'Factor Spotlight', href: '/research?category=factor-spotlight' },
    { label: 'Education', href: '/research?category=education' },
  ],
  company: [
    { label: 'About', href: '/about' },
    { label: 'Careers', href: '/careers' },
    { label: 'Contact', href: '/contact' },
    { label: 'Pricing', href: '/pricing' },
  ],
  legal: [
    { label: 'Terms', href: '/terms' },
    { label: 'Privacy', href: '/privacy' },
    { label: 'Disclaimer', href: '/disclaimer' },
  ],
};
