import type { Metadata } from 'next';
import { CodeTabs } from '@/components/data/CodeTabs';

export const metadata: Metadata = {
  title: 'API Documentation',
  description: 'Pyhron RESTful API reference for market data, screener, backtesting, and trading.',
};

interface EndpointDoc {
  method: string;
  path: string;
  description: string;
  auth?: boolean;
  params?: { name: string; type: string; required: boolean; description: string }[];
  responseShape: string;
  examples: { label: string; code: string }[];
}

const endpoints: EndpointDoc[] = [
  {
    method: 'GET', path: '/v1/market/overview',
    description: 'Market overview with IHSG composite level, volume, advances/declines.',
    responseShape: `{ "index_name": "IHSG", "last_value": 7245.32, "change": 42.18,
  "change_pct": 0.59, "volume": 12450000000, "value_traded": 8750000000000,
  "advances": 245, "declines": 198, "unchanged": 87, "timestamp": "..." }`,
    examples: [
      { label: 'cURL', code: 'curl https://api.pyhron.com/v1/market/overview \\\n  -H "Authorization: Bearer $TOKEN"' },
      { label: 'Python', code: `import requests\nres = requests.get("https://api.pyhron.com/v1/market/overview",\n    headers={"Authorization": f"Bearer {token}"})\ndata = res.json()\nprint(f"IHSG: {data['last_value']} ({data['change_pct']:+.2f}%)")` },
      { label: 'JavaScript', code: `const res = await fetch("https://api.pyhron.com/v1/market/overview", {\n  headers: { Authorization: \`Bearer \${token}\` }\n});\nconst data = await res.json();` },
    ],
  },
  {
    method: 'GET', path: '/v1/market/instruments',
    description: 'List all tradeable instruments with sector, market cap, and LQ45 membership.',
    params: [
      { name: 'sector', type: 'string', required: false, description: 'Filter by sector (e.g. "Financials")' },
      { name: 'lq45_only', type: 'boolean', required: false, description: 'Only LQ45 constituents' },
    ],
    responseShape: `[{ "symbol": "BBCA", "name": "Bank Central Asia Tbk", "exchange": "IDX",
  "sector": "Financials", "market_cap": 1200000000000000, "is_lq45": true, "board": "Main" }]`,
    examples: [
      { label: 'cURL', code: 'curl "https://api.pyhron.com/v1/market/instruments?sector=Financials&lq45_only=true" \\\n  -H "Authorization: Bearer $TOKEN"' },
      { label: 'Python', code: `res = requests.get("https://api.pyhron.com/v1/market/instruments",\n    params={"sector": "Financials", "lq45_only": "true"},\n    headers={"Authorization": f"Bearer {token}"})\nstocks = res.json()` },
      { label: 'JavaScript', code: `const res = await fetch(\n  "https://api.pyhron.com/v1/market/instruments?sector=Financials",\n  { headers: { Authorization: \`Bearer \${token}\` } }\n);` },
    ],
  },
  {
    method: 'GET', path: '/v1/market/ohlcv/:symbol',
    description: 'OHLCV price bars for a given symbol.',
    params: [
      { name: 'symbol', type: 'string', required: true, description: 'Ticker symbol (path param)' },
      { name: 'interval', type: 'string', required: false, description: '"daily" | "weekly" | "monthly"' },
      { name: 'limit', type: 'number', required: false, description: 'Number of bars (default: 365)' },
    ],
    responseShape: `[{ "timestamp": "2026-03-28T00:00:00Z", "open": 9850, "high": 9900,
  "low": 9800, "close": 9875, "volume": 15000000, "value": 148125000000 }]`,
    examples: [
      { label: 'cURL', code: 'curl "https://api.pyhron.com/v1/market/ohlcv/BBCA?interval=daily&limit=30" \\\n  -H "Authorization: Bearer $TOKEN"' },
      { label: 'Python', code: `res = requests.get("https://api.pyhron.com/v1/market/ohlcv/BBCA",\n    params={"interval": "daily", "limit": 30},\n    headers={"Authorization": f"Bearer {token}"})` },
      { label: 'JavaScript', code: `const res = await fetch(\n  "https://api.pyhron.com/v1/market/ohlcv/BBCA?interval=daily&limit=30",\n  { headers: { Authorization: \`Bearer \${token}\` } }\n);` },
    ],
  },
  {
    method: 'GET', path: '/v1/screener/screen',
    description: 'Screen stocks by fundamental and technical criteria.',
    params: [
      { name: 'sector', type: 'string', required: false, description: 'Filter by sector' },
      { name: 'market_cap_min', type: 'number', required: false, description: 'Min market cap (IDR)' },
      { name: 'pe_min', type: 'number', required: false, description: 'Min P/E ratio' },
      { name: 'pe_max', type: 'number', required: false, description: 'Max P/E ratio' },
      { name: 'roe_min', type: 'number', required: false, description: 'Min ROE (%)' },
      { name: 'sort_by', type: 'string', required: false, description: 'market_cap | pe_ratio | roe | volume' },
      { name: 'limit', type: 'number', required: false, description: 'Results per page (default: 50)' },
    ],
    responseShape: `{ "meta": { "total_matches": 42, "sort_by": "market_cap", "limit": 50 },
  "results": [{ "symbol": "BBCA", "last_price": 9875, "change_pct": 1.25,
    "market_cap": 1200000000000000, "pe_ratio": 25.3, "roe": 19.2 }] }`,
    examples: [
      { label: 'cURL', code: 'curl "https://api.pyhron.com/v1/screener/screen?sector=Financials&roe_min=15&sort_by=market_cap" \\\n  -H "Authorization: Bearer $TOKEN"' },
      { label: 'Python', code: `res = requests.get("https://api.pyhron.com/v1/screener/screen",\n    params={"sector": "Financials", "roe_min": 15, "sort_by": "market_cap"},\n    headers={"Authorization": f"Bearer {token}"})` },
      { label: 'JavaScript', code: `const params = new URLSearchParams({ sector: "Financials", roe_min: "15" });\nconst res = await fetch(\`https://api.pyhron.com/v1/screener/screen?\${params}\`,\n  { headers: { Authorization: \`Bearer \${token}\` } }\n);` },
    ],
  },
  {
    method: 'GET', path: '/v1/macro/indicators',
    description: 'Indonesian macro indicators: BI rate, GDP, CPI, exchange rate.',
    responseShape: `[{ "code": "BI_RATE", "name": "BI 7-Day Reverse Repo Rate",
  "latest_value": 5.75, "unit": "%", "period": "2026-03", "source": "Bank Indonesia" }]`,
    examples: [
      { label: 'cURL', code: 'curl https://api.pyhron.com/v1/macro/indicators \\\n  -H "Authorization: Bearer $TOKEN"' },
      { label: 'Python', code: `res = requests.get("https://api.pyhron.com/v1/macro/indicators",\n    headers={"Authorization": f"Bearer {token}"})` },
      { label: 'JavaScript', code: `const res = await fetch("https://api.pyhron.com/v1/macro/indicators",\n  { headers: { Authorization: \`Bearer \${token}\` } }\n);` },
    ],
  },
  {
    method: 'GET', path: '/v1/commodities/dashboard',
    description: 'Commodity prices: CPO, coal, nickel, tin, gold, rubber.',
    responseShape: `{ "commodities": [{ "code": "CPO", "name": "Crude Palm Oil",
  "last_price": 4125, "currency": "MYR", "unit": "MT", "change_pct": 1.23 }],
  "last_updated": "2026-03-28T00:00:00Z" }`,
    examples: [
      { label: 'cURL', code: 'curl https://api.pyhron.com/v1/commodities/dashboard \\\n  -H "Authorization: Bearer $TOKEN"' },
      { label: 'Python', code: `res = requests.get("https://api.pyhron.com/v1/commodities/dashboard",\n    headers={"Authorization": f"Bearer {token}"})` },
      { label: 'JavaScript', code: `const res = await fetch("https://api.pyhron.com/v1/commodities/dashboard",\n  { headers: { Authorization: \`Bearer \${token}\` } }\n);` },
    ],
  },
  {
    method: 'GET', path: '/v1/bonds/government',
    description: 'Government bond yields, prices, duration, and outstanding amounts.',
    responseShape: `[{ "series": "FR0098", "bond_type": "Fixed Rate", "coupon_rate": 7.125,
  "maturity_date": "2038-06-15", "yield_to_maturity": 6.85, "price": 102.45 }]`,
    examples: [
      { label: 'cURL', code: 'curl https://api.pyhron.com/v1/bonds/government \\\n  -H "Authorization: Bearer $TOKEN"' },
      { label: 'Python', code: `res = requests.get("https://api.pyhron.com/v1/bonds/government",\n    headers={"Authorization": f"Bearer {token}"})` },
      { label: 'JavaScript', code: `const res = await fetch("https://api.pyhron.com/v1/bonds/government",\n  { headers: { Authorization: \`Bearer \${token}\` } }\n);` },
    ],
  },
  {
    method: 'GET', path: '/v1/strategies/', auth: true,
    description: 'List all trading strategies with parameters and risk limits.',
    responseShape: `[{ "id": "strat-001", "name": "IDX Momentum", "strategy_type": "momentum",
  "is_enabled": true, "parameters": { "lookback": 252 },
  "risk_limits": { "max_drawdown": 0.15 }, "description": "12-1 month momentum on LQ45" }]`,
    examples: [
      { label: 'cURL', code: 'curl https://api.pyhron.com/v1/strategies/ \\\n  -H "Authorization: Bearer $TOKEN"' },
      { label: 'Python', code: `res = requests.get("https://api.pyhron.com/v1/strategies/",\n    headers={"Authorization": f"Bearer {token}"})` },
      { label: 'JavaScript', code: `const res = await fetch("https://api.pyhron.com/v1/strategies/",\n  { headers: { Authorization: \`Bearer \${token}\` } }\n);` },
    ],
  },
  {
    method: 'POST', path: '/v1/backtest/', auth: true,
    description: 'Submit a backtest job. Returns task_id for status polling.',
    params: [
      { name: 'strategy_name', type: 'string', required: true, description: 'Strategy identifier' },
      { name: 'symbols', type: 'string[]', required: true, description: 'Ticker symbols to backtest' },
      { name: 'start_date', type: 'string', required: true, description: 'ISO date (e.g. "2024-01-01")' },
      { name: 'end_date', type: 'string', required: true, description: 'ISO date (e.g. "2025-12-31")' },
      { name: 'initial_capital', type: 'number', required: true, description: 'Starting capital in IDR' },
    ],
    responseShape: `{ "task_id": "bt-abc123", "status": "PENDING", "strategy_name": "IDX Momentum" }`,
    examples: [
      { label: 'cURL', code: `curl -X POST https://api.pyhron.com/v1/backtest/ \\\n  -H "Authorization: Bearer $TOKEN" \\\n  -H "Content-Type: application/json" \\\n  -d '{"strategy_name":"IDX Momentum","symbols":["BBCA","BBRI"],"start_date":"2024-01-01","end_date":"2025-12-31","initial_capital":1000000000}'` },
      { label: 'Python', code: `res = requests.post("https://api.pyhron.com/v1/backtest/",\n    json={"strategy_name": "IDX Momentum", "symbols": ["BBCA", "BBRI"],\n          "start_date": "2024-01-01", "end_date": "2025-12-31",\n          "initial_capital": 1_000_000_000},\n    headers={"Authorization": f"Bearer {token}"})` },
      { label: 'JavaScript', code: `const res = await fetch("https://api.pyhron.com/v1/backtest/", {\n  method: "POST",\n  headers: { Authorization: \`Bearer \${token}\`, "Content-Type": "application/json" },\n  body: JSON.stringify({\n    strategy_name: "IDX Momentum", symbols: ["BBCA", "BBRI"],\n    start_date: "2024-01-01", end_date: "2025-12-31", initial_capital: 1e9\n  })\n});` },
    ],
  },
  {
    method: 'GET', path: '/v1/risk/:strategy_id/snapshot', auth: true,
    description: 'Real-time risk snapshot: VaR, exposure, concentration, drawdown.',
    params: [
      { name: 'strategy_id', type: 'string', required: true, description: 'Strategy ID (path param)' },
    ],
    responseShape: `{ "strategy_id": "strat-001", "nav_idr": 1250000000,
  "exposure": { "gross_exposure_idr": 1100000000, "beta_vs_ihsg": 0.85 },
  "var": { "var_1d_95_idr": 25000000, "var_1d_99_idr": 38000000 },
  "drawdown_pct": -2.1, "kill_switch_state": "ARMED" }`,
    examples: [
      { label: 'cURL', code: 'curl https://api.pyhron.com/v1/risk/strat-001/snapshot \\\n  -H "Authorization: Bearer $TOKEN"' },
      { label: 'Python', code: `res = requests.get("https://api.pyhron.com/v1/risk/strat-001/snapshot",\n    headers={"Authorization": f"Bearer {token}"})` },
      { label: 'JavaScript', code: `const res = await fetch("https://api.pyhron.com/v1/risk/strat-001/snapshot",\n  { headers: { Authorization: \`Bearer \${token}\` } }\n);` },
    ],
  },
  {
    method: 'POST', path: '/v1/auth/login',
    description: 'Authenticate with email and password. Returns JWT access and refresh tokens.',
    params: [
      { name: 'email', type: 'string', required: true, description: 'Account email' },
      { name: 'password', type: 'string', required: true, description: 'Account password' },
    ],
    responseShape: `{ "access_token": "eyJ...", "refresh_token": "eyJ...",
  "token_type": "bearer", "expires_in": 3600 }`,
    examples: [
      { label: 'cURL', code: `curl -X POST https://api.pyhron.com/v1/auth/login \\\n  -H "Content-Type: application/json" \\\n  -d '{"email":"you@company.com","password":"your-password"}'` },
      { label: 'Python', code: `res = requests.post("https://api.pyhron.com/v1/auth/login",\n    json={"email": "you@company.com", "password": "your-password"})` },
      { label: 'JavaScript', code: `const res = await fetch("https://api.pyhron.com/v1/auth/login", {\n  method: "POST",\n  headers: { "Content-Type": "application/json" },\n  body: JSON.stringify({ email: "you@company.com", password: "your-password" })\n});` },
    ],
  },
  {
    method: 'POST', path: '/v1/auth/refresh',
    description: 'Refresh an expired access token using the refresh token.',
    params: [
      { name: 'refresh_token', type: 'string', required: true, description: 'Refresh token from login' },
    ],
    responseShape: `{ "access_token": "eyJ...", "refresh_token": "eyJ...",
  "token_type": "bearer", "expires_in": 3600 }`,
    examples: [
      { label: 'cURL', code: `curl -X POST https://api.pyhron.com/v1/auth/refresh \\\n  -H "Content-Type: application/json" \\\n  -d '{"refresh_token":"eyJ..."}'` },
      { label: 'Python', code: `res = requests.post("https://api.pyhron.com/v1/auth/refresh",\n    json={"refresh_token": refresh_token})` },
      { label: 'JavaScript', code: `const res = await fetch("https://api.pyhron.com/v1/auth/refresh", {\n  method: "POST",\n  headers: { "Content-Type": "application/json" },\n  body: JSON.stringify({ refresh_token: refreshToken })\n});` },
    ],
  },
];

const methodColors: Record<string, string> = {
  GET: 'bg-positive/10 text-positive',
  POST: 'bg-warning/10 text-warning',
  PUT: 'bg-accent-500/10 text-accent-500',
  DELETE: 'bg-negative/10 text-negative',
};

const errorCodes = [
  { code: '400', description: 'Bad Request — Invalid parameters or malformed request body.' },
  { code: '401', description: 'Unauthorized — Missing or expired access token.' },
  { code: '403', description: 'Forbidden — Insufficient permissions for this resource.' },
  { code: '404', description: 'Not Found — Resource does not exist.' },
  { code: '429', description: 'Rate Limited — Too many requests. Check X-RateLimit-* headers.' },
];

export default function ApiDocsPage() {
  return (
    <div className="mx-auto max-w-content px-6 py-16 md:py-24">
      <h1 className="font-display text-4xl text-text-primary md:text-5xl">API Documentation</h1>
      <p className="mt-4 text-text-secondary">
        RESTful API for market data, screening, backtesting, and trading. Base URL: <code className="font-mono text-accent-500">https://api.pyhron.com/v1</code>
      </p>

      {/* Authentication */}
      <section className="mt-12">
        <h2 className="text-xl font-medium text-text-primary mb-2">Authentication</h2>
        <p className="text-sm text-text-secondary mb-4">
          POST to /v1/auth/login with email and password. Include the access token as a Bearer token in the Authorization header. Tokens expire after 1 hour; use /v1/auth/refresh to get a new pair.
        </p>
        <div className="rounded-lg border border-border bg-bg-tertiary p-4">
          <pre className="text-sm font-mono text-text-secondary overflow-x-auto">{`curl -X POST https://api.pyhron.com/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"email": "you@company.com", "password": "your-password"}'

# Response: { "access_token": "...", "refresh_token": "...", "expires_in": 3600 }

curl https://api.pyhron.com/v1/market/overview \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"`}</pre>
        </div>
      </section>

      {/* Rate Limits */}
      <section className="mt-12">
        <h2 className="text-xl font-medium text-text-primary mb-2">Rate Limits</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-border">
              <th className="py-2 text-left text-text-muted">Tier</th>
              <th className="py-2 text-left text-text-muted">Limit</th>
              <th className="py-2 text-left text-text-muted">Window</th>
            </tr></thead>
            <tbody>
              <tr className="border-b border-border"><td className="py-2">Free</td><td className="py-2 font-mono">100</td><td className="py-2">per day</td></tr>
              <tr className="border-b border-border"><td className="py-2">Pro</td><td className="py-2 font-mono">10,000</td><td className="py-2">per day</td></tr>
              <tr><td className="py-2">Enterprise</td><td className="py-2 font-mono">Unlimited</td><td className="py-2">&mdash;</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* Error Codes */}
      <section className="mt-12">
        <h2 className="text-xl font-medium text-text-primary mb-4">Error Handling</h2>
        <div className="space-y-2">
          {errorCodes.map((e) => (
            <div key={e.code} className="flex items-start gap-3 text-sm">
              <code className="rounded bg-negative/10 px-2 py-0.5 font-mono text-xs text-negative">{e.code}</code>
              <span className="text-text-secondary">{e.description}</span>
            </div>
          ))}
        </div>
        <pre className="mt-4 rounded-lg bg-bg-tertiary p-4 text-sm font-mono text-text-secondary overflow-x-auto">{`// Error response format:
{ "detail": "Invalid credentials" }  // 401
{ "detail": "Rate limit exceeded" }  // 429`}</pre>
      </section>

      {/* Endpoints */}
      <section className="mt-12">
        <h2 className="text-xl font-medium text-text-primary mb-4">Endpoints</h2>
        <div className="space-y-4">
          {endpoints.map((ep) => (
            <details key={ep.method + ep.path} className="group rounded-lg border border-border overflow-hidden">
              <summary className="flex cursor-pointer items-start gap-3 p-4 hover:bg-bg-secondary transition-colors">
                <span className={`rounded px-2 py-0.5 text-xs font-mono font-medium ${methodColors[ep.method] || ''}`}>{ep.method}</span>
                <div className="flex-1">
                  <code className="text-sm font-mono text-text-primary">{ep.path}</code>
                  {ep.auth && <span className="ml-2 rounded bg-warning/10 px-1.5 py-0.5 text-xs text-warning">Auth</span>}
                  <p className="mt-1 text-xs text-text-secondary">{ep.description}</p>
                </div>
              </summary>
              <div className="border-t border-border bg-bg-secondary p-4 space-y-4">
                {ep.params && ep.params.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">Parameters</h4>
                    <table className="w-full text-sm">
                      <thead><tr className="border-b border-border">
                        <th className="py-1.5 text-left text-xs text-text-muted">Name</th>
                        <th className="py-1.5 text-left text-xs text-text-muted">Type</th>
                        <th className="py-1.5 text-left text-xs text-text-muted">Required</th>
                        <th className="py-1.5 text-left text-xs text-text-muted">Description</th>
                      </tr></thead>
                      <tbody>
                        {ep.params.map((p) => (
                          <tr key={p.name} className="border-b border-border last:border-0">
                            <td className="py-1.5 font-mono text-xs">{p.name}</td>
                            <td className="py-1.5 text-xs text-text-muted">{p.type}</td>
                            <td className="py-1.5 text-xs">{p.required ? 'Yes' : 'No'}</td>
                            <td className="py-1.5 text-xs text-text-secondary">{p.description}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">Response</h4>
                  <pre className="rounded-lg bg-bg-tertiary p-3 font-mono text-xs text-text-secondary overflow-x-auto">{ep.responseShape}</pre>
                </div>
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">Examples</h4>
                  <CodeTabs examples={ep.examples} />
                </div>
              </div>
            </details>
          ))}
        </div>
      </section>

      {/* WebSocket API */}
      <section className="mt-12">
        <h2 className="text-xl font-medium text-text-primary mb-2">WebSocket API</h2>
        <p className="text-sm text-text-secondary mb-4">
          Real-time streaming via WebSocket at <code className="font-mono text-accent-500">wss://api.pyhron.com/ws</code>. Connect, authenticate, then subscribe to channels.
        </p>
        <pre className="rounded-lg bg-bg-tertiary p-4 text-sm font-mono text-text-secondary overflow-x-auto">{`// 1. Connect
const ws = new WebSocket("wss://api.pyhron.com/ws");

// 2. Authenticate
ws.send(JSON.stringify({ type: "AUTH", token: accessToken }));
// Server responds: { "type": "AUTH_OK", "user_id": "...", "role": "TRADER" }

// 3. Subscribe to channels
ws.send(JSON.stringify({ type: "SUBSCRIBE", channel: "quotes", key: "BBCA" }));

// Available channels: quotes, orders, positions, signals, paper_nav
// Numeric values are JSON strings (Decimal precision) — parse with parseFloat()`}</pre>
      </section>

      {/* Python SDK */}
      <section className="mt-12">
        <h2 className="text-xl font-medium text-text-primary mb-4">Python SDK</h2>
        <div className="rounded-lg border border-border bg-bg-tertiary p-4">
          <pre className="text-sm font-mono text-text-secondary overflow-x-auto">{`pip install pyhron

from pyhron import Client

client = Client(api_key="your-api-key")
overview = client.market.overview()
print(f"IHSG: {overview.last_value} ({overview.change_pct:+.2f}%)")

# Screen stocks
results = client.screener.screen(sector="Financials", roe_min=15)
for stock in results:
    print(f"{stock.symbol}: P/E {stock.pe_ratio}, ROE {stock.roe}%")

# Backtest a strategy
bt = client.backtest.run(
    strategy="IDX Momentum", symbols=["BBCA", "BBRI", "TLKM"],
    start_date="2024-01-01", end_date="2025-12-31",
    initial_capital=1_000_000_000
)
print(f"Sharpe: {bt.metrics.sharpe_ratio}, Max DD: {bt.metrics.max_drawdown_pct}%")`}</pre>
        </div>
      </section>
    </div>
  );
}
