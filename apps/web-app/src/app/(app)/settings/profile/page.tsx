import { PageHeader } from '@/design-system/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';
import { Button } from '@/design-system/primitives/Button';
import { Input } from '@/design-system/primitives/Input';

export const metadata = { title: 'Profile' };

export default function ProfilePage() {
  return (
    <div className="max-w-2xl space-y-6">
      <PageHeader title="Profile" description="Manage your account settings" />
      <Card>
        <CardHeader><CardTitle>Personal Information</CardTitle></CardHeader>
        <CardContent>
          <form className="space-y-4">
            <Input label="Full Name" defaultValue="John Doe" />
            <Input label="Email" type="email" defaultValue="john@example.com" disabled />
            <Input label="Phone" type="tel" placeholder="+62" />
            <Button type="submit">Save Changes</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
