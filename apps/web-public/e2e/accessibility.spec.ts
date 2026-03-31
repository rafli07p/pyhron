import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility', () => {
  test('homepage has zero critical axe violations', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    const critical = results.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious',
    );
    if (critical.length > 0) {
      console.log('Critical violations:', JSON.stringify(critical, null, 2));
    }
    expect(critical).toHaveLength(0);
  });

  test('focus ring visible on tab navigation', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    const focused = page.locator(':focus');
    await expect(focused).toBeVisible({ timeout: 10000 });
    const outlineStyle = await focused.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return style.outlineStyle;
    });
    expect(outlineStyle).not.toBe('none');
  });

  test('skip-to-content link works', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.keyboard.press('Tab');
    const skipLink = page.locator('.skip-to-content');
    await expect(skipLink).toBeAttached({ timeout: 10000 });
    await expect(skipLink).toBeFocused({ timeout: 10000 });
    await page.keyboard.press('Enter');
    const mainContent = page.locator('#main-content');
    await expect(mainContent).toBeAttached({ timeout: 10000 });
  });

  test('ticker has aria-label', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const ticker = page.locator('[aria-label="Market ticker"]');
    await expect(ticker).toBeVisible({ timeout: 10000 });
  });
});
