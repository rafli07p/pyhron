import { test, expect } from '@playwright/test';

test.describe('Responsive Layout', () => {
  test('homepage at 375px has no horizontal overflow', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/', { waitUntil: 'networkidle' });
    const body = page.locator('body');
    const bodyWidth = await body.evaluate((el) => el.scrollWidth);
    expect(bodyWidth).toBeLessThanOrEqual(375);
  });

  test('screener at 375px has no horizontal overflow', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/data/screener', { waitUntil: 'networkidle' });
    // Table is allowed to overflow-x, but body should not
    const html = page.locator('html');
    const htmlWidth = await html.evaluate((el) => el.scrollWidth);
    const viewportWidth = await html.evaluate(() => window.innerWidth);
    // Allow small tolerance for scrollbar
    expect(htmlWidth).toBeLessThanOrEqual(viewportWidth + 2);
  });

  test('research at 375px has no horizontal overflow', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/research', { waitUntil: 'networkidle' });
    const body = page.locator('body');
    const bodyWidth = await body.evaluate((el) => el.scrollWidth);
    expect(bodyWidth).toBeLessThanOrEqual(375);
  });

  test('MegaMenu becomes sheet at 768px', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/', { waitUntil: 'networkidle' });
    // Desktop nav should be hidden, mobile menu button visible
    const menuBtn = page.getByRole('button', { name: /open menu/i });
    await expect(menuBtn).toBeVisible({ timeout: 10000 });
    await menuBtn.click();
    // Sheet should appear from right
    await expect(page.locator('text=Solutions').last()).toBeAttached({ timeout: 10000 });
  });
});
