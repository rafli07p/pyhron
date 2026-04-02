'use client';

import * as TabsPrimitive from '@radix-ui/react-tabs';
import { forwardRef } from 'react';
import { cn } from '@/lib/utils';

const Tabs = TabsPrimitive.Root;

const TabsList = forwardRef<
  React.ComponentRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(
      'inline-flex h-9 items-center gap-1 rounded-lg bg-[var(--surface-2)] p-1',
      className,
    )}
    {...props}
  />
));
TabsList.displayName = TabsPrimitive.List.displayName;

const TabsTrigger = forwardRef<
  React.ComponentRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      'inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-xs font-medium text-[var(--text-secondary)] transition-all',
      'hover:text-[var(--text-primary)]',
      'data-[state=active]:bg-[var(--surface-0)] data-[state=active]:text-[var(--text-primary)] data-[state=active]:shadow-sm',
      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-500)]',
      'disabled:pointer-events-none disabled:opacity-50',
      className,
    )}
    {...props}
  />
));
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;

const TabsContent = forwardRef<
  React.ComponentRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      'mt-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-500)]',
      className,
    )}
    {...props}
  />
));
TabsContent.displayName = TabsPrimitive.Content.displayName;

export { Tabs, TabsList, TabsTrigger, TabsContent };
