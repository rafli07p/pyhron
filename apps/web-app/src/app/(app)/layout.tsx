import { redirect } from 'next/navigation';
import { auth } from '@/lib/auth';
import { AppShell } from '@/design-system/layout/AppShell';

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();

  if (!session) {
    redirect('/login');
  }

  return <AppShell>{children}</AppShell>;
}
