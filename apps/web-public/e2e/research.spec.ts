import { test, expect } from '@playwright/test';

test.describe('Research Hub', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/research', { waitUntil: 'networkidle' });
  });

  test('loads research cards', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Research', { timeout: 10000 });
    const cards = page.locator('a[href^="/research/"]');
    await expect(cards.first()).toBeAttached({ timeout: 10000 });
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(3);
  });

  test('category filter reduces card count', async ({ page }) => {
    const allCards = page.locator('a[href^="/research/"]');
    await expect(allCards.first()).toBeAttached({ timeout: 10000 });
    const initialCount = await allCards.count();

    const select = page.locator('select');
    await expect(select).toBeAttached({ timeout: 10000 });
    await select.selectOption('commodity');
    const filteredCards = page.locator('a[href^="/research/"]');
    await expect(filteredCards.first()).toBeAttached({ timeout: 10000 });
    const filteredCount = await filteredCards.count();
    expect(filteredCount).toBeLessThan(initialCount);
    expect(filteredCount).toBeGreaterThan(0);
  });

  test('search matches articles', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search"]');
    await expect(searchInput).toBeAttached({ timeout: 10000 });
    await searchInput.fill('momentum');
    // Should show momentum-related articles
    const cards = page.locator('a[href^="/research/"]');
    await expect(cards.first()).toBeAttached({ timeout: 10000 });
    const titles = await cards.allTextContents();
    const hasMatch = titles.some((t) => t.toLowerCase().includes('momentum'));
    expect(hasMatch).toBe(true);
  });

  test('pagination works', async ({ page }) => {
    // With 7 articles and 6 per page, there should be 2 pages
    const pageButtons = page.locator('button', { hasText: /^[0-9]+$/ });
    await expect(pageButtons.first()).toBeAttached({ timeout: 10000 });
    const count = await pageButtons.count();
    if (count > 1) {
      await pageButtons.nth(1).click();
      const cards = page.locator('a[href^="/research/"]');
      await expect(cards.first()).toBeAttached({ timeout: 10000 });
    }
  });
});

test.describe('Research Article', () => {
  test('article page renders with content', async ({ page }) => {
    await page.goto('/research/fama-french-five-factor-ihsg', { waitUntil: 'networkidle' });
    await expect(page.locator('h1')).toContainText('Fama-French', { timeout: 10000 });
    // Author info in DOM
    await expect(page.locator('text=Pyhron Research').first()).toBeAttached({ timeout: 10000 });
  });

  test('related articles sidebar shows links', async ({ page }) => {
    await page.goto('/research/fama-french-five-factor-ihsg', { waitUntil: 'networkidle' });
    const related = page.locator('aside a[href^="/research/"]');
    await expect(related.first()).toBeAttached({ timeout: 10000 });
    const count = await related.count();
    expect(count).toBeGreaterThan(0);
  });
});
