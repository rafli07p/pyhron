import { test, expect } from '@playwright/test';

test('health endpoint returns healthy', async ({ request }) => {
  const response = await request.get('/api/health');
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.status).toBe('healthy');
});

test('landing page renders', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('text=PYHRON')).toBeVisible();
});

test('login page renders', async ({ page }) => {
  await page.goto('/login');
  await expect(page.locator('text=Sign in to your account')).toBeVisible();
});
