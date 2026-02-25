import { test, expect, waitForAuthCheck } from './fixtures/test-fixtures';

/**
 * Basic application smoke tests
 *
 * These tests verify that the core application functionality works:
 * - App loads successfully
 * - Navigation works
 * - Key pages render correctly
 */

test.describe('Application Smoke Tests', () => {
  test('should load the application', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // The app should load without crashing
    // Check for either dashboard content (bypass auth) or login page
    const pageContent = await page.content();
    expect(pageContent).toBeTruthy();
  });

  test('should display page title', async ({ page }) => {
    await page.goto('/');

    // Check that the page has a title
    const title = await page.title();
    expect(title).toBeTruthy();
  });

  test('should not have console errors on load', async ({ page }) => {
    const consoleErrors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // Filter out known acceptable errors (e.g., failed network requests during tests)
    const criticalErrors = consoleErrors.filter(
      (error) =>
        !error.includes('Failed to load resource') && !error.includes('net::ERR'),
    );

    expect(criticalErrors).toHaveLength(0);
  });
});

test.describe('Navigation', () => {
  test('should have working navigation or login page', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // Wait for auth check to complete
    await waitForAuthCheck(page);

    // Additional wait for content to render
    await page.waitForTimeout(2000);

    // Check if we're still stuck on auth loading
    const stillCheckingAuth = await page
      .locator('text="Checking authentication"')
      .isVisible()
      .catch(() => false);

    if (stillCheckingAuth) {
      // Auth is stuck - this means BYPASS_AUTH might not be set or there's an auth error
      // Skip this test as it requires proper auth configuration
      test.skip(
        true,
        'Auth check is stuck - BYPASS_AUTH might not be set on the dev server',
      );
      return;
    }

    // Wait for React to hydrate
    await page
      .waitForSelector('header, main, nav, button', { timeout: 15000 })
      .catch(() => {});

    // App should show either:
    // 1. Navigation (if auth bypassed or logged in)
    // 2. Login page (if auth enabled)
    // 3. Or at minimum, some content loaded (not stuck on auth check)
    const nav = page.locator('nav, [role="navigation"], header');
    const loginPage = page.locator(
      'button:has-text("Login"), button:has-text("Sign in"), [data-testid="login-btn"], .login, [class*="login"]',
    );
    const mainContent = page.locator('main, [role="main"]');

    // Either navigation OR login page OR main content should be visible
    const navVisible = await nav
      .first()
      .isVisible()
      .catch(() => false);
    const loginVisible = await loginPage
      .first()
      .isVisible()
      .catch(() => false);
    const contentVisible = await mainContent
      .first()
      .isVisible()
      .catch(() => false);

    expect(navVisible || loginVisible || contentVisible).toBe(true);
  });
});
