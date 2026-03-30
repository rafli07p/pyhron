import { test as setup } from '@playwright/test';

const AUTH_FILE = 'e2e/.auth/user.json';

setup('authenticate', async ({ page }) => {
  // The proxy.ts checks for the authjs.session-token cookie.
  // Set it directly to bypass the login flow (no backend available in tests).
  await page.context().addCookies([
    {
      name: 'authjs.session-token',
      value: 'mock-session-token-for-e2e',
      domain: 'localhost',
      path: '/',
      httpOnly: true,
      secure: false,
      sameSite: 'Lax',
    },
  ]);

  // Verify the cookie lets us through the proxy
  await page.goto('/dashboard/overview', { waitUntil: 'networkidle' });

  // Save storage state (includes cookies)
  await page.context().storageState({ path: AUTH_FILE });
});
