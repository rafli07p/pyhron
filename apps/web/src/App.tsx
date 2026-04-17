giimport { Routes, Route, NavLink } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import LoadingSpinner from '@/shared_ui_components/LoadingSpinner';

const EquityTerminalPage = lazy(() => import('@/features/equity_terminal/EquityTerminalPage'));
const StockDetailPage = lazy(() => import('@/features/equity_terminal/StockDetailPage'));
const ScreenerPage = lazy(() => import('@/features/equity_terminal/ScreenerPage'));
const SectorHeatmapPage = lazy(() => import('@/features/equity_terminal/SectorHeatmapPage'));

const MacroDashboardPage = lazy(() => import('@/features/macro_intelligence/MacroDashboardPage'));
const YieldCurvePage = lazy(() => import('@/features/macro_intelligence/YieldCurvePage'));
const IndicatorDetailPage = lazy(() => import('@/features/macro_intelligence/IndicatorDetailPage'));
const PolicyCalendarPage = lazy(() => import('@/features/macro_intelligence/PolicyCalendarPage'));

const CommodityDashboardPage = lazy(() => import('@/features/commodity_intelligence/CommodityDashboardPage'));
const CommodityDetailPage = lazy(() => import('@/features/commodity_intelligence/CommodityDetailPage'));
const StockImpactPage = lazy(() => import('@/features/commodity_intelligence/StockImpactPage'));
const ClimateOverlayPage = lazy(() => import('@/features/commodity_intelligence/ClimateOverlayPage'));

const BondDashboardPage = lazy(() => import('@/features/fixed_income/BondDashboardPage'));
const YieldCurveAnalysisPage = lazy(() => import('@/features/fixed_income/YieldCurveAnalysisPage'));
const CreditSpreadPage = lazy(() => import('@/features/fixed_income/CreditSpreadPage'));

const GovernanceDashboardPage = lazy(() => import('@/features/governance_intelligence/GovernanceDashboardPage'));
const OwnershipChangesPage = lazy(() => import('@/features/governance_intelligence/OwnershipChangesPage'));

const StrategyManagerPage = lazy(() => import('@/features/algo_trading/StrategyManagerPage'));
const BacktestResultsPage = lazy(() => import('@/features/algo_trading/BacktestResultsPage'));
const LiveTradingPage = lazy(() => import('@/features/algo_trading/LiveTradingPage'));

interface NavItem {
  label: string;
  path: string;
}

const navSections: { title: string; items: NavItem[] }[] = [
  {
    title: 'Equity',
    items: [
      { label: 'Terminal', path: '/' },
      { label: 'Screener', path: '/screener' },
      { label: 'Sectors', path: '/sectors' },
    ],
  },
  {
    title: 'Macro',
    items: [
      { label: 'Dashboard', path: '/macro' },
      { label: 'Yield Curve', path: '/macro/yield-curve' },
      { label: 'Calendar', path: '/macro/calendar' },
    ],
  },
  {
    title: 'Commodities',
    items: [
      { label: 'Overview', path: '/commodities' },
      { label: 'Impact', path: '/commodities/impact' },
      { label: 'Climate', path: '/commodities/climate' },
    ],
  },
  {
    title: 'Fixed Income',
    items: [
      { label: 'Bonds', path: '/bonds' },
      { label: 'Yield Analysis', path: '/bonds/yield-analysis' },
      { label: 'Spreads', path: '/bonds/spreads' },
    ],
  },
  {
    title: 'Governance',
    items: [
      { label: 'Flags', path: '/governance' },
      { label: 'Ownership', path: '/governance/ownership' },
    ],
  },
  {
    title: 'Algo',
    items: [
      { label: 'Strategies', path: '/algo' },
      { label: 'Backtest', path: '/algo/backtest' },
      { label: 'Live', path: '/algo/live' },
    ],
  },
];

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `px-2 py-1 text-xs rounded transition-colors ${
    isActive
      ? 'bg-bloomberg-accent text-white'
      : 'text-bloomberg-text-secondary hover:text-bloomberg-text-primary hover:bg-bloomberg-bg-tertiary'
  }`;

export default function App() {
  return (
    <div className="min-h-screen bg-bloomberg-bg-primary flex flex-col">
      <header className="bg-bloomberg-bg-secondary border-b border-bloomberg-border px-4 py-2">
        <div className="flex items-center gap-6">
          <h1 className="text-bloomberg-accent font-mono font-bold text-lg tracking-tight">
            PYHRON
          </h1>
          <nav className="flex items-center gap-4 overflow-x-auto">
            {navSections.map((section) => (
              <div key={section.title} className="flex items-center gap-1">
                <span className="text-xxs text-bloomberg-text-muted font-mono uppercase mr-1">
                  {section.title}
                </span>
                {section.items.map((item) => (
                  <NavLink key={item.path} to={item.path} className={linkClass} end>
                    {item.label}
                  </NavLink>
                ))}
              </div>
            ))}
          </nav>
        </div>
      </header>

      <main className="flex-1 p-4 overflow-auto">
        <Suspense fallback={<LoadingSpinner />}>
          <Routes>
            <Route path="/" element={<EquityTerminalPage />} />
            <Route path="/stock/:ticker" element={<StockDetailPage />} />
            <Route path="/screener" element={<ScreenerPage />} />
            <Route path="/sectors" element={<SectorHeatmapPage />} />

            <Route path="/macro" element={<MacroDashboardPage />} />
            <Route path="/macro/yield-curve" element={<YieldCurvePage />} />
            <Route path="/macro/indicator/:id" element={<IndicatorDetailPage />} />
            <Route path="/macro/calendar" element={<PolicyCalendarPage />} />

            <Route path="/commodities" element={<CommodityDashboardPage />} />
            <Route path="/commodities/:symbol" element={<CommodityDetailPage />} />
            <Route path="/commodities/impact" element={<StockImpactPage />} />
            <Route path="/commodities/climate" element={<ClimateOverlayPage />} />

            <Route path="/bonds" element={<BondDashboardPage />} />
            <Route path="/bonds/yield-analysis" element={<YieldCurveAnalysisPage />} />
            <Route path="/bonds/spreads" element={<CreditSpreadPage />} />

            <Route path="/governance" element={<GovernanceDashboardPage />} />
            <Route path="/governance/ownership" element={<OwnershipChangesPage />} />

            <Route path="/algo" element={<StrategyManagerPage />} />
            <Route path="/algo/backtest" element={<BacktestResultsPage />} />
            <Route path="/algo/live" element={<LiveTradingPage />} />
          </Routes>
        </Suspense>
      </main>

      <footer className="bg-bloomberg-bg-secondary border-t border-bloomberg-border px-4 py-1">
        <div className="flex justify-between text-xxs text-bloomberg-text-muted font-mono">
          <span>PYHRON Terminal v0.1.0</span>
          <span>IDX Market Data</span>
          <span>{new Date().toLocaleTimeString('id-ID', { hour12: false })}</span>
        </div>
      </footer>
    </div>
  );
}
