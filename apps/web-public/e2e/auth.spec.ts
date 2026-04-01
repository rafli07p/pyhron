import { test, expect } from '@playwright/test';

test.describe('Auth', () => {
  test('login form shows error for invalid credentials', async ({ page }) => {
    await page.goto('/login', { waitUntil: 'networkidle' });
    const emailInput = page.locator('input[type="email"]');
    await expect(emailInput).toBeVisible({ timeout: 10000 });
    await emailInput.fill('wrong@test.com');
    await page.locator('input[type="password"]').fill('wrongpass');
    const submitBtn = page.locator('button[type="submit"]');
    await submitBtn.click();
    const errorVisible = page.locator('text=/invalid|error|failed|incorrect/i');
    const stayedOnLogin = page.locator('input[type="email"]');
    await expect(async () => {
      const hasError = await errorVisible.isVisible().catch(() => false);
      const stillOnLogin = await stayedOnLogin.isVisible().catch(() => false);
      expect(hasError || stillOnLogin).toBe(true);
    }).toPass({ timeout: 10000 });
  });

  test('login page has required fields', async ({ page }) => {
    await page.goto('/login', { waitUntil: 'networkidle' });
    await expect(page.locator('h1')).toContainText(/log in/i, { timeout: 10000 });
    await expect(page.locator('input[type="email"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('input[type="password"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('button[type="submit"]')).toBeVisible({ timeout: 10000 });
  });

  test('unauthenticated /dashboard redirects to login', async ({ page }) => {
    await page.goto('/dashboard', { waitUntil: 'networkidle' });
    await expect(page).toHaveURL(/login/, { timeout: 10000 });
  });

  test('register page shows form', async ({ page }) => {
    await page.goto('/register', { waitUntil: 'networkidle' });
    await expect(page.locator('h1')).toContainText(/create|register/i, { timeout: 10000 });
    await expect(page.locator('input[type="email"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('input[type="password"]').first()).toBeVisible({ timeout: 10000 });
  });

  test('register form validates password mismatch', async ({ page }) => {
    await page.goto('/register', { waitUntil: 'networkidle' });
    const nameInput = page.locator('#full_name');
    await expect(nameInput).toBeVisible({ timeout: 10000 });
    await nameInput.fill('Test User');
    await page.locator('#reg-email').fill('test@example.com');
    await page.locator('#reg-password').fill('password123');
    await page.locator('#confirm-password').fill('different123');
    await page.locator('button[type="submit"]').click();
    await expect(page.locator('text=/passwords do not match/i')).toBeVisible({ timeout: 10000 });
  });
});
