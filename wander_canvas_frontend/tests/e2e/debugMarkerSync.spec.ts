import { test, expect } from '@playwright/test'

test.describe('Map Markers Sync Debug', () => {
  test('Debug marker sync with console logs', async ({ page }) => {
    const logs: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'log' || msg.type() === 'error' || msg.type() === 'warn') {
        logs.push(`[${msg.type()}] ${msg.text()}`)
      }
    })
    
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    console.log('=== Initial ===')
    console.log('Markers:', await page.locator('.custom-marker').count())
    
    console.log('\n=== First Click (hide Landmarks) ===')
    await page.locator('button').filter({ hasText: 'Landmarks' }).click()
    await page.waitForTimeout(1000)
    console.log('Markers:', await page.locator('.custom-marker').count())
    
    console.log('\n=== Second Click (restore Landmarks) ===')
    await page.locator('button').filter({ hasText: 'Landmarks' }).click()
    await page.waitForTimeout(1000)
    console.log('Markers:', await page.locator('.custom-marker').count())
    
    console.log('\n=== Console Logs ===')
    logs.forEach(log => console.log(log))
  })
})
