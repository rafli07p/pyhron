'use client';

import { useState, type FormEvent } from 'react';
import Link from 'next/link';

export default function ContactPage() {
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitted(true);
  }

  const inputClass =
    'w-full border-b border-[var(--border-default)] bg-transparent py-3 text-[15px] text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:border-[#2563eb] focus:outline-none';
  const labelClass = 'block text-[14px] text-[var(--text-tertiary)] mb-1';

  return (
    <div className="py-24">
      <div className="mx-auto max-w-[700px] px-6">
        <h1 className="text-4xl font-semibold text-[#2563eb]">Contact Sales</h1>
        <p className="mt-4 text-[15px] leading-relaxed text-[var(--text-secondary)]">
          Fill out the form so we may connect you with a sales expert who
          understands your industry and interests.
        </p>
        <Link href="/status" className="mt-2 inline-block text-[14px] text-[var(--text-tertiary)] underline underline-offset-2 hover:text-[var(--text-primary)]">
          Need service or support? Get help here
        </Link>

        {submitted ? (
          <div className="mt-12 rounded-lg border border-[var(--border-default)] bg-[var(--surface-1)] p-8 text-center">
            <p className="text-lg font-semibold text-[var(--text-primary)]">Thank you</p>
            <p className="mt-2 text-sm text-[var(--text-secondary)]">
              We&apos;ll respond within 1-2 business days.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-12 space-y-8">
            <div>
              <label className={labelClass}>Interest *</label>
              <select required className={inputClass + ' cursor-pointer'}>
                <option value="">Select...</option>
                <option>Asset Management</option>
                <option>Hedge Fund</option>
                <option>Proprietary Trading</option>
                <option>Research</option>
                <option>Academic</option>
                <option>Individual</option>
                <option>Other</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className={labelClass}>First Name *</label>
                <input required type="text" className={inputClass} placeholder="First name" />
              </div>
              <div>
                <label className={labelClass}>Last Name *</label>
                <input required type="text" className={inputClass} placeholder="Last name" />
              </div>
            </div>

            <div>
              <label className={labelClass}>Email address *</label>
              <input required type="email" className={inputClass} placeholder="you@company.com" />
            </div>

            <div>
              <label className={labelClass}>Company name *</label>
              <input required type="text" className={inputClass} placeholder="Company" />
            </div>

            <div>
              <label className={labelClass}>Segment *</label>
              <select required className={inputClass + ' cursor-pointer'}>
                <option value="">Select...</option>
                <option>Buy Side</option>
                <option>Sell Side</option>
                <option>Corporate</option>
                <option>Academic</option>
                <option>Other</option>
              </select>
            </div>

            <div>
              <label className={labelClass}>Country *</label>
              <select required className={inputClass + ' cursor-pointer'} defaultValue="Indonesia">
                <option>Indonesia</option>
                <option>Singapore</option>
                <option>Malaysia</option>
                <option>Thailand</option>
                <option>Other</option>
              </select>
            </div>

            <div>
              <label className={labelClass}>Message</label>
              <textarea rows={4} className={inputClass + ' resize-none'} placeholder="How can we help?" />
            </div>

            <button type="submit" className="h-10 rounded-full bg-[#2563eb] px-8 text-[14px] font-medium text-white transition-colors hover:bg-[#1d4ed8]">
              Submit
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
