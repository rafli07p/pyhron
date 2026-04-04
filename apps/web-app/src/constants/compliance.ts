export const COMPLIANCE = {
  platformName: 'Pyhron' as const,
  platformType: 'Quantitative research and algorithmic trading platform' as const,
  jurisdiction: 'Indonesia' as const,

  regulatoryStatus: {
    isRegisteredBroker: false,
    isRegisteredAdvisor: false,
    regulatoryBody: 'OJK (Otoritas Jasa Keuangan)',
    statement:
      'Pyhron tidak terdaftar sebagai perantara pedagang efek, penasihat investasi, ' +
      'atau perantara lainnya di Otoritas Jasa Keuangan (OJK) maupun Bursa Efek Indonesia (IDX). ' +
      'Pyhron adalah platform riset kuantitatif dan eksekusi order diteruskan ke broker pihak ketiga.',
    statementEn:
      'Pyhron is NOT registered as a broker-dealer, investment adviser, or securities intermediary ' +
      'with the Indonesian Financial Services Authority (OJK) or the Indonesia Stock Exchange (IDX). ' +
      'Pyhron is a quantitative research platform. Order execution is routed through third-party brokers.',
  },

  liveTradeAcknowledgments: [
    {
      id: 'risk_of_loss',
      textId:
        'Saya memahami bahwa trading algoritmik melibatkan risiko kerugian substansial, termasuk kemungkinan kehilangan seluruh modal.',
      textEn:
        'I understand that algorithmic trading involves substantial risk of loss, including the possibility of losing all capital.',
    },
    {
      id: 'past_performance',
      textId:
        'Saya memahami bahwa performa masa lalu (termasuk hasil backtest dan paper trading) tidak menjamin hasil di masa depan.',
      textEn:
        'I understand that past performance (including backtest and paper trading results) does not guarantee future results.',
    },
    {
      id: 'not_advice',
      textId:
        'Saya memahami bahwa Pyhron bukan penasihat investasi dan sinyal ML bukan rekomendasi investasi.',
      textEn:
        'I understand that Pyhron is not an investment adviser and ML signals are not investment recommendations.',
    },
    {
      id: 'sole_responsibility',
      textId:
        'Saya bertanggung jawab penuh atas semua keputusan trading dan kerugian yang mungkin timbul.',
      textEn:
        'I am solely responsible for all trading decisions and any losses that may result.',
    },
    {
      id: 'system_risk',
      textId:
        'Saya memahami bahwa sistem trading otomatis dapat mengalami kegagalan teknis, latensi, atau perilaku tak terduga.',
      textEn:
        'I understand that automated trading systems may experience technical failures, latency, or unexpected behavior.',
    },
    {
      id: 'terms_acceptance',
      textId:
        'Saya telah membaca dan menyetujui Terms of Service, Risk Disclosure, dan Privacy Policy Pyhron.',
      textEn:
        "I have read and agree to Pyhron's Terms of Service, Risk Disclosure, and Privacy Policy.",
    },
  ],

  algoOrderRequiredFields: [
    'strategy_id',
    'signal_id',
    'risk_check_passed',
    'guardrail_snapshot',
    'user_tier',
  ],

  auditRetentionDays: 365 * 7,
  maxLeverage: 1.0,

  paperDisclaimer:
    'Paper trading menggunakan data pasar nyata tetapi eksekusi bersifat simulasi. ' +
    'Hasil paper trading tidak memperhitungkan slippage nyata, market impact, atau ' +
    'kemungkinan order gagal tereksekusi. Performa paper trading mungkin berbeda ' +
    'secara signifikan dari trading live.',
  paperDisclaimerEn:
    'Paper trading uses real market data but execution is simulated. Paper trading results ' +
    'do not account for real slippage, market impact, or the possibility of failed order ' +
    'execution. Paper trading performance may differ significantly from live trading.',
  dataPrivacy: {
    applicableLaw: 'UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi',
    userRights: [
      'right_to_access',
      'right_to_rectification',
      'right_to_deletion',
      'right_to_restriction',
      'right_to_portability',
      'right_to_object',
      'right_to_withdraw_consent',
    ],
    retention: {
      accountData: 'Active account + 30 days after deletion request',
      tradingHistory: '7 years (Indonesian tax requirement)',
      auditLogs: '7 years',
      analyticsData: '24 months (anonymized after 6 months)',
    },
    exportFormats: ['json', 'csv'] as const,
  },
} as const;
