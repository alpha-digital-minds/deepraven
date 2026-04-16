import { test, expect } from '@playwright/test'

test.describe('Dashboard smoke tests', () => {
  test('unauthenticated visit redirects to login', async ({ page }) => {
    // Clear storage before page scripts run so the auth store finds no token
    await page.addInitScript(() => localStorage.clear())

    await page.goto('/dashboard/')
    await expect(page).toHaveURL(/\/dashboard\/login/)
  })

  test('login page renders core elements', async ({ page }) => {
    await page.goto('/dashboard/login')

    await expect(page.locator('#auth-title')).toBeVisible()
    await expect(page.locator('input[type="email"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()
    await expect(page.locator('button.login-btn')).toBeVisible()
    await expect(page.locator('button.login-btn')).toHaveText('Sign in')
  })

  test('login page switches to register mode', async ({ page }) => {
    await page.goto('/dashboard/login')

    await page.locator('.login-switch a').click()
    await expect(page.locator('#auth-title')).toHaveText('Create account')
    await expect(page.locator('button.login-btn')).toHaveText('Create account')
  })

  test('login page shows error on empty submit', async ({ page }) => {
    await page.goto('/dashboard/login')

    await page.locator('button.login-btn').click()
    await expect(page.locator('.login-error')).toBeVisible()
    await expect(page.locator('.login-error')).toContainText('required')
  })

  test('no JavaScript errors on initial load', async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', err => errors.push(err.message))

    await page.goto('/dashboard/login')
    await page.waitForLoadState('networkidle')

    expect(errors).toHaveLength(0)
  })

  test('built assets load correctly', async ({ page }) => {
    const failedRequests: string[] = []
    page.on('requestfailed', req => failedRequests.push(req.url()))

    await page.goto('/dashboard/login')
    await page.waitForLoadState('networkidle')

    // Filter out API calls (expected to fail without backend) — only asset failures matter
    const assetFailures = failedRequests.filter(u => u.includes('/assets/'))
    expect(assetFailures).toHaveLength(0)
  })
})
