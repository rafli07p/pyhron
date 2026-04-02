import { test, expect } from '@playwright/test';

test('health endpoint returns healthy', async ({ request }) => {
  const response = await request.get('/api/health');
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.status).toBe('healthy');
});

test('landing page loads without error', async ({ page }) => {
  const response = await page.goto('/');
  expect(response?.status()).toBeLessThan(500);
});

test('login page loads without error', async ({ page }) => {
  const response = await page.goto('/login');
  expect(response?.status()).toBeLessThan(500);
});
