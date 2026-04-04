export interface CorporateAction {
  id: string;
  symbol: string;
  type:
    | 'stock_split'
    | 'reverse_split'
    | 'rights_issue'
    | 'dividend_cash'
    | 'dividend_stock'
    | 'bonus_shares'
    | 'merger'
    | 'delisting'
    | 'relisting';
  exDate: string;
  recordDate: string;
  paymentDate?: string;
  ratio?: string;
  amount?: number;
  adjustmentFactor?: number;
  description: string;
  status: 'announced' | 'ex_date' | 'completed';
  createdAt: string;
}
