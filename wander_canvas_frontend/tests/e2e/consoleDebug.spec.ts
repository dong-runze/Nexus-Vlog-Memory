import { test, expect } from '@playwright/test'

test.describe('Debug Toggle with Console Logs', () => {
  test('Check console logs during toggle', async ({ page }) => {
    const logs: string[] = []
    page.on('console', msg => {
      logs.push(`[${msg.type()}] ${msg.text()}`)
    })
    
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    console.log('=== Initial State ===')
    console.log('Places:', await page.locator('.space-y-2 button').count())
    
    console.log('\n=== First Click ===')
    const landmarkBtn = page.locator('button').filter({ hasText: 'Landmarks' }).first()
    await landmarkBtn.click()
    await page.waitForTimeout(1000)
    console.log('Places:', await page.locator('.space-y-2 button').count())
    
    console.log('\n=== Second Click ===')
    await landmarkBtn.click()
    await page.waitForTimeout(1000)
    console.log('Places:', await page.locator('.space-y-2 button').count())
    
    console.log('\n=== Console Logs ===')
    logs.forEach(log => console.log(log))
    
    expect(await page.locator('.space-y-2 button').count()).toBe(8)
  })
})
