import { redirect } from 'next/navigation';
import { auth } from '@/lib/auth';
import { AppShell } from '@/design-system/layout/AppShell';
import { DegradedBanner } from '@/design-system/layout/DegradedBanner';

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();

  if (!session) {
    redirect('/login');
  }

  return (
    <>
      <DegradedBanner />
      <AppShell>{children}</AppShell>
    </>
  );
}
