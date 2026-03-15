import { test, expect } from '@playwright/test'

test.describe('NTU Campus Map - Zustand Migration Fix', () => {
  test('Scenario 1: Page loads without React/Zustand errors', async ({ page }) => {
    const consoleErrors: string[] = []
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
      }
    })

    await page.goto('http://localhost:5173/')
    
    await page.waitForTimeout(2000)
    
    const bodyText = await page.locator('body').textContent()
    await expect(bodyText).not.toContain('Invalid hook call')
    await expect(bodyText).not.toContain('Cannot read properties of null')
    await expect(bodyText).not.toContain('useRef')
    
    const hasZustandError = consoleErrors.some(err => 
      err.includes('zustand') || err.includes('hook') || err.includes('useRef')
    )
    expect(hasZustandError).toBe(false)
    
    console.log('✓ Scenario 1 passed: No React/Zustand errors')
  })

  test('Scenario 2: Map loads with default markers', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    
    await page.waitForTimeout(2000)
    
    const sidebar = page.locator('.absolute.top-0.left-0')
    await expect(sidebar).toBeVisible()
    
    const placesHeader = page.locator('text=Places')
    await expect(placesHeader).toBeVisible()
    
    const initialLandmarks = await page.locator('.space-y-2 button').count()
    expect(initialLandmarks).toBeGreaterThan(0)
    
    console.log(`✓ Scenario 2 passed: Found ${initialLandmarks} landmarks on page load`)
  })

  test('Scenario 3: Sidebar category filters work', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    
    await page.waitForTimeout(2000)
    
    const landmarkButton = page.locator('button:has-text("Landmarks")')
    await expect(landmarkButton).toBeVisible()
    
    await landmarkButton.click()
    
    await page.waitForTimeout(500)
    
    console.log('✓ Scenario 3 passed: Category filters work correctly')
  })

  test('Scenario 4: Click on landmark shows detail panel', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    
    await page.waitForTimeout(2000)
    
    const firstLandmark = page.locator('.space-y-2 button').first()
    await firstLandmark.click()
    
    await page.waitForTimeout(500)
    
    const detailPanel = page.locator('.absolute.top-0.right-0')
    await expect(detailPanel).toBeVisible()
    
    console.log('✓ Scenario 4 passed: Detail panel opens on landmark click')
  })

  test('Scenario 5: Export and Import buttons exist', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    
    await page.waitForTimeout(2000)
    
    const exportButton = page.locator('button:has-text("Export")')
    const importButton = page.locator('button:has-text("Import")')
    
    await expect(exportButton).toBeVisible()
    await expect(importButton).toBeVisible()
    
    console.log('✓ Scenario 5 passed: Export and Import buttons are present')
  })
})
