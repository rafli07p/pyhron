import { Button } from '@/design-system/primitives/Button';
import { Input } from '@/design-system/primitives/Input';
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/primitives/Card';

export const metadata = { title: 'Contact' };

export default function ContactPage() {
  return (
    <div className="mx-auto max-w-lg px-6 py-20">
      <h1 className="text-center text-3xl font-bold text-[var(--text-primary)]">Contact Us</h1>
      <p className="mt-2 text-center text-sm text-[var(--text-secondary)]">
        Schedule a demo or ask us anything
      </p>
      <Card className="mt-8">
        <CardContent className="pt-6">
          <form className="space-y-4">
            <Input label="Name" placeholder="Your name" />
            <Input label="Email" type="email" placeholder="you@company.com" />
            <Input label="Company" placeholder="Company name" />
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--text-secondary)]">Message</label>
              <textarea
                className="flex min-h-24 w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-500)]"
                placeholder="Tell us about your needs..."
              />
            </div>
            <Button type="submit" className="w-full">Send Message</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
