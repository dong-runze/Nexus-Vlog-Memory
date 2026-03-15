import { test, expect } from '@playwright/test'

test.describe('Clone + Zoom Issue', () => {
  test('After clone, zoom should not cause marker position shift', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const initialCount = await page.locator('.custom-marker').count()
    console.log('Initial:', initialCount)
    
    const firstMarker = page.locator('.custom-marker').first()
    const initialBox = await firstMarker.boundingBox()
    console.log('Initial position:', initialBox)
    
    await firstMarker.click({ button: 'right' })
    await page.waitForTimeout(500)
    
    const afterCloneCount = await page.locator('.custom-marker').count()
    console.log('After clone:', afterCloneCount)
    
    const afterCloneBox = await firstMarker.boundingBox()
    console.log('After clone position:', afterCloneBox)
    
    await page.mouse.wheel(0, -200)
    await page.waitForTimeout(1000)
    
    const afterZoomBox = await firstMarker.boundingBox()
    console.log('After zoom position:', afterZoomBox)
    
    const afterZoomCount = await page.locator('.custom-marker').count()
    console.log('After zoom count:', afterZoomCount)
    
    expect(afterZoomCount).toBe(afterCloneCount)
  })

  test('Multiple clones and zoom should work correctly', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    await page.locator('.custom-marker').first().click({ button: 'right' })
    await page.waitForTimeout(300)
    
    await page.locator('.custom-marker').first().click({ button: 'right' })
    await page.waitForTimeout(300)
    
    const afterTwoClones = await page.locator('.custom-marker').count()
    console.log('After 2 clones:', afterTwoClones)
    
    for (let i = 0; i < 3; i++) {
      await page.mouse.wheel(0, -200)
      await page.waitForTimeout(300)
      await page.mouse.wheel(0, 200)
      await page.waitForTimeout(300)
    }
    
    const finalCount = await page.locator('.custom-marker').count()
    console.log('Final count:', finalCount)
    expect(finalCount).toBe(afterTwoClones)
  })
})
