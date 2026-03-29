import { type ReactNode } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuthStore } from './store/auth';
import AppLayout from './components/layout/AppLayout';
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import DashboardPage from './pages/dashboard/DashboardPage';
import MarketOverviewPage from './pages/dashboard/MarketOverviewPage';
import ScreenerPage from './pages/stocks/ScreenerPage';
import StockDetailPage from './pages/stocks/StockDetailPage';
import NewsPage from './pages/news/NewsPage';
import TradingPage from './pages/trading/TradingPage';
import PositionsPage from './pages/trading/PositionsPage';
import PaperTradingPage from './pages/paper/PaperTradingPage';
import StrategiesPage from './pages/strategies/StrategiesPage';
import BacktestPage from './pages/backtest/BacktestPage';
import RiskPage from './pages/risk/RiskPage';
import MacroPage from './pages/macro/MacroPage';
import CommoditiesPage from './pages/commodities/CommoditiesPage';
import FixedIncomePage from './pages/fixed-income/FixedIncomePage';
import GovernancePage from './pages/governance/GovernancePage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function ProtectedRoute({ children }: { children: ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Protected routes */}
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="market" element={<MarketOverviewPage />} />
            <Route path="screener" element={<ScreenerPage />} />
            <Route path="stocks/:symbol" element={<StockDetailPage />} />
            <Route path="news" element={<NewsPage />} />
            <Route path="trading" element={<TradingPage />} />
            <Route path="positions" element={<PositionsPage />} />
            <Route path="paper-trading" element={<PaperTradingPage />} />
            <Route path="strategies" element={<StrategiesPage />} />
            <Route path="backtest" element={<BacktestPage />} />
            <Route path="risk" element={<RiskPage />} />
            <Route path="macro" element={<MacroPage />} />
            <Route path="commodities" element={<CommoditiesPage />} />
            <Route path="fixed-income" element={<FixedIncomePage />} />
            <Route path="governance" element={<GovernancePage />} />
          </Route>

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
