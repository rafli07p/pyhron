import type { Metadata } from 'next';
import { ContactForm } from '@/components/marketing/ContactForm';

export const metadata: Metadata = {
  title: 'Contact',
  description: 'Get in touch with the Pyhron team.',
};

export default function ContactPage() {
  return (
    <div className="mx-auto max-w-content px-6 py-16 md:py-24">
      <div className="grid gap-12 lg:grid-cols-2">
        <div>
          <h1 className="font-display text-4xl text-text-primary md:text-5xl">Contact Us</h1>
          <p className="mt-4 text-text-secondary">
            Questions about our platform, pricing, or API? Reach out and we will respond within one business day.
          </p>
          <div className="mt-8 space-y-4">
            <div>
              <h3 className="text-sm font-medium text-text-muted">General Inquiries</h3>
              <p className="text-text-secondary">info@pyhron.com</p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-muted">Technical Support</h3>
              <p className="text-text-secondary">support@pyhron.com</p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-muted">Enterprise Sales</h3>
              <p className="text-text-secondary">enterprise@pyhron.com</p>
            </div>
          </div>
        </div>
        <ContactForm />
      </div>
    </div>
  );
}
