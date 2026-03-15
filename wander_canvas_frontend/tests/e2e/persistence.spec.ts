import { test, expect } from '@playwright/test'

test.describe('Data Persistence', () => {
  test('Cloned marker should persist after page reload', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const initialCount = await page.locator('.custom-marker').count()
    console.log('Initial markers:', initialCount)
    
    const firstMarker = page.locator('.custom-marker').first()
    await firstMarker.click({ button: 'right' })
    await page.waitForTimeout(500)
    
    const afterCloneCount = await page.locator('.custom-marker').count()
    console.log('After clone:', afterCloneCount)
    expect(afterCloneCount).toBe(initialCount + 1)
    
    await page.reload()
    await page.waitForTimeout(2000)
    
    const afterReloadCount = await page.locator('.custom-marker').count()
    console.log('After reload:', afterReloadCount)
    expect(afterReloadCount).toBe(afterCloneCount)
  })
})
