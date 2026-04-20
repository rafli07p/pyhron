export type TabKey = 'weight' | 'usd' | 'esg';

export type EsgRating = 'AAA' | 'AA' | 'A' | 'BBB' | 'BB' | 'B' | 'CCC';

export type IndexRow = {
  rank: number | null;
  indexCode: string;
  indexName: string;
  nextRebalancingDate: string | null;
  indexedAumMillionUsd: number | null;
  weights: Record<string, number | null>;
  isParent: boolean;
  esg?: {
    rating: EsgRating;
    carbonIntensity: number;
    esgQualityScore: number;
  };
};

export type PeerMember = {
  symbol: string;
  name: string;
  industry: string;
};

export type IndexMembershipResponse = {
  symbol: string;
  industry: string;
  asOfDate: string;
  availablePeers: PeerMember[];
  rows: IndexRow[];
};
