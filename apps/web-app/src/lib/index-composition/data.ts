import type { IndexRow, PeerMember } from './types';

export const AVAILABLE_PEERS: PeerMember[] = [
  { symbol: 'BBCA', name: 'Bank Central Asia Tbk', industry: 'Banks' },
  { symbol: 'BMRI', name: 'Bank Mandiri Tbk', industry: 'Banks' },
  { symbol: 'BBRI', name: 'Bank Rakyat Indonesia Tbk', industry: 'Banks' },
  { symbol: 'BBNI', name: 'Bank Negara Indonesia Tbk', industry: 'Banks' },
  { symbol: 'BRIS', name: 'Bank Syariah Indonesia Tbk', industry: 'Banks' },
  { symbol: 'BTPS', name: 'BTPN Syariah Tbk', industry: 'Banks' },
  { symbol: 'ARTO', name: 'Bank Jago Tbk', industry: 'Banks' },
  { symbol: 'BBTN', name: 'Bank Tabungan Negara Tbk', industry: 'Banks' },
  { symbol: 'BNGA', name: 'Bank CIMB Niaga Tbk', industry: 'Banks' },
];

export const DEFAULT_PEER_SYMBOLS = ['BBCA', 'BMRI', 'BBRI', 'BBNI'];

export const AS_OF_DATES = [
  '2025-09-30',
  '2025-06-30',
  '2025-03-31',
  '2024-12-31',
  '2024-09-30',
];

export const BBCA_INDEX_ROWS: IndexRow[] = [
  {
    rank: null, indexCode: '664204', indexName: 'MSCI Indonesia IMI',
    nextRebalancingDate: null, indexedAumMillionUsd: null, isParent: true,
    weights: { BBCA: 1, BMRI: 1, BBRI: 1, BBNI: 1, BRIS: 1, BTPS: 1, ARTO: 1, BBTN: 1, BNGA: 1 },
  },
  {
    rank: null, indexCode: '892400', indexName: 'MSCI Indonesia',
    nextRebalancingDate: null, indexedAumMillionUsd: null, isParent: true,
    weights: { BBCA: 1, BMRI: 1, BBRI: 1, BBNI: 1 },
  },
  {
    rank: 1, indexCode: '723912', indexName: 'MSCI Indonesia ESG Enhanced Focus CTB',
    nextRebalancingDate: '2025-11-28', indexedAumMillionUsd: 145, isParent: false,
    weights: { BBCA: 22.85, BMRI: 15.23, BBRI: 12.41, BBNI: 8.67, BRIS: 2.15 },
    esg: { rating: 'AA', carbonIntensity: 68, esgQualityScore: 7.8 },
  },
  {
    rank: 2, indexCode: '721417', indexName: 'MSCI Indonesia ESG Screened',
    nextRebalancingDate: '2025-11-28', indexedAumMillionUsd: 89, isParent: false,
    weights: { BBCA: 24.12, BMRI: 16.08, BBRI: 13.15, BBNI: 9.12, BRIS: 2.34 },
    esg: { rating: 'AA', carbonIntensity: 72, esgQualityScore: 7.5 },
  },
  {
    rank: 3, indexCode: '719471', indexName: 'MSCI Indonesia Extended ESG Focus',
    nextRebalancingDate: '2025-11-28', indexedAumMillionUsd: 67, isParent: false,
    weights: { BBCA: 20.74, BMRI: 14.56, BBRI: 11.83, BBNI: 7.95 },
    esg: { rating: 'AAA', carbonIntensity: 52, esgQualityScore: 8.4 },
  },
  {
    rank: 4, indexCode: '717287', indexName: 'MSCI Indonesia Low Carbon SRI Selection',
    nextRebalancingDate: '2025-11-28', indexedAumMillionUsd: 42, isParent: false,
    weights: { BBCA: 26.38, BMRI: 17.22, BBRI: null, BBNI: null, BRIS: 4.21 },
    esg: { rating: 'AAA', carbonIntensity: 38, esgQualityScore: 8.9 },
  },
  {
    rank: 5, indexCode: '721415', indexName: 'MSCI Indonesia ESG Leaders',
    nextRebalancingDate: '2025-11-28', indexedAumMillionUsd: 312, isParent: false,
    weights: { BBCA: 18.92, BMRI: 12.84, BBRI: 10.47, BBNI: 7.23 },
    esg: { rating: 'AA', carbonIntensity: 78, esgQualityScore: 7.2 },
  },
  {
    rank: 6, indexCode: '700719', indexName: 'MSCI Indonesia SRI Select',
    nextRebalancingDate: '2025-11-28', indexedAumMillionUsd: 28, isParent: false,
    weights: { BBCA: 28.15, BMRI: 18.74, BBRI: null, BBNI: null },
    esg: { rating: 'AAA', carbonIntensity: 45, esgQualityScore: 8.6 },
  },
  {
    rank: 7, indexCode: '734908', indexName: 'MSCI Indonesia SRI Low Carbon Select 5% Issuer Cap',
    nextRebalancingDate: '2025-11-28', indexedAumMillionUsd: 18, isParent: false,
    weights: { BBCA: 5.00, BMRI: 5.00, BBRI: 4.87, BBNI: null },
    esg: { rating: 'AAA', carbonIntensity: 35, esgQualityScore: 9.1 },
  },
];
