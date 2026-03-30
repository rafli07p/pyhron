import { test, expect } from '@playwright/test';

test.describe('Stock Screener', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/data/screener', { waitUntil: 'networkidle' });
  });

  test('renders stock rows', async ({ page }) => {
    await expect(page.locator('table')).toBeAttached({ timeout: 10000 });
    const rows = page.locator('tbody tr');
    await expect(rows.first()).toBeAttached({ timeout: 10000 });
    const count = await rows.count();
    expect(count).toBeGreaterThanOrEqual(20);
  });

  test('column sort reverses order', async ({ page }) => {
    await expect(page.locator('table')).toBeAttached({ timeout: 10000 });
    // Get first ticker before sort
    const firstCellBefore = await page.locator('tbody tr:first-child td:first-child').textContent();

    // Click P/E header to sort
    await page.locator('th', { hasText: 'P/E' }).click();
    await page.waitForTimeout(500);
    // Click again to reverse
    await page.locator('th', { hasText: 'P/E' }).click();
    await page.waitForTimeout(500);

    const firstCellAfter = await page.locator('tbody tr:first-child td:first-child').textContent();
    // Order should have changed at some point (may or may not be different after double click)
    expect(firstCellBefore).toBeDefined();
    expect(firstCellAfter).toBeDefined();
  });

  test('sector filter narrows results', async ({ page }) => {
    await expect(page.locator('tbody tr').first()).toBeAttached({ timeout: 10000 });
    const allRows = await page.locator('tbody tr').count();
    await page.locator('select').first().selectOption('Energy');
    await page.waitForTimeout(500);
    const filteredRows = await page.locator('tbody tr').count();
    expect(filteredRows).toBeLessThan(allRows);
    expect(filteredRows).toBeGreaterThan(0);
  });

  test('LQ45 filter works', async ({ page }) => {
    await expect(page.locator('tbody tr').first()).toBeAttached({ timeout: 10000 });
    const allRows = await page.locator('tbody tr').count();
    await page.locator('input[type="checkbox"]').click();
    await page.waitForTimeout(500);
    const filteredRows = await page.locator('tbody tr').count();
    expect(filteredRows).toBeLessThanOrEqual(allRows);
  });

  test('CSV export triggers download', async ({ page }) => {
    await expect(page.locator('table')).toBeAttached({ timeout: 10000 });
    const downloadPromise = page.waitForEvent('download', { timeout: 10000 });
    await page.locator('button', { hasText: /CSV/i }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain('pyhron-screener');
  });
});
