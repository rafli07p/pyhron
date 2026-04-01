import { test as setup } from '@playwright/test';

const AUTH_FILE = 'e2e/.auth/user.json';

setup('authenticate', async ({ page }) => {
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

  await page.goto('/dashboard/overview', { waitUntil: 'networkidle' });
  await page.context().storageState({ path: AUTH_FILE });
});
