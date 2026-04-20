import { create } from 'zustand';

interface CompanyStore {
  selectedSymbol: string;
  selectedName: string;
  setSelected: (symbol: string, name: string) => void;
}

export const useCompanyStore = create<CompanyStore>((set) => ({
  selectedSymbol: 'BBCA',
  selectedName: 'Bank Central Asia Tbk',
  setSelected: (symbol, name) => set({ selectedSymbol: symbol, selectedName: name }),
}));
