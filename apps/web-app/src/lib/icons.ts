/**
 * Centralized icon mapping.
 *
 * All icons used throughout the app are routed through this single map. Rather
 * than importing from `lucide-react` inline across components, import from
 * here:
 *
 *   import { Icons } from '@/lib/icons';
 *   <Icons.Terminal className="h-4 w-4" />
 *
 * To swap any icon with a custom SVG later, replace the value in the `Icons`
 * object below with your own React component — as long as it satisfies the
 * `LucideIcon` (or compatible) signature, nothing else in the codebase needs
 * to change. Example:
 *
 *   import { MyCustomTerminal } from '@/components/icons/MyCustomTerminal';
 *   export const Icons = {
 *     Terminal: MyCustomTerminal,
 *     ...
 *   };
 */

import {
  Activity,
  ArrowUpDown,
  BarChart3,
  Bell,
  BookOpen,
  Brain,
  Building2,
  ChevronDown,
  Database,
  Download,
  ExternalLink,
  FileText,
  Filter,
  Globe,
  Layers,
  LineChart,
  Lock,
  type LucideIcon,
  Menu,
  PieChart,
  Search,
  Settings,
  Shield,
  Target,
  TrendingUp,
  Users,
  X,
  Zap,
} from 'lucide-react';

export const Icons = {
  // Product surfaces
  Terminal: BarChart3,
  Workbench: LineChart,
  Execution: Zap,
  Portfolio: PieChart,
  MarketData: TrendingUp,
  Factors: Layers,
  Fundamentals: Database,

  // Concepts
  Research: Brain,
  Target,
  Risk: Shield,
  Compliance: Lock,
  Coverage: Globe,
  Activity,

  // UI actions
  Search,
  Settings,
  Notifications: Bell,
  Docs: FileText,
  Guides: BookOpen,
  Team: Users,
  Company: Building2,
  ChevronDown,
  Close: X,
  Menu,
  ExternalLink,
  Download,
  Filter,
  Sort: ArrowUpDown,
} as const satisfies Record<string, LucideIcon>;

export type IconName = keyof typeof Icons;
