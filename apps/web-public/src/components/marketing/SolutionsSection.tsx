'use client';

import { motion } from 'framer-motion';
import { BarChart3, Cpu, LineChart, Shield, Code, TrendingUp } from 'lucide-react';

const solutions = [
  {
    icon: BarChart3,
    title: 'Factor Models',
    description: 'Fama-French five-factor decomposition for 50+ IDX stocks. Value, momentum, quality, size, and low-volatility factors.',
  },
  {
    icon: Cpu,
    title: 'Algorithmic Trading',
    description: '5 pre-built strategies with backtesting. Event-driven engine with T+2 settlement and IDX lot size handling.',
  },
  {
    icon: LineChart,
    title: 'Index Products',
    description: 'Custom factor indices for IDX. Track composite, value, momentum, quality, and low-vol benchmarks.',
  },
  {
    icon: Shield,
    title: 'Risk Analytics',
    description: 'Real-time VaR (95/99%), stress testing, drawdown monitoring, and kill-switch protection.',
  },
  {
    icon: Code,
    title: 'Developer API',
    description: 'RESTful API with 15+ endpoints. Python SDK, WebSocket streaming, and Jupyter integration.',
  },
  {
    icon: TrendingUp,
    title: 'Market Intelligence',
    description: 'BI rate tracker, commodity-equity linkages, CPO/coal/nickel sensitivity analysis, and governance flags.',
  },
];

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' as const } },
};

export function SolutionsSection() {
  return (
    <section className="bg-bg-primary py-24 md:py-32">
      <div className="mx-auto max-w-content px-6">
        <h2 className="font-display text-3xl text-text-primary md:text-4xl">
          Built for quantitative analysis
        </h2>
        <p className="mt-4 max-w-2xl text-text-secondary">
          End-to-end platform covering factor research, strategy backtesting, live execution, and risk management for the Indonesia Stock Exchange.
        </p>
        <motion.div
          className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.2 }}
        >
          {solutions.map((sol) => (
            <motion.div
              key={sol.title}
              variants={itemVariants}
              className="group rounded-lg border border-border bg-bg-secondary p-6 transition-colors hover:border-accent-500"
            >
              <sol.icon className="h-8 w-8 text-accent-500" />
              <h3 className="mt-4 text-lg font-medium text-text-primary">{sol.title}</h3>
              <p className="mt-2 text-sm text-text-secondary">{sol.description}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
