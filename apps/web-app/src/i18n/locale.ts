import { cookies } from 'next/headers';

const DEFAULT_LOCALE = 'id';
const SUPPORTED_LOCALES = ['id', 'en'] as const;
type Locale = (typeof SUPPORTED_LOCALES)[number];

export async function getUserLocale(): Promise<Locale> {
  const cookieStore = await cookies();
  const locale = cookieStore.get('pyhron:locale')?.value;
  if (locale && SUPPORTED_LOCALES.includes(locale as Locale)) {
    return locale as Locale;
  }
  return DEFAULT_LOCALE;
}

export { SUPPORTED_LOCALES, DEFAULT_LOCALE };
export type { Locale };
