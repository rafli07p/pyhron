'use client';

import Link from 'next/link';
import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Badge } from '@/design-system/primitives/Badge';
import { Button } from '@/design-system/primitives/Button';
import { StatCard } from '@/design-system/data-display/StatCard';
import { useTierGate } from '@/hooks/useTierGate';
import type { QualificationStatus } from '@/types/tier';
import {
  Wifi,
  Play,
  TrendingUp,
  Shield,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
} from 'lucide-react';

const SAMPLE_QUALIFICATION: QualificationStatus = {
  accountAgeDays: 45,
  paperTradingDays: 37,
  paperTradesCount: 84,
  strategiesDeployed: 2,
  emailVerified: true,
  kycCompleted: false,
  onboardingCallCompleted: false,
  guardrailsConfigured: false,
  progressPercent: 0,
  meetsAutoRequirements: false,
};

// Compute progress
function computeProgress(q: QualificationStatus): number {
  const checks = [
    q.accountAgeDays >= 30,
    q.paperTradingDays >= 30,
    q.paperTradesCount >= 50,
    q.strategiesDeployed >= 1,
    q.emailVerified,
    q.kycCompleted,
    q.onboardingCallCompleted,
    q.guardrailsConfigured,
  ];
  return Math.round((checks.filter(Boolean).length / checks.length) * 100);
}

function QualificationCheckItem({
  label,
  met,
  detail,
}: {
  label: string;
  met: boolean;
  detail: string;
}) {
  return (
    <div className="flex items-center justify-between rounded-md px-3 py-2 hover:bg-[var(--surface-3)]">
      <div className="flex items-center gap-2">
        {met ? (
          <CheckCircle2 className="h-4 w-4 text-[var(--positive)]" />
        ) : (
          <XCircle className="h-4 w-4 text-[var(--text-tertiary)]" />
        )}
        <span className="text-sm text-[var(--text-primary)]">{label}</span>
      </div>
      <span className="text-xs text-[var(--text-tertiary)]">{detail}</span>
    </div>
  );
}

export default function ExecutionPage() {
  const { hasAccess: hasOperatorAccess } = useTierGate('execution.live');
  const qual = { ...SAMPLE_QUALIFICATION, progressPercent: computeProgress(SAMPLE_QUALIFICATION) };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Execution"
        description="Paper trading, live trading, and execution management"
      />

      {/* Paper Trading Section */}
      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
          Paper Trading
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Connection"
            value="Connected"
            delta="Alpaca Paper"
            deltaType="positive"
            icon={Wifi}
          />
          <StatCard
            label="Active Strategies"
            value="2"
            delta="MomentumIDX, PairsTrade"
            deltaType="neutral"
            icon={Play}
          />
          <StatCard
            label="Paper P&L (MTD)"
            value="+IDR 3.456.789"
            delta="+2.8%"
            deltaType="positive"
            icon={TrendingUp}
          />
          <StatCard
            label="Paper Trades"
            value="84"
            delta="37 days active"
            deltaType="neutral"
            icon={Clock}
          />
        </div>
      </div>

      {/* Live Trading Section */}
      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
          Live Trading
        </h2>

        {hasOperatorAccess ? (
          /* Operator live dashboard */
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Live Connection"
              value="Connected"
              delta="Broker: Active"
              deltaType="positive"
              icon={Wifi}
            />
            <StatCard
              label="Live Strategies"
              value="1"
              delta="MomentumIDX"
              deltaType="neutral"
              icon={Play}
            />
            <StatCard
              label="Live P&L (MTD)"
              value="+IDR 8.765.432"
              delta="+4.1%"
              deltaType="positive"
              icon={TrendingUp}
            />
            <StatCard
              label="Risk Status"
              value="Normal"
              delta="All guardrails OK"
              deltaType="positive"
              icon={Shield}
            />
          </div>
        ) : (
          /* Non-operator: qualification progress */
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Qualification Progress</CardTitle>
                <Badge variant={qual.progressPercent === 100 ? 'positive' : 'warning'}>
                  {qual.progressPercent}% complete
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="mb-4">
                <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--surface-3)]">
                  <div
                    className="h-full rounded-full bg-[var(--accent-500)] transition-all"
                    style={{ width: `${qual.progressPercent}%` }}
                  />
                </div>
              </div>

              <div className="space-y-1">
                <QualificationCheckItem
                  label="Account Age"
                  met={qual.accountAgeDays >= 30}
                  detail={`${qual.accountAgeDays} / 30 days`}
                />
                <QualificationCheckItem
                  label="Paper Trading Days"
                  met={qual.paperTradingDays >= 30}
                  detail={`${qual.paperTradingDays} / 30 days`}
                />
                <QualificationCheckItem
                  label="Paper Trades"
                  met={qual.paperTradesCount >= 50}
                  detail={`${qual.paperTradesCount} / 50 trades`}
                />
                <QualificationCheckItem
                  label="Strategies Deployed"
                  met={qual.strategiesDeployed >= 1}
                  detail={`${qual.strategiesDeployed} deployed`}
                />
                <QualificationCheckItem
                  label="Email Verified"
                  met={qual.emailVerified}
                  detail={qual.emailVerified ? 'Verified' : 'Not verified'}
                />
                <QualificationCheckItem
                  label="KYC Completed"
                  met={qual.kycCompleted}
                  detail={qual.kycCompleted ? 'Completed' : 'Not completed'}
                />
                <QualificationCheckItem
                  label="Onboarding Call"
                  met={qual.onboardingCallCompleted}
                  detail={qual.onboardingCallCompleted ? 'Completed' : 'Not scheduled'}
                />
                <QualificationCheckItem
                  label="Guardrails Configured"
                  met={qual.guardrailsConfigured}
                  detail={qual.guardrailsConfigured ? 'Configured' : 'Not configured'}
                />
              </div>

              <div className="mt-6 flex gap-3">
                <Link href="/execution/request-access">
                  <Button size="sm">
                    Request Live Access
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
                <Link href="/execution/guardrails">
                  <Button variant="outline" size="sm">
                    <Shield className="h-4 w-4" />
                    View Guardrails
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
