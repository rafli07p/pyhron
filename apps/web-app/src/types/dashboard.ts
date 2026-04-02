export interface DashboardTile {
  id: string;
  type:
    | 'chart'
    | 'stat_card'
    | 'data_table'
    | 'heatmap'
    | 'markdown'
    | 'signal_card'
    | 'equity_curve'
    | 'alert_feed'
    | 'data_freshness';
  title: string;
  config: Record<string, unknown>;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface CustomDashboard {
  id: string;
  name: string;
  description?: string;
  tiles: DashboardTile[];
  visibility: 'private' | 'team' | 'public';
  curated: boolean;
  createdAt: string;
  updatedAt: string;
}
