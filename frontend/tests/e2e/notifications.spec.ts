import { test, expect } from '@playwright/test'

test.describe('Notification Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login')
    await page.fill('[data-testid="email-input"]', 'operator@test-municipality.gov')
    await page.fill('[data-testid="password-input"]', 'testpassword123')
    await page.click('[data-testid="login-button"]')
    await expect(page).toHaveURL('/dashboard')
  })
  
  test('should display notifications list', async ({ page }) => {
    await page.goto('/notifications')
    
    // Should show notifications table
    await expect(page.locator('[data-testid="notifications-table"]')).toBeVisible()
    
    // Should show at least one notification
    await expect(page.locator('[data-testid="notification-row"]')).toHaveCount.greaterThan(0)
    
    // Should show notification details
    const firstRow = page.locator('[data-testid="notification-row"]').first()
    await expect(firstRow.locator('[data-testid="notification-title"]')).toBeVisible()
    await expect(firstRow.locator('[data-testid="notification-status"]')).toBeVisible()
    await expect(firstRow.locator('[data-testid="notification-severity"]')).toBeVisible()
  })
  
  test('should filter notifications by status', async ({ page }) => {
    await page.goto('/notifications')
    
    // Select "received" status filter
    await page.click('[data-testid="status-filter"]')
    await page.click('[data-testid="status-received"]')
    
    // Should show only received notifications
    const statusCells = page.locator('[data-testid="notification-status"]')
    const count = await statusCells.count()
    
    for (let i = 0; i < count; i++) {
      await expect(statusCells.nth(i)).toContainText('received')
    }
  })
  
  test('should approve a notification', async ({ page }) => {
    await page.goto('/notifications')
    
    // Find a received notification
    const receivedRow = page.locator('[data-testid="notification-row"]')
      .filter({ has: page.locator('[data-testid="notification-status"]:has-text("received")') })
      .first()
    
    // Click on the notification to view details
    await receivedRow.click()
    
    // Should show notification detail page
    await expect(page.locator('[data-testid="notification-detail"]')).toBeVisible()
    
    // Should show approve button
    await expect(page.locator('[data-testid="approve-button"]')).toBeVisible()
    
    // Click approve button
    await page.click('[data-testid="approve-button"]')
    
    // Should show approval dialog
    await expect(page.locator('[data-testid="approval-dialog"]')).toBeVisible()
    
    // Select targets and categories
    await page.check('[data-testid="target-downtown"]')
    await page.check('[data-testid="category-emergency"]')
    
    // Confirm approval
    await page.click('[data-testid="confirm-approve-button"]')
    
    // Should show success message
    await expect(page.locator('[data-testid="success-message"]')).toBeVisible()
    await expect(page.locator('[data-testid="success-message"]')).toContainText('approved')
    
    // Status should be updated
    await expect(page.locator('[data-testid="notification-status"]')).toContainText('approved')
  })
  
  test('should deny a notification', async ({ page }) => {
    await page.goto('/notifications')
    
    // Find a received notification
    const receivedRow = page.locator('[data-testid="notification-row"]')
      .filter({ has: page.locator('[data-testid="notification-status"]:has-text("received")') })
      .first()
    
    // Click on the notification to view details
    await receivedRow.click()
    
    // Should show deny button
    await expect(page.locator('[data-testid="deny-button"]')).toBeVisible()
    
    // Click deny button
    await page.click('[data-testid="deny-button"]')
    
    // Should show denial dialog
    await expect(page.locator('[data-testid="denial-dialog"]')).toBeVisible()
    
    // Enter denial reason
    await page.fill('[data-testid="denial-reason"]', 'Test denial for E2E testing')
    
    // Confirm denial
    await page.click('[data-testid="confirm-deny-button"]')
    
    // Should show success message
    await expect(page.locator('[data-testid="success-message"]')).toBeVisible()
    await expect(page.locator('[data-testid="success-message"]')).toContainText('denied')
    
    // Status should be updated
    await expect(page.locator('[data-testid="notification-status"]')).toContainText('denied')
  })
  
  test('should search notifications', async ({ page }) => {
    await page.goto('/notifications')
    
    // Enter search term
    await page.fill('[data-testid="search-input"]', 'Water Main')
    
    // Should filter results
    const rows = page.locator('[data-testid="notification-row"]')
    const count = await rows.count()
    
    // All visible notifications should contain the search term
    for (let i = 0; i < count; i++) {
      const title = await rows.nth(i).locator('[data-testid="notification-title"]').textContent()
      expect(title?.toLowerCase()).toContain('water main')
    }
  })
})