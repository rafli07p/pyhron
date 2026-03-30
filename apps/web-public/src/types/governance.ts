export interface GovernanceFlag {
  id: string;
  symbol: string;
  flag_type: string;
  severity: string;
  title: string;
  description: string;
  source: string | null;
  detected_at: string;
  resolved: boolean;
}

export interface OwnershipChange {
  symbol: string;
  holder_name: string;
  holder_type: string;
  change_type: string;
  shares_before: number;
  shares_after: number;
  change_pct: number;
  transaction_date: string;
  reported_date: string | null;
}

export interface AuditOpinion {
  symbol: string;
  fiscal_year: number;
  auditor: string;
  opinion: string;
  key_audit_matters: string[];
  going_concern: boolean;
  report_date: string | null;
}
