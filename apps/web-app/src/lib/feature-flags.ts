import { create } from 'zustand';

interface FeatureFlags {
  enableLiveTrading: boolean;
  enableMLPipeline: boolean;
  enableStrategyBuilder: boolean;
  enableDataExplorer: boolean;
  enableAlgoExecution: boolean;
  enableCustomScenarios: boolean;
  showBetaBadges: boolean;
  maintenanceMode: boolean;
  maintenanceMessage: string;
}

const DEFAULT_FLAGS: FeatureFlags = {
  enableLiveTrading: false,
  enableMLPipeline: false,
  enableStrategyBuilder: false,
  enableDataExplorer: false,
  enableAlgoExecution: false,
  enableCustomScenarios: false,
  showBetaBadges: true,
  maintenanceMode: false,
  maintenanceMessage: '',
};

interface FeatureFlagStore {
  flags: FeatureFlags;
  setFlags: (flags: Partial<FeatureFlags>) => void;
}

export const useFeatureFlagStore = create<FeatureFlagStore>((set) => ({
  flags: DEFAULT_FLAGS,
  setFlags: (newFlags) => set((s) => ({ flags: { ...s.flags, ...newFlags } })),
}));

export function useFeatureFlag(flag: keyof FeatureFlags): boolean {
  return useFeatureFlagStore((s) => !!s.flags[flag]);
}
