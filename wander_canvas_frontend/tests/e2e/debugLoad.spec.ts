import { test, expect } from '@playwright/test'

test.describe('Debug Page Load', () => {
  test('Check page loads and console errors', async ({ page }) => {
    const errors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })
    
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(5000)
    
    const title = await page.title()
    console.log('Page title:', title)
    
    const bodyContent = await page.locator('body').innerHTML()
    console.log('Body length:', bodyContent.length)
    
    const mapContainer = await page.locator('.leaflet-container').count()
    console.log('Map container count:', mapContainer)
    
    const markers = await page.locator('.custom-marker').count()
    console.log('Marker count:', markers)
    
    console.log('Console errors:', errors)
  })
})
