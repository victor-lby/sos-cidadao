import { test, expect } from '@playwright/test'

test.describe('Authentication Flow', () => {
  test('should login with valid credentials', async ({ page }) => {
    await page.goto('/login')
    
    // Fill login form
    await page.fill('[data-testid="email-input"]', 'operator@test-municipality.gov')
    await page.fill('[data-testid="password-input"]', 'testpassword123')
    
    // Submit form
    await page.click('[data-testid="login-button"]')
    
    // Should redirect to dashboard
    await expect(page).toHaveURL('/dashboard')
    
    // Should show user name in header
    await expect(page.locator('[data-testid="user-name"]')).toContainText('Test Operator')
  })
  
  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/login')
    
    // Fill with invalid credentials
    await page.fill('[data-testid="email-input"]', 'invalid@example.com')
    await page.fill('[data-testid="password-input"]', 'wrongpassword')
    
    // Submit form
    await page.click('[data-testid="login-button"]')
    
    // Should show error message
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible()
    await expect(page.locator('[data-testid="error-message"]')).toContainText('Invalid credentials')
  })
  
  test('should logout successfully', async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.fill('[data-testid="email-input"]', 'operator@test-municipality.gov')
    await page.fill('[data-testid="password-input"]', 'testpassword123')
    await page.click('[data-testid="login-button"]')
    
    // Wait for dashboard
    await expect(page).toHaveURL('/dashboard')
    
    // Click user menu
    await page.click('[data-testid="user-menu-button"]')
    
    // Click logout
    await page.click('[data-testid="logout-button"]')
    
    // Should redirect to login
    await expect(page).toHaveURL('/login')
  })
})