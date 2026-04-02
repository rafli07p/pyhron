import { authHandlers } from './auth';
import { marketHandlers } from './market';
import { portfolioHandlers } from './portfolio';
import { strategyHandlers } from './strategy';
import { researchHandlers } from './research';
import { riskHandlers } from './risk';
import { backtestHandlers } from './backtest';
import { screenerHandlers } from './screener';

export const handlers = [
  ...authHandlers,
  ...marketHandlers,
  ...portfolioHandlers,
  ...strategyHandlers,
  ...researchHandlers,
  ...riskHandlers,
  ...backtestHandlers,
  ...screenerHandlers,
];
