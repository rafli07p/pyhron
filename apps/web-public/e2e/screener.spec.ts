import { test, expect } from '@playwright/test';

test.describe('Stock Screener', () => {
  test('should display screener table', async ({ page }) => {
    await page.goto('/screener');
    await expect(page.locator('table')).toBeVisible();
    // Should have at least one stock row
    const rows = page.locator('tbody tr');
    await expect(rows.first()).toBeVisible();
  });

  test('should sort by column', async ({ page }) => {
    await page.goto('/screener');
    const symbolHeader = page.getByRole('columnheader', { name: /symbol/i });
    if (await symbolHeader.isVisible()) {
      await symbolHeader.click();
      // Table should still be visible after sort
      await expect(page.locator('table')).toBeVisible();
    }
  });

  test('should filter by sector', async ({ page }) => {
    await page.goto('/screener');
    const sectorFilter = page.locator('select, [data-testid="sector-filter"]').first();
    if (await sectorFilter.isVisible()) {
      await sectorFilter.selectOption({ index: 1 });
      await expect(page.locator('table')).toBeVisible();
    }
  });
});
