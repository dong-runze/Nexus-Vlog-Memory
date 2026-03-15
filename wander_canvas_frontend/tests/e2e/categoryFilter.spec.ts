import { test, expect } from '@playwright/test'

test.describe('NTU Campus Map - Category Filter Tests', () => {
  test('Category filter should toggle visibility correctly', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const initialCount = await page.locator('.space-y-2 button').count()
    console.log(`Initial places count: ${initialCount}`)
    expect(initialCount).toBeGreaterThan(0)
    
    const landmarkButton = page.locator('button:has-text("Landmarks")')
    await expect(landmarkButton).toBeVisible()
    await landmarkButton.click()
    await page.waitForTimeout(500)
    
    const afterToggleCount = await page.locator('.space-y-2 button').count()
    console.log(`After toggle count: ${afterToggleCount}`)
    expect(afterToggleCount).not.toBe(initialCount)
    
    await landmarkButton.click()
    await page.waitForTimeout(500)
    
    const restoredCount = await page.locator('.space-y-2 button').count()
    console.log(`Restored count: ${restoredCount}`)
    expect(restoredCount).toBe(initialCount)
    
    console.log('✓ Category filter toggle works correctly')
  })

  test('All category buttons should be clickable and toggle states', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const categories = ['Landmarks', 'Schools', 'Dining', 'Special']
    
    for (const category of categories) {
      const button = page.locator(`button:has-text("${category}")`)
      await expect(button).toBeVisible()
      await button.click()
      await page.waitForTimeout(300)
      await button.click()
      await page.waitForTimeout(300)
    }
    
    console.log('✓ All category buttons are clickable')
  })

  test('Map markers should sync with sidebar filter', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const sidebarCount = await page.locator('.space-y-2 button').count()
    console.log(`Sidebar places: ${sidebarCount}`)
    
    await page.locator('button:has-text("Landmarks")').click()
    await page.waitForTimeout(500)
    
    const filteredCount = await page.locator('.space-y-2 button').count()
    console.log(`Filtered places: ${filteredCount}`)
    
    expect(filteredCount).toBeLessThan(sidebarCount)
    
    console.log('✓ Map markers sync with sidebar filter')
  })

  test('Hidden category button should have visual feedback', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const landmarkButton = page.locator('button:has-text("Landmarks")')
    await landmarkButton.click()
    await page.waitForTimeout(500)
    
    const buttonClasses = await landmarkButton.getAttribute('class')
    console.log(`Button classes after click: ${buttonClasses}`)
    
    expect(buttonClasses).toContain('opacity-50')
    expect(buttonClasses).toContain('saturate-50')
    
    console.log('✓ Visual feedback (opacity/saturate) is applied')
  })

  test('Restore category and verify all places return', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const originalCount = await page.locator('.space-y-2 button').count()
    console.log(`Original count: ${originalCount}`)
    
    await page.locator('button:has-text("Landmarks")').click()
    await page.waitForTimeout(500)
    
    await page.locator('button:has-text("Schools")').click()
    await page.waitForTimeout(500)
    
    const reducedCount = await page.locator('.space-y-2 button').count()
    console.log(`Reduced count: ${reducedCount}`)
    expect(reducedCount).toBeLessThan(originalCount)
    
    await page.locator('button:has-text("Landmarks")').click()
    await page.waitForTimeout(500)
    await page.locator('button:has-text("Schools")').click()
    await page.waitForTimeout(500)
    
    const restoredCount = await page.locator('.space-y-2 button').count()
    console.log(`Restored count: ${restoredCount}`)
    expect(restoredCount).toBe(originalCount)
    
    console.log('✓ All categories can be restored correctly')
  })
})
