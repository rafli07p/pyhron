import { NavLink, useNavigate } from 'react-router-dom';
import {
  Activity,
  LayoutDashboard,
  BarChart3,
  Search,
  Newspaper,
  Zap,
  FlaskConical,
  Brain,
  TestTubes,
  Shield,
  Wallet,
  Globe,
  Gem,
  Landmark,
  Scale,
  ChevronLeft,
  ChevronRight,
  LogOut,
  User,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useAuthStore } from '../../store/auth';

interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    title: 'OVERVIEW',
    items: [
      { label: 'Dashboard', path: '/', icon: LayoutDashboard },
    ],
  },
  {
    title: 'MARKET DATA',
    items: [
      { label: 'Market Overview', path: '/market', icon: BarChart3 },
      { label: 'Screener', path: '/screener', icon: Search },
      { label: 'News & Sentiment', path: '/news', icon: Newspaper },
    ],
  },
  {
    title: 'TRADING',
    items: [
      { label: 'Live Trading', path: '/trading', icon: Zap },
      { label: 'Paper Trading', path: '/paper-trading', icon: FlaskConical },
      { label: 'Strategies', path: '/strategies', icon: Brain },
      { label: 'Backtesting', path: '/backtest', icon: TestTubes },
    ],
  },
  {
    title: 'RISK & ANALYTICS',
    items: [
      { label: 'Risk Dashboard', path: '/risk', icon: Shield },
      { label: 'Positions & P&L', path: '/positions', icon: Wallet },
    ],
  },
  {
    title: 'INTELLIGENCE',
    items: [
      { label: 'Macro', path: '/macro', icon: Globe },
      { label: 'Commodities', path: '/commodities', icon: Gem },
      { label: 'Fixed Income', path: '/fixed-income', icon: Landmark },
      { label: 'Governance', path: '/governance', icon: Scale },
    ],
  },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export default function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside
      className={`fixed top-0 left-0 z-40 h-screen flex flex-col bg-slate-900 border-r border-slate-700 transition-all duration-300 ${
        collapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Logo */}
      <div className="flex items-center h-16 px-4 border-b border-slate-700 shrink-0">
        <Activity className="h-6 w-6 text-blue-500 shrink-0" />
        {!collapsed && (
          <span className="ml-3 text-lg font-bold tracking-wider text-slate-100">
            PYHRON
          </span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-2">
        {navSections.map((section) => (
          <div key={section.title} className="mb-4">
            {!collapsed && (
              <p className="px-3 mb-2 text-[11px] font-semibold uppercase tracking-widest text-slate-500">
                {section.title}
              </p>
            )}
            <ul className="space-y-0.5">
              {section.items.map((item) => (
                <li key={item.path}>
                  <NavLink
                    to={item.path}
                    end={item.path === '/'}
                    className={({ isActive }) =>
                      `flex items-center gap-3 rounded-lg transition-colors duration-150 ${
                        collapsed ? 'justify-center px-2 py-2.5' : 'px-3 py-2.5'
                      } ${
                        isActive
                          ? 'bg-blue-500/10 text-blue-400 border-l-2 border-blue-500'
                          : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200 border-l-2 border-transparent'
                      }`
                    }
                    title={collapsed ? item.label : undefined}
                  >
                    <item.icon className="h-[18px] w-[18px] shrink-0" />
                    {!collapsed && (
                      <span className="text-sm font-medium truncate">
                        {item.label}
                      </span>
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      {/* User profile + collapse toggle */}
      <div className="border-t border-slate-700 p-3 shrink-0">
        {/* User info */}
        <div
          className={`flex items-center gap-3 mb-3 ${
            collapsed ? 'justify-center' : ''
          }`}
        >
          <div className="flex items-center justify-center h-8 w-8 rounded-full bg-blue-600 text-white text-xs font-bold shrink-0">
            {user?.full_name
              ? user.full_name
                  .split(' ')
                  .map((n) => n[0])
                  .join('')
                  .toUpperCase()
                  .slice(0, 2)
              : <User className="h-4 w-4" />}
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-200 truncate">
                {user?.full_name || 'User'}
              </p>
              <p className="text-xs text-slate-500 truncate">
                {user?.email || ''}
              </p>
            </div>
          )}
        </div>

        {/* Logout */}
        <button
          onClick={handleLogout}
          className={`flex items-center gap-3 w-full rounded-lg py-2 text-slate-400 hover:bg-slate-800 hover:text-red-400 transition-colors ${
            collapsed ? 'justify-center px-2' : 'px-3'
          }`}
          title="Log out"
        >
          <LogOut className="h-[18px] w-[18px] shrink-0" />
          {!collapsed && <span className="text-sm font-medium">Log out</span>}
        </button>

        {/* Collapse toggle */}
        <button
          onClick={onToggle}
          className={`flex items-center gap-3 w-full rounded-lg py-2 mt-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors ${
            collapsed ? 'justify-center px-2' : 'px-3'
          }`}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <ChevronRight className="h-[18px] w-[18px] shrink-0" />
          ) : (
            <>
              <ChevronLeft className="h-[18px] w-[18px] shrink-0" />
              <span className="text-sm font-medium">Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
