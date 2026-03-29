import { useState, useRef, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Search, Bell, LogOut, User } from 'lucide-react';
import { useAuthStore } from '../../store/auth';

const routeTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/market': 'Market Overview',
  '/screener': 'Screener',
  '/news': 'News & Sentiment',
  '/trading': 'Live Trading',
  '/paper-trading': 'Paper Trading',
  '/strategies': 'Strategies',
  '/backtest': 'Backtesting',
  '/risk': 'Risk Dashboard',
  '/positions': 'Positions & P&L',
  '/macro': 'Macro',
  '/commodities': 'Commodities',
  '/fixed-income': 'Fixed Income',
  '/governance': 'Governance',
};

export default function TopBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const pageTitle =
    routeTitles[location.pathname] ||
    (location.pathname.startsWith('/stocks/')
      ? `Stock: ${location.pathname.split('/').pop()?.toUpperCase()}`
      : 'Page');

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const initials = user?.full_name
    ? user.full_name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : 'U';

  return (
    <header className="h-16 bg-slate-900/80 backdrop-blur-md border-b border-slate-700 flex items-center justify-between px-6 shrink-0">
      {/* Page title */}
      <h1 className="text-lg font-semibold text-slate-100">{pageTitle}</h1>

      {/* Right side */}
      <div className="flex items-center gap-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search..."
            className="w-56 pl-9 pr-3 py-2 text-sm rounded-lg bg-slate-800 border border-slate-700 text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
          />
        </div>

        {/* Notifications */}
        <button className="relative p-2 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors">
          <Bell className="h-5 w-5" />
          <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-blue-500" />
        </button>

        {/* User dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold">
              {initials}
            </div>
          </button>

          {dropdownOpen && (
            <div className="absolute right-0 mt-2 w-56 rounded-lg bg-slate-800 border border-slate-700 shadow-xl py-1 z-50">
              <div className="px-4 py-3 border-b border-slate-700">
                <p className="text-sm font-medium text-slate-200">
                  {user?.full_name || 'User'}
                </p>
                <p className="text-xs text-slate-500">{user?.email || ''}</p>
              </div>
              <button
                onClick={() => { setDropdownOpen(false); }}
                className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-700 transition-colors"
              >
                <User className="h-4 w-4" />
                Profile
              </button>
              <button
                onClick={handleLogout}
                className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-red-400 hover:bg-slate-700 transition-colors"
              >
                <LogOut className="h-4 w-4" />
                Log out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
