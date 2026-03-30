import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'API Documentation',
  description: 'Pyhron RESTful API reference for market data, screener, backtesting, and trading.',
};

const endpoints = [
  { method: 'GET', path: '/v1/market/overview', description: 'Market overview with IHSG level and market breadth' },
  { method: 'GET', path: '/v1/market/instruments', description: 'List all instruments with sector and market cap' },
  { method: 'GET', path: '/v1/market/ohlcv/:symbol', description: 'OHLCV bars for a given symbol' },
  { method: 'GET', path: '/v1/screener/screen', description: 'Screen stocks by fundamental and technical criteria' },
  { method: 'GET', path: '/v1/macro/indicators', description: 'Indonesian macro indicators (BI rate, GDP, CPI)' },
  { method: 'GET', path: '/v1/commodities/dashboard', description: 'Commodity prices (CPO, coal, nickel, tin)' },
  { method: 'GET', path: '/v1/bonds/government', description: 'Government bond yields and prices' },
  { method: 'GET', path: '/v1/strategies/', description: 'List all strategies' },
  { method: 'POST', path: '/v1/backtest/', description: 'Submit a backtest job' },
  { method: 'GET', path: '/v1/risk/:strategy_id/snapshot', description: 'Real-time risk snapshot' },
  { method: 'POST', path: '/v1/auth/login', description: 'Authenticate and get JWT tokens' },
  { method: 'POST', path: '/v1/auth/refresh', description: 'Refresh access token' },
];

export default function ApiDocsPage() {
  return (
    <div className="mx-auto max-w-content px-6 py-16 md:py-24">
      <h1 className="font-display text-4xl text-text-primary md:text-5xl">API Documentation</h1>
      <p className="mt-4 text-text-secondary">
        RESTful API for market data, screening, backtesting, and trading. Base URL: <code className="font-mono text-accent-500">https://api.pyhron.com/v1</code>
      </p>

      <section className="mt-12">
        <h2 className="text-xl font-medium text-text-primary mb-2">Authentication</h2>
        <p className="text-sm text-text-secondary mb-4">
          Authenticate via POST /v1/auth/login with email and password. Include the access token in the Authorization header.
        </p>
        <div className="rounded-lg border border-border bg-bg-secondary p-4">
          <pre className="text-sm font-mono text-text-secondary overflow-x-auto">
{`curl -X POST https://api.pyhron.com/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"email": "you@company.com", "password": "your-password"}'

# Response: { "access_token": "...", "refresh_token": "...", "expires_in": 3600 }

# Use the token:
curl https://api.pyhron.com/v1/market/overview \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"`}
          </pre>
        </div>
      </section>

      <section className="mt-12">
        <h2 className="text-xl font-medium text-text-primary mb-2">Rate Limits</h2>
        <p className="text-sm text-text-secondary">
          Free: 100 requests/day. Pro: 10,000 requests/day. Enterprise: Unlimited. Rate limit headers included in every response.
        </p>
      </section>

      <section className="mt-12">
        <h2 className="text-xl font-medium text-text-primary mb-4">Endpoints</h2>
        <div className="space-y-3">
          {endpoints.map((ep) => (
            <div key={ep.path} className="flex items-start gap-3 rounded-lg border border-border p-4">
              <span className={`rounded px-2 py-0.5 text-xs font-mono font-medium ${ep.method === 'GET' ? 'bg-positive/10 text-positive' : 'bg-warning/10 text-warning'}`}>
                {ep.method}
              </span>
              <div>
                <code className="text-sm font-mono text-text-primary">{ep.path}</code>
                <p className="mt-1 text-xs text-text-secondary">{ep.description}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-12">
        <h2 className="text-xl font-medium text-text-primary mb-4">Python SDK</h2>
        <div className="rounded-lg border border-border bg-bg-secondary p-4">
          <pre className="text-sm font-mono text-text-secondary overflow-x-auto">
{`pip install pyhron

from pyhron import Client

client = Client(api_key="your-api-key")
overview = client.market.overview()
print(f"IHSG: {overview.last_value} ({overview.change_pct:+.2f}%)")

# Screen stocks
results = client.screener.screen(sector="Financials", roe_min=15)
for stock in results:
    print(f"{stock.symbol}: P/E {stock.pe_ratio}, ROE {stock.roe}%")`}
          </pre>
        </div>
      </section>
    </div>
  );
}
