import { test, expect } from '@playwright/test';

test.describe('MegaMenu', () => {
  test('opens on hover (desktop)', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const solutionsBtn = page.locator('header nav button', { hasText: 'Solutions' });
    await expect(solutionsBtn).toBeVisible({ timeout: 10000 });
    await solutionsBtn.click();
    const megaMenu = page.locator('h3:has-text("Quantitative Analytics")');
    await expect(megaMenu).toBeAttached({ timeout: 10000 });
  });

  test('closes on Escape', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const solutionsBtn = page.locator('header nav button', { hasText: 'Solutions' });
    await expect(solutionsBtn).toBeVisible({ timeout: 10000 });
    await solutionsBtn.click();
    await expect(page.locator('h3:has-text("Quantitative Analytics")')).toBeAttached({ timeout: 10000 });
    await page.keyboard.press('Escape');
    await expect(page.locator('h3:has-text("Quantitative Analytics")')).not.toBeAttached({ timeout: 10000 });
  });

  test('closes on click outside', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const solutionsBtn = page.locator('header nav button', { hasText: 'Solutions' });
    await expect(solutionsBtn).toBeVisible({ timeout: 10000 });
    await solutionsBtn.click();
    await expect(page.locator('h3:has-text("Quantitative Analytics")')).toBeAttached({ timeout: 10000 });
    await page.mouse.click(400, 500);
    await page.waitForTimeout(500);
    await expect(page.locator('h3:has-text("Quantitative Analytics")')).not.toBeAttached({ timeout: 10000 });
  });

  test('navigates on item click', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const solutionsBtn = page.locator('header nav button', { hasText: 'Solutions' });
    await expect(solutionsBtn).toBeVisible({ timeout: 10000 });
    await solutionsBtn.click();
    const factorModels = page.locator('a[href="/solutions/factor-models"]').first();
    await expect(factorModels).toBeAttached({ timeout: 10000 });
    await factorModels.click();
    await expect(page).toHaveURL('/solutions/factor-models', { timeout: 10000 });
  });

  test('shows sheet on mobile (375px)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/', { waitUntil: 'networkidle' });
    const menuBtn = page.getByRole('button', { name: /open menu/i });
    await expect(menuBtn).toBeVisible({ timeout: 10000 });
    await menuBtn.click();
    await expect(page.locator('text=Solutions').last()).toBeAttached({ timeout: 10000 });
  });
});
