import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format, formatDistanceToNow } from 'date-fns';
import { Shield, CheckCircle, XCircle, Search } from 'lucide-react';
import { governanceApi } from '../../api/endpoints';
import type {
  GovernanceFlag,
  AuditOpinion,
} from '../../types';
import PageHeader from '../../components/common/PageHeader';
import Badge from '../../components/common/Badge';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import DataTable from '../../components/common/DataTable';
import type { Column } from '../../components/common/DataTable';

function severityColor(s: string): string {
  if (s === 'critical') return 'bg-red-500/15 text-red-400 border-red-500/30';
  if (s === 'high') return 'bg-orange-500/15 text-orange-400 border-orange-500/30';
  if (s === 'medium') return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
  if (s === 'low') return 'bg-blue-500/15 text-blue-400 border-blue-500/30';
  return 'bg-slate-500/15 text-slate-400 border-slate-500/30';
}

function opinionVariant(o: string): 'success' | 'warning' | 'danger' | 'neutral' {
  if (o === 'unqualified') return 'success';
  if (o === 'qualified') return 'warning';
  if (o === 'adverse' || o === 'disclaimer') return 'danger';
  return 'neutral';
}

function changeTypeVariant(t: string): 'success' | 'danger' | 'warning' | 'neutral' {
  if (t === 'acquisition') return 'success';
  if (t === 'disposal') return 'danger';
  if (t === 'dilution') return 'warning';
  return 'neutral';
}

function formatShares(val: number): string {
  if (Math.abs(val) >= 1_000_000_000) return (val / 1_000_000_000).toFixed(2) + 'B';
  if (Math.abs(val) >= 1_000_000) return (val / 1_000_000).toFixed(2) + 'M';
  if (Math.abs(val) >= 1_000) return (val / 1_000).toFixed(1) + 'K';
  return val.toLocaleString();
}

export default function GovernancePage() {
  const [flagSymbol, setFlagSymbol] = useState('');
  const [flagSeverity, setFlagSeverity] = useState('');
  const [flagResolved, setFlagResolved] = useState('');
  const [ownerSymbol, setOwnerSymbol] = useState('');
  const [searchedOwnerSymbol, setSearchedOwnerSymbol] = useState('');
  const [auditSymbol, setAuditSymbol] = useState('');
  const [searchedAuditSymbol, setSearchedAuditSymbol] = useState('');

  // Governance Flags
  const { data: flags, isLoading: loadingFlags } = useQuery({
    queryKey: ['gov-flags', flagSymbol, flagSeverity, flagResolved],
    queryFn: () =>
      governanceApi
        .flags({
          symbol: flagSymbol || undefined,
          severity: flagSeverity || undefined,
          resolved: flagResolved !== '' ? flagResolved === 'true' : undefined,
          limit: 50,
        })
        .then((r) => r.data),
  });

  // Ownership Changes
  const { data: ownership, isLoading: loadingOwnership } = useQuery({
    queryKey: ['gov-ownership', searchedOwnerSymbol],
    queryFn: () =>
      governanceApi
        .ownershipChanges(searchedOwnerSymbol, { limit: 30 })
        .then((r) => r.data),
    enabled: !!searchedOwnerSymbol,
  });

  // Audit Opinions
  const { data: audits, isLoading: loadingAudits } = useQuery({
    queryKey: ['gov-audits', searchedAuditSymbol],
    queryFn: () =>
      governanceApi
        .auditOpinions(searchedAuditSymbol, { limit: 10 })
        .then((r) => r.data),
    enabled: !!searchedAuditSymbol,
  });

  const flagColumns: Column[] = [
    { key: 'symbol', label: 'Symbol', sortable: true,
      render: (v: string) => <span className="font-medium text-slate-200">{v}</span>,
    },
    {
      key: 'flag_type',
      label: 'Type',
      sortable: true,
      render: (v: string) => (
        <span className="text-xs text-slate-400">{v.replace(/_/g, ' ')}</span>
      ),
    },
    {
      key: 'severity',
      label: 'Severity',
      sortable: true,
      render: (v: string) => (
        <span
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${severityColor(v)}`}
        >
          {v}
        </span>
      ),
    },
    {
      key: 'title',
      label: 'Title',
      render: (_v: string, row: GovernanceFlag) => (
        <div className="max-w-xs">
          <p className="text-sm text-slate-200">{row.title}</p>
          <p className="text-xs text-slate-500 mt-0.5 truncate">{row.description}</p>
        </div>
      ),
    },
    {
      key: 'detected_at',
      label: 'Detected',
      sortable: true,
      render: (v: string) => (
        <span className="text-xs text-slate-400" title={format(new Date(v), 'MMM dd, yyyy HH:mm')}>
          {formatDistanceToNow(new Date(v), { addSuffix: true })}
        </span>
      ),
    },
    {
      key: 'resolved',
      label: 'Resolved',
      sortable: true,
      render: (v: boolean) =>
        v ? (
          <span className="flex items-center gap-1 text-emerald-400 text-xs">
            <CheckCircle className="w-3.5 h-3.5" />
            Yes
          </span>
        ) : (
          <span className="flex items-center gap-1 text-red-400 text-xs">
            <XCircle className="w-3.5 h-3.5" />
            No
          </span>
        ),
    },
  ];

  const ownershipColumns: Column[] = [
    {
      key: 'holder_name',
      label: 'Holder',
      sortable: true,
      render: (v: string) => <span className="font-medium text-slate-200">{v}</span>,
    },
    {
      key: 'holder_type',
      label: 'Type',
      render: (v: string) => <Badge variant="neutral">{v}</Badge>,
    },
    {
      key: 'change_type',
      label: 'Change Type',
      sortable: true,
      render: (v: string) => <Badge variant={changeTypeVariant(v)}>{v}</Badge>,
    },
    {
      key: 'shares_before',
      label: 'Shares Before',
      align: 'right',
      sortable: true,
      render: (v: number) => formatShares(v),
    },
    {
      key: 'shares_after',
      label: 'Shares After',
      align: 'right',
      sortable: true,
      render: (v: number) => formatShares(v),
    },
    {
      key: 'change_pct',
      label: 'Change %',
      align: 'right',
      sortable: true,
      render: (v: number) => (
        <span
          className={`font-medium ${
            v > 0 ? 'text-emerald-400' : v < 0 ? 'text-red-400' : 'text-slate-400'
          }`}
        >
          {v > 0 ? '+' : ''}
          {v.toFixed(2)}%
        </span>
      ),
    },
    {
      key: 'transaction_date',
      label: 'Transaction',
      sortable: true,
      render: (v: string) => format(new Date(v), 'dd MMM yyyy'),
    },
    {
      key: 'reported_date',
      label: 'Reported',
      sortable: true,
      render: (v: string) => format(new Date(v), 'dd MMM yyyy'),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Governance Intelligence"
        subtitle="Corporate governance flags, ownership changes, and audit opinions"
      >
        <Shield className="h-5 w-5 text-slate-400" />
      </PageHeader>

      {/* Section 1: Governance Flags */}
      <div className="mb-8 p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
        <h3 className="text-sm font-semibold text-slate-100 mb-4">
          Governance Flags
        </h3>
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
            <input
              type="text"
              placeholder="Symbol"
              value={flagSymbol}
              onChange={(e) => setFlagSymbol(e.target.value.toUpperCase())}
              className="pl-9 pr-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 w-36"
            />
          </div>
          <select
            value={flagSeverity}
            onChange={(e) => setFlagSeverity(e.target.value)}
            className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500"
          >
            <option value="">All Severity</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <select
            value={flagResolved}
            onChange={(e) => setFlagResolved(e.target.value)}
            className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500"
          >
            <option value="">All Status</option>
            <option value="false">Unresolved</option>
            <option value="true">Resolved</option>
          </select>
        </div>
        <DataTable
          columns={flagColumns}
          data={flags || []}
          loading={loadingFlags}
          emptyMessage="No governance flags found."
        />
      </div>

      {/* Section 2: Ownership Changes */}
      <div className="mb-8 p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
        <h3 className="text-sm font-semibold text-slate-100 mb-4">
          Ownership Changes
        </h3>
        <div className="flex items-center gap-3 mb-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
            <input
              type="text"
              placeholder="Symbol (e.g. BBCA)"
              value={ownerSymbol}
              onChange={(e) => setOwnerSymbol(e.target.value.toUpperCase())}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && ownerSymbol.trim()) {
                  setSearchedOwnerSymbol(ownerSymbol.trim());
                }
              }}
              className="pl-9 pr-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 w-48"
            />
          </div>
          <button
            onClick={() => {
              if (ownerSymbol.trim()) setSearchedOwnerSymbol(ownerSymbol.trim());
            }}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            Search
          </button>
        </div>

        {!searchedOwnerSymbol ? (
          <p className="text-xs text-slate-500 text-center py-4">
            Enter a symbol and press Search to view ownership changes.
          </p>
        ) : (
          <DataTable
            columns={ownershipColumns}
            data={ownership || []}
            loading={loadingOwnership}
            emptyMessage={`No ownership changes found for ${searchedOwnerSymbol}.`}
          />
        )}
      </div>

      {/* Section 3: Audit Opinions */}
      <div className="p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
        <h3 className="text-sm font-semibold text-slate-100 mb-4">
          Audit Opinions
        </h3>
        <div className="flex items-center gap-3 mb-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
            <input
              type="text"
              placeholder="Symbol (e.g. BBCA)"
              value={auditSymbol}
              onChange={(e) => setAuditSymbol(e.target.value.toUpperCase())}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && auditSymbol.trim()) {
                  setSearchedAuditSymbol(auditSymbol.trim());
                }
              }}
              className="pl-9 pr-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 w-48"
            />
          </div>
          <button
            onClick={() => {
              if (auditSymbol.trim()) setSearchedAuditSymbol(auditSymbol.trim());
            }}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            Search
          </button>
        </div>

        {!searchedAuditSymbol ? (
          <p className="text-xs text-slate-500 text-center py-4">
            Enter a symbol and press Search to view audit opinions.
          </p>
        ) : loadingAudits ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner size="sm" label="Loading audit opinions..." />
          </div>
        ) : !audits || audits.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-4">
            No audit opinions found for {searchedAuditSymbol}.
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {audits.map((a: AuditOpinion, idx: number) => (
              <div
                key={idx}
                className="p-4 bg-slate-900/50 border border-slate-700/50 rounded-lg"
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="text-lg font-bold text-slate-100">
                    FY {a.fiscal_year}
                  </span>
                  <Badge variant={opinionVariant(a.opinion)}>{a.opinion}</Badge>
                </div>
                <p className="text-sm text-slate-400 mb-2">
                  Auditor: <span className="text-slate-300">{a.auditor}</span>
                </p>
                {a.going_concern && (
                  <div className="flex items-center gap-1.5 text-red-400 text-xs font-medium mb-2 p-2 bg-red-500/10 border border-red-500/20 rounded">
                    <XCircle className="w-3.5 h-3.5 shrink-0" />
                    Going Concern Warning
                  </div>
                )}
                {a.key_audit_matters.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
                      Key Audit Matters
                    </p>
                    <ul className="space-y-1.5">
                      {a.key_audit_matters.map((matter, j) => (
                        <li
                          key={j}
                          className="text-xs text-slate-400 pl-3 relative before:content-[''] before:absolute before:left-0 before:top-1.5 before:w-1.5 before:h-1.5 before:rounded-full before:bg-slate-600"
                        >
                          {matter}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <p className="text-xs text-slate-500 mt-3">
                  Report date: {format(new Date(a.report_date), 'dd MMM yyyy')}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
