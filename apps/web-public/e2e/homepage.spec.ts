import { test, expect } from '@playwright/test';

test.describe('Homepage', () => {
  test('should load and display hero section', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1')).toBeVisible();
    await expect(page.locator('h1')).toContainText(/quantitative|Pyhron/i);
  });

  test('should have working navigation', async ({ page }) => {
    await page.goto('/');
    const nav = page.locator('header nav');
    await expect(nav).toBeVisible();
  });

  test('should toggle dark/light theme', async ({ page }) => {
    await page.goto('/');
    const html = page.locator('html');
    const initialClass = await html.getAttribute('class');
    // Theme toggle button
    const themeBtn = page.getByRole('button', { name: /theme|dark|light/i });
    if (await themeBtn.isVisible()) {
      await themeBtn.click();
      const newClass = await html.getAttribute('class');
      expect(newClass).not.toBe(initialClass);
    }
  });

  test('should open command palette with Cmd+K', async ({ page }) => {
    await page.goto('/');
    await page.keyboard.press('Meta+k');
    await expect(page.getByPlaceholder(/search/i)).toBeVisible({ timeout: 3000 });
  });
});
