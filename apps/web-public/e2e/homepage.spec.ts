import { test, expect } from '@playwright/test';

test.describe('Homepage', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
  });

  test('hero section is visible with headline', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Quantitative Analytics', { timeout: 10000 });
  });

  test('animated counters reach non-zero values', async ({ page }) => {
    await page.waitForTimeout(3000);
    const counters = page.locator('text=/\\d+\\+/');
    const count = await counters.count();
    expect(count).toBeGreaterThanOrEqual(1);
    const text = await counters.first().textContent();
    const num = parseInt(text?.replace(/[^0-9]/g, '') || '0');
    expect(num).toBeGreaterThan(0);
  });

  test('ticker bar scrolls with stock data', async ({ page }) => {
    const ticker = page.locator('[aria-label="Market ticker"]');
    await expect(ticker).toBeAttached({ timeout: 10000 });
    await expect(ticker).toContainText('IHSG', { timeout: 10000 });
  });

  test('research insight cards link to articles', async ({ page }) => {
    const cards = page.locator('a[href^="/research/"]');
    await expect(cards.first()).toBeAttached({ timeout: 10000 });
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(3);
  });

  test('solutions cards appear on scroll', async ({ page }) => {
    const heading = page.locator('text=Built for quantitative analysis');
    await expect(heading).toBeAttached({ timeout: 10000 });
    await expect(page.locator('text=Algorithmic Trading').first()).toBeAttached({ timeout: 10000 });
  });

  test('CTAs are visible', async ({ page }) => {
    await expect(page.locator('a[href="/register"]').first()).toBeVisible({ timeout: 10000 });
  });

  test('footer is visible with links', async ({ page }) => {
    await expect(page.locator('footer')).toBeVisible({ timeout: 10000 });
  });
});
