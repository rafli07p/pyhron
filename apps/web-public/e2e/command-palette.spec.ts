import { test, expect } from '@playwright/test';

test.describe('Command Palette', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
  });

  test('Ctrl+K opens command palette', async ({ page }) => {
    await page.keyboard.press('Control+k');
    const input = page.getByPlaceholder(/search/i);
    await expect(input).toBeAttached({ timeout: 10000 });
  });

  test('typing filters results', async ({ page }) => {
    await page.keyboard.press('Control+k');
    const input = page.getByPlaceholder(/search/i);
    await expect(input).toBeAttached({ timeout: 10000 });
    await input.fill('momentum');
    await page.waitForTimeout(500);
    // Results are plain buttons inside the palette
    const results = page.locator('button', { hasText: /momentum/i });
    await expect(results.first()).toBeAttached({ timeout: 10000 });
  });

  test('arrow keys navigate results', async ({ page }) => {
    await page.keyboard.press('Control+k');
    const input = page.getByPlaceholder(/search/i);
    await expect(input).toBeAttached({ timeout: 10000 });
    // Press down arrow to highlight an item
    await page.keyboard.press('ArrowDown');
    await page.waitForTimeout(300);
    // The selected item gets accent-500 color class in the component
    const highlighted = page.locator('button[class*="accent"]');
    const count = await highlighted.count();
    expect(count).toBeGreaterThan(0);
  });

  test('Enter navigates to selected result', async ({ page }) => {
    await page.keyboard.press('Control+k');
    const input = page.getByPlaceholder(/search/i);
    await expect(input).toBeAttached({ timeout: 10000 });
    await input.fill('Pricing');
    await page.waitForTimeout(1000);
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/pricing/, { timeout: 10000 });
  });

  test('Escape closes palette', async ({ page }) => {
    await page.keyboard.press('Control+k');
    const input = page.getByPlaceholder(/search/i);
    await expect(input).toBeAttached({ timeout: 10000 });
    await page.keyboard.press('Escape');
    await expect(input).not.toBeAttached({ timeout: 10000 });
  });
});
