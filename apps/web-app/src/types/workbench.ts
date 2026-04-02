export interface WorkbenchOverlay {
  metric: string;
  params: Record<string, number>;
  axis: 'primary' | 'secondary' | 'panel';
}

export interface WorkbenchTransform {
  fn: string;
  target: string;
  params: Record<string, number>;
}

export interface WorkbenchState {
  base: string;
  compare: string[];
  timeframe: string;
  range: string;
  overlays: WorkbenchOverlay[];
  transforms: WorkbenchTransform[];
  scale: 'linear' | 'log';
  normalize: boolean;
}

export interface WorkbenchPreset {
  id: string;
  name: string;
  state: WorkbenchState;
  curated: boolean;
  userId?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ChartAnnotation {
  id: string;
  chartId: string;
  userId: string;
  timestamp: number;
  price?: number;
  text: string;
  color: string;
  visibility: 'private' | 'team' | 'public';
  createdAt: string;
  updatedAt: string;
}
