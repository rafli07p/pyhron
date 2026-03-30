import { test, expect } from '@playwright/test';

test.describe('Research Hub', () => {
  test('should display research articles list', async ({ page }) => {
    await page.goto('/research');
    await expect(page.locator('h1')).toContainText(/research/i);
    const articles = page.locator('article, [data-testid="research-card"]');
    await expect(articles.first()).toBeVisible();
  });

  test('should navigate to article detail', async ({ page }) => {
    await page.goto('/research');
    const firstLink = page.locator('a[href*="/research/"]').first();
    await firstLink.click();
    await expect(page.locator('article h1')).toBeVisible();
  });

  test('should filter by category', async ({ page }) => {
    await page.goto('/research');
    const filterBtn = page.getByRole('button', { name: /quantitative/i });
    if (await filterBtn.isVisible()) {
      await filterBtn.click();
      // Should still show articles
      const articles = page.locator('article, [data-testid="research-card"]');
      await expect(articles.first()).toBeVisible();
    }
  });
});
