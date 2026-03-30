import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  const routes = [
    { path: '/', title: /pyhron|home/i },
    { path: '/research', title: /research/i },
    { path: '/screener', title: /screener/i },
    { path: '/indices', title: /ind/i },
    { path: '/pricing', title: /pricing/i },
    { path: '/docs', title: /doc|api/i },
  ];

  for (const route of routes) {
    test(`should load ${route.path}`, async ({ page }) => {
      await page.goto(route.path);
      await expect(page).toHaveTitle(route.title);
    });
  }

  test('should have responsive mobile menu', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    const menuBtn = page.getByRole('button', { name: /menu/i });
    await expect(menuBtn).toBeVisible();
  });

  test('should navigate via footer links', async ({ page }) => {
    await page.goto('/');
    const footer = page.locator('footer');
    await expect(footer).toBeVisible();
    const researchLink = footer.locator('a[href="/research"]');
    if (await researchLink.isVisible()) {
      await researchLink.click();
      await expect(page).toHaveURL('/research');
    }
  });
});
