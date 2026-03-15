import { test, expect } from '@playwright/test'

test.describe('NTU Campus Map - Category Filter Debug', () => {
  test('Debug category toggle - step by step', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(3000)
    
    console.log('=== Step 1: Initial State ===')
    let count1 = await page.locator('.space-y-2 button').count()
    console.log(`Places count: ${count1}`)
    
    const landmarksBtn = page.locator('button').filter({ hasText: 'Landmarks' })
    const btnText = await landmarksBtn.textContent()
    console.log(`Button text: ${btnText}`)
    let btnClasses = await landmarksBtn.getAttribute('class')
    console.log(`Button classes: ${btnClasses}`)
    
    console.log('\n=== Step 2: Click to hide Landmarks ===')
    await landmarksBtn.click()
    await page.waitForTimeout(1000)
    
    let count2 = await page.locator('.space-y-2 button').count()
    console.log(`Places count: ${count2}`)
    btnClasses = await landmarksBtn.getAttribute('class')
    console.log(`Button classes: ${btnClasses}`)
    
    console.log('\n=== Step 3: Click again to restore Landmarks ===')
    await landmarksBtn.click()
    await page.waitForTimeout(1000)
    
    let count3 = await page.locator('.space-y-2 button').count()
    console.log(`Places count: ${count3}`)
    btnClasses = await landmarksBtn.getAttribute('class')
    console.log(`Button classes: ${btnClasses}`)
    
    console.log('\n=== Final Check ===')
    expect(count3).toBe(count1)
  })

  test('Test toggle with Schools category', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(3000)
    
    const initialCount = await page.locator('.space-y-2 button').count()
    console.log(`Initial: ${initialCount}`)
    
    const schoolsBtn = page.locator('button').filter({ hasText: 'Schools' })
    await schoolsBtn.click()
    await page.waitForTimeout(1000)
    
    const afterHide = await page.locator('.space-y-2 button').count()
    console.log(`After hide: ${afterHide}`)
    
    await schoolsBtn.click()
    await page.waitForTimeout(1000)
    
    const afterRestore = await page.locator('.space-y-2 button').count()
    console.log(`After restore: ${afterRestore}`)
    
    expect(afterRestore).toBe(initialCount)
  })
})
