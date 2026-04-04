'use client';

import { useState, type FormEvent } from 'react';

export default function ContactPage() {
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitted(true);
  }

  const inputClass =
    'flex h-9 w-full rounded-md border border-white/[0.08] bg-[#0f0f12] px-3 py-1 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-500)]';
  const labelClass = 'block text-xs font-medium text-[var(--text-secondary)] mb-1.5';

  return (
    <div className="py-20">
      <div className="mx-auto grid max-w-6xl gap-12 px-6 md:grid-cols-5">
        {/* Left */}
        <div className="md:col-span-2">
          <h1 className="text-3xl font-bold text-[var(--text-primary)]">Get in Touch</h1>
          <p className="mt-3 text-sm leading-relaxed text-[var(--text-secondary)]">
            Interested in Pyhron for your institution? Schedule a demo, request API access, or ask us anything about the platform.
          </p>

          <div className="mt-10 space-y-6">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Email</p>
              <p className="mt-1 text-sm text-[var(--text-primary)]">contact@pyhron.com</p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Location</p>
              <p className="mt-1 text-sm text-[var(--text-primary)]">Jakarta, Indonesia</p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Links</p>
              <div className="mt-1 flex gap-4 text-sm text-[var(--text-secondary)]">
                <a href="https://github.com/pyhron" className="hover:text-[var(--text-primary)]">GitHub</a>
                <a href="https://linkedin.com/company/pyhron" className="hover:text-[var(--text-primary)]">LinkedIn</a>
                <a href="https://twitter.com/pyhron" className="hover:text-[var(--text-primary)]">Twitter</a>
              </div>
            </div>
          </div>
        </div>

        {/* Right */}
        <div className="md:col-span-3">
          {submitted ? (
            <div className="flex h-full items-center justify-center rounded-xl border border-[var(--border-default)] bg-[var(--surface-1)] p-12">
              <div className="text-center">
                <p className="text-lg font-semibold text-[var(--text-primary)]">Message sent</p>
                <p className="mt-2 text-sm text-[var(--text-secondary)]">
                  We&apos;ll get back to you within 1-2 business days.
                </p>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="rounded-xl border border-[var(--border-default)] bg-[var(--surface-1)] p-8">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="first-name" className={labelClass}>First Name</label>
                  <input id="first-name" name="firstName" required placeholder="Jane" className={inputClass} />
                </div>
                <div>
                  <label htmlFor="last-name" className={labelClass}>Last Name</label>
                  <input id="last-name" name="lastName" required placeholder="Doe" className={inputClass} />
                </div>
              </div>

              <div className="mt-4">
                <label htmlFor="email" className={labelClass}>Business Email</label>
                <input id="email" name="email" type="email" required placeholder="jane@institution.com" className={inputClass} />
              </div>

              <div className="mt-4">
                <label htmlFor="institution-type" className={labelClass}>Institution Type</label>
                <select id="institution-type" name="institutionType" required className={inputClass} defaultValue="">
                  <option value="" disabled>Select type</option>
                  <option value="asset-manager">Asset Manager</option>
                  <option value="hedge-fund">Hedge Fund</option>
                  <option value="bank">Bank / Securities</option>
                  <option value="family-office">Family Office</option>
                  <option value="proprietary">Proprietary Trading</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div className="mt-4">
                <label htmlFor="subject" className={labelClass}>Subject</label>
                <select id="subject" name="subject" required className={inputClass} defaultValue="">
                  <option value="" disabled>Select subject</option>
                  <option value="demo">Schedule a Demo</option>
                  <option value="api">API Access</option>
                  <option value="enterprise">Enterprise Pricing</option>
                  <option value="partnership">Partnership</option>
                  <option value="general">General Inquiry</option>
                </select>
              </div>

              <div className="mt-4">
                <label htmlFor="message" className={labelClass}>Message</label>
                <textarea
                  id="message"
                  name="message"
                  required
                  rows={5}
                  placeholder="Tell us about your needs..."
                  className={`${inputClass} min-h-[120px] py-2`}
                />
              </div>

              <button
                type="submit"
                className="mt-6 inline-flex h-10 w-full items-center justify-center rounded-md bg-[var(--accent-500)] px-6 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-600)]"
              >
                Send Message
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
