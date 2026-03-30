import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test('overview page has metric cards', async ({ page }) => {
    await page.goto('/dashboard/overview', { waitUntil: 'networkidle' });
    await expect(page.locator('text=NAV')).toBeAttached({ timeout: 10000 });
    await expect(page.locator('text=Daily Return')).toBeAttached({ timeout: 10000 });
    await expect(page.locator('text=Max Drawdown')).toBeAttached({ timeout: 10000 });
  });

  test('sidebar navigation switches views', async ({ page }) => {
    await page.goto('/dashboard/overview', { waitUntil: 'networkidle' });
    const portfolioLink = page.locator('a[href="/dashboard/portfolio"]');
    await expect(portfolioLink).toBeVisible({ timeout: 10000 });
    await portfolioLink.click();
    await expect(page).toHaveURL('/dashboard/portfolio', { timeout: 10000 });
    await expect(page.locator('h1')).toContainText('Portfolio', { timeout: 10000 });
  });

  test('strategies page lists strategies', async ({ page }) => {
    await page.goto('/dashboard/strategies', { waitUntil: 'networkidle' });
    await expect(page.locator('h1')).toContainText('Strategies', { timeout: 10000 });
    await expect(page.locator('text=IDX Momentum')).toBeAttached({ timeout: 10000 });
    await expect(page.locator('text=Value-Quality')).toBeAttached({ timeout: 10000 });
  });

  test('api keys page has table', async ({ page }) => {
    await page.goto('/dashboard/api-keys', { waitUntil: 'networkidle' });
    await expect(page.locator('h1')).toContainText('API Keys', { timeout: 10000 });
    await expect(page.locator('table')).toBeAttached({ timeout: 10000 });
    await expect(page.locator('td', { hasText: 'Production' })).toBeAttached({ timeout: 10000 });
  });

  test('settings page has profile form', async ({ page }) => {
    await page.goto('/dashboard/settings', { waitUntil: 'networkidle' });
    await expect(page.locator('h1')).toContainText('Settings', { timeout: 10000 });
    await expect(page.locator('h2', { hasText: 'Profile' })).toBeAttached({ timeout: 10000 });
    await expect(page.locator('input[type="text"]').first()).toBeAttached({ timeout: 10000 });
  });
});
